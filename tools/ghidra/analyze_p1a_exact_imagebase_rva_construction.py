#!/usr/bin/env python3
"""Bound exact imagebase + exact carrier-RVA immediate construction for P1.3A.

This is a deliberately narrow negative proof. It scans PC-retail .text disassembly
for exact scalar uses of the preferred PE image base (0x00400000) and exact RVA
scalars for the 16 canonical P1.3A carrier entrypoints. A same-function candidate
requires both tokens. Split arithmetic, encoded values, runtime-generated values,
callbacks and incoming indirect dispatch are intentionally out of scope.
"""
from __future__ import annotations
import argparse, bisect, collections, hashlib, json, re, sqlite3, subprocess
from pathlib import Path

FORMAT = "SHIFT.P1A.P13AExactImagebaseRvaImmediateConstructionClosure/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
INDEX_SHA256 = "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
IMAGE_BASE = 0x00400000
CARRIERS = [
    ("FUN_00758b50", 0x00758B50),
    ("FUN_00755950", 0x00755950),
    ("FUN_00770e80", 0x00770E80),
    ("FUN_00755a60", 0x00755A60),
    ("FUN_00752fc0", 0x00752FC0),
    ("FUN_00760b50", 0x00760B50),
    ("FUN_00763570", 0x00763570),
    ("FUN_00755f80", 0x00755F80),
    ("FUN_0076d100", 0x0076D100),
    ("FUN_00758810", 0x00758810),
    ("FUN_00769ef0", 0x00769EF0),
    ("FUN_007675f0", 0x007675F0),
    ("FUN_007682c0", 0x007682C0),
    ("FUN_00766510", 0x00766510),
    ("FUN_00758fc0", 0x00758FC0),
    ("FUN_00765c40", 0x00765C40),
]
INSTRUCTION_RE = re.compile(
    r"^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$"
)
HEX_TOKEN_RE = re.compile(r"(?<![0-9A-Fa-f])0x([0-9A-Fa-f]+)(?![0-9A-Fa-f])")
VALUE_MATERIALIZING_MNEMONICS = {"mov", "push", "add", "sub", "lea"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_functions(db: Path):
    con = sqlite3.connect(db)
    try:
        rows = []
        for addr, name in con.execute("select address,name from functions"):
            try:
                rows.append((int(addr, 16), name))
            except (TypeError, ValueError):
                pass
    finally:
        con.close()
    rows.sort()
    return rows


def function_for(address: int, functions, starts):
    i = bisect.bisect_right(starts, address) - 1
    if i < 0:
        return None
    return functions[i]


def scan_instruction_lines(lines, functions):
    starts = [row[0] for row in functions]
    carrier_rvas = {va - IMAGE_BASE: name for name, va in CARRIERS}
    imagebase_rows = []
    carrier_rva_rows = []
    per_function = collections.defaultdict(lambda: {"imagebase": [], "carrier_rva": []})
    instruction_count = 0
    for line in lines:
        m = INSTRUCTION_RE.match(line)
        if not m:
            continue
        instruction_count += 1
        operands = m.group(3).strip()
        if "0x" not in operands:
            continue
        tokens = [int(x, 16) for x in HEX_TOKEN_RE.findall(operands)]
        if IMAGE_BASE not in tokens and not any(t in carrier_rvas for t in tokens):
            continue
        address = int(m.group(1), 16)
        mnemonic = m.group(2).lower()
        fn = function_for(address, functions, starts)
        fn_name = fn[1] if fn else None
        row = {
            "address": f"0x{address:08x}",
            "mnemonic": mnemonic,
            "operands": operands,
            "function": fn_name,
        }
        if IMAGE_BASE in tokens:
            imagebase_rows.append(row)
            if fn_name:
                per_function[fn_name]["imagebase"].append(row)
        for token in tokens:
            if token in carrier_rvas:
                rr = dict(row)
                rr["carrier"] = carrier_rvas[token]
                rr["rva"] = f"0x{token:08x}"
                carrier_rva_rows.append(rr)
                if fn_name:
                    per_function[fn_name]["carrier_rva"].append(rr)
    candidates = []
    for fn_name, buckets in sorted(per_function.items()):
        if buckets["imagebase"] and buckets["carrier_rva"]:
            candidates.append(
                {
                    "function": fn_name,
                    "imagebase_sites": [r["address"] for r in buckets["imagebase"]],
                    "carrier_rva_sites": [r["address"] for r in buckets["carrier_rva"]],
                    "carriers": sorted({r["carrier"] for r in buckets["carrier_rva"]}),
                }
            )
    return {
        "instruction_count": instruction_count,
        "imagebase_rows": imagebase_rows,
        "carrier_rva_rows": carrier_rva_rows,
        "same_function_candidates": candidates,
    }


def scan_disassembly(exe: Path, functions):
    proc = subprocess.Popen(
        ["objdump", "-d", "-Mintel", str(exe)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
    )
    assert proc.stdout is not None
    result = scan_instruction_lines(proc.stdout, functions)
    stderr = proc.stderr.read() if proc.stderr else ""
    rc = proc.wait()
    if rc:
        raise RuntimeError(f"objdump failed ({rc}): {stderr}")
    return result


def analyze(exe: Path, db: Path):
    exe_sha = sha256(exe)
    db_sha = sha256(db)
    if exe_sha != RETAIL_SHA256:
        raise ValueError(f"unexpected SHIFT.exe SHA-256: {exe_sha}")
    if db_sha != INDEX_SHA256:
        raise ValueError(f"unexpected Ghidra SQLite SHA-256: {db_sha}")

    functions = load_functions(db)
    scan = scan_disassembly(exe, functions)
    imagebase_rows = scan["imagebase_rows"]
    carrier_rva_rows = scan["carrier_rva_rows"]
    materializers = [
        row for row in imagebase_rows if row["mnemonic"] in VALUE_MATERIALIZING_MNEMONICS
    ]
    mnemonic_counts = dict(
        sorted(collections.Counter(r["mnemonic"] for r in imagebase_rows).items())
    )
    per_carrier = []
    rva_hit_counts = collections.Counter(row["carrier"] for row in carrier_rva_rows)
    for name, va in CARRIERS:
        per_carrier.append(
            {
                "name": name,
                "address": f"0x{va:08x}",
                "rva": f"0x{va - IMAGE_BASE:08x}",
                "exact_rva_scalar_hit_count": rva_hit_counts[name],
            }
        )

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1A / P1.3A",
        "upstream_contracts": ["SHIFT.P1A.P13AStaticCarrierSeedHandoff/1"],
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": exe_sha,
            "ghidra_sqlite_sha256": db_sha,
            "preferred_image_base": "0x00400000",
            "machine_disassembly_adjudicates": True,
        },
        "scope": {
            "description": "same-function exact preferred-imagebase scalar plus exact canonical-carrier RVA scalar",
            "carrier_count": len(CARRIERS),
            "split_or_encoded_arithmetic_in_scope": False,
        },
        "scan": {
            "disassembled_instruction_count": scan["instruction_count"],
            "exact_imagebase_scalar_use_count": len(imagebase_rows),
            "exact_imagebase_mnemonic_counts": mnemonic_counts,
            "exact_imagebase_value_materializing_use_count": len(materializers),
            "exact_carrier_rva_scalar_use_count": len(carrier_rva_rows),
            "same_function_exact_imagebase_plus_carrier_rva_candidate_count": len(
                scan["same_function_candidates"]
            ),
        },
        "imagebase_value_materializers": materializers,
        "carrier_rva_surface": per_carrier,
        "same_function_candidates": scan["same_function_candidates"],
        "adjudication": {
            "p13a_exact_imagebase_plus_exact_carrier_rva_immediate_subset_complete": True,
            "p13a_exact_imagebase_plus_exact_carrier_rva_candidate_found": bool(
                scan["same_function_candidates"]
            ),
            "manual_imagebase_plus_exact_rva_immediate_construction_ruled_out": not bool(
                scan["same_function_candidates"]
            ),
            "manual_imagebase_plus_rva_pointer_construction_ruled_out": False,
            "encoded_or_reconstructed_carrier_pointers_ruled_out": False,
            "runtime_generated_or_copied_carrier_pointers_ruled_out": False,
            "runtime_callback_registration_ruled_out": False,
            "incoming_indirect_entry_ruled_out": False,
            "runtime_generated_selected_wheel_pointer_stores_ruled_out": False,
            "stored_or_escaped_aliases_ruled_out": False,
            "p13a_slot0_complete": False,
            "p13a_slot1_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only constructions whose function contains the exact preferred image-base scalar 0x00400000 and an exact canonical carrier RVA scalar.",
            "The result does not cover split additions, table-derived RVAs, encoded/XORed values, runtime arithmetic, copied/generated pointers, callback registration or incoming indirect dispatch.",
            "Exact image-base numeric uses that are flags, sizes, startup arguments or CRT image inspection are retained as observations and are not treated as pointer identity by themselves.",
            "No slot0/slot1 or aggregate P1.3 gate is promoted.",
        ],
        "next_step": "Trace split/table-derived/encoded carrier reconstruction and runtime registration/dispatch; continue selected-wheel data-pointer persistence independently.",
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("executable", type=Path)
    ap.add_argument("ghidra_sqlite", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    payload = analyze(args.executable, args.ghidra_sqlite)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
