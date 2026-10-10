#!/usr/bin/env python3
"""Bound x86 string/bulk-copy opcodes in direct callees of the 16 exact-root carriers."""
from __future__ import annotations
import argparse, hashlib, json, re, sqlite3, subprocess
from pathlib import Path

FORMAT = "SHIFT.P1D.Slot3DirectCalleeBulkOpcodeClosure/1"
EXE_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
SQLITE_SHA256 = "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
EXPECTED_DIRECT_CALLSITE_COUNT = 214
EXPECTED_DIRECT_CALLEE_COUNT = 82
EXPECTED_DIRECT_CALLEE_INSTRUCTION_COUNT = 9159
EXPECTED_DIRECT_CALLSITE_SHA256 = "bdd48b9a2c49f2aaec1f0311a895c7b077f44b254ca05c7165d84629e0ddbed8"
EXPECTED_TARGET_MANIFEST_SHA256 = "439a0227f1f7619763f579f4e7a6d0033fd7de341eb7180645b0537124633b27"
EXPECTED_INDIRECT_MANIFEST_SHA256 = "f25f5ac79ea099196349cf39ebb69c9e586ad2c12523f1c19cd43bf837444c27"
CARRIERS = {
    "FUN_00752fc0": (0x00752FC0, 37), "FUN_00755950": (0x00755950, 66),
    "FUN_00755a60": (0x00755A60, 1297), "FUN_00755f80": (0x00755F80, 132),
    "FUN_00758810": (0x00758810, 347), "FUN_00758b50": (0x00758B50, 1136),
    "FUN_00758fc0": (0x00758FC0, 364), "FUN_00760b50": (0x00760B50, 531),
    "FUN_00763570": (0x00763570, 3276), "FUN_00765c40": (0x00765C40, 2248),
    "FUN_00766510": (0x00766510, 4310), "FUN_007675f0": (0x007675F0, 1340),
    "FUN_007682c0": (0x007682C0, 335), "FUN_00769ef0": (0x00769EF0, 774),
    "FUN_0076d100": (0x0076D100, 508), "FUN_00770e80": (0x00770E80, 1183),
}
INSN_RE = re.compile(r"^\s*([0-9a-f]+):\s+((?:[0-9a-f]{2}\s+)+)\s*(.*)$", re.I)
CALL_RE = re.compile(r"call\s+(0x[0-9a-f]+|[0-9a-f]+)\b", re.I)
BULK_RE = re.compile(r"\b(?:rep|repe|repz|repne|repnz)\b|\b(?:movs|stos|lods|scas|cmps)[bwdq]?\b", re.I)

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def manifest_hash(value) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()

def disasm(exe: Path, start: int, size: int) -> list[tuple[int, str]]:
    out = subprocess.check_output([
        "objdump", "-d", "-M", "intel", f"--start-address={hex(start)}",
        f"--stop-address={hex(start + size)}", str(exe)
    ], text=True, errors="replace")
    rows = []
    for line in out.splitlines():
        m = INSN_RE.match(line)
        if m:
            rows.append((int(m.group(1), 16), m.group(3).strip()))
    return rows

def analyze(exe: Path, sqlite_path: Path) -> dict:
    exe_digest, db_digest = sha256(exe), sha256(sqlite_path)
    if exe_digest != EXE_SHA256:
        raise ValueError(f"unexpected SHIFT.exe SHA-256: {exe_digest}")
    if db_digest != SQLITE_SHA256:
        raise ValueError(f"unexpected shift_ghidra.sqlite SHA-256: {db_digest}")
    direct, indirect = [], []
    for caller, (start, size) in CARRIERS.items():
        for site, text in disasm(exe, start, size):
            if not text.lower().startswith("call"):
                continue
            m = CALL_RE.match(text)
            if m and int(m.group(1), 16) >= 0x00400000:
                direct.append({"caller": caller, "site": f"0x{site:08x}", "target": f"0x{int(m.group(1),16):08x}"})
            else:
                indirect.append({"caller": caller, "site": f"0x{site:08x}", "text": text})
    if len(direct) != EXPECTED_DIRECT_CALLSITE_COUNT or manifest_hash(direct) != EXPECTED_DIRECT_CALLSITE_SHA256:
        raise ValueError("direct callsite surface drift")
    if manifest_hash(indirect) != EXPECTED_INDIRECT_MANIFEST_SHA256:
        raise ValueError("indirect callsite surface drift")
    con = sqlite3.connect(sqlite_path)
    targets = []
    try:
        for address in sorted({row["target"] for row in direct}):
            row = con.execute("select name, raw_json from functions where address=?", (address,)).fetchone()
            if row is None:
                raise ValueError(f"missing function metadata for {address}")
            meta = json.loads(row[1])
            size = int(meta.get("size") or 0)
            if size <= 0:
                raise ValueError(f"missing function size for {address}")
            targets.append({"address": address, "name": row[0], "size": size})
    finally:
        con.close()
    if len(targets) != EXPECTED_DIRECT_CALLEE_COUNT or manifest_hash(targets) != EXPECTED_TARGET_MANIFEST_SHA256:
        raise ValueError("direct callee target manifest drift")
    hits, instruction_count = [], 0
    for target in targets:
        rows = disasm(exe, int(target["address"], 16), target["size"])
        instruction_count += len(rows)
        for site, text in rows:
            if BULK_RE.search(text):
                hits.append({"callee": target["name"], "site": f"0x{site:08x}", "text": text})
    if instruction_count != EXPECTED_DIRECT_CALLEE_INSTRUCTION_COUNT:
        raise ValueError(f"direct callee instruction-count drift: {instruction_count}")
    return {
        "format": FORMAT, "version": 1, "ready": True, "owner": "Process 1D / P1.3D",
        "authority": {"platform": "PC retail 1.02", "retail_executable_sha256": exe_digest, "ghidra_sqlite_sha256": db_digest, "machine_bytes_adjudicate": True},
        "surface": {
            "carrier_count": len(CARRIERS), "direct_callsite_count": len(direct), "unique_direct_callee_count": len(targets),
            "direct_callee_instruction_count": instruction_count,
            "direct_callsite_manifest_sha256": manifest_hash(direct), "direct_callee_manifest_sha256": manifest_hash(targets),
            "indirect_callsite_count": len(indirect), "indirect_callsite_manifest_sha256": manifest_hash(indirect),
            "indirect_callsites": indirect, "bulk_opcode_hit_count": len(hits), "bulk_opcode_hits": hits,
        },
        "adjudication": {
            "first_direct_callee_bulk_opcode_surface_complete": True,
            "first_direct_callee_bulk_opcode_found": bool(hits),
            "aggregate_or_bulk_alias_stores_ruled_out": False,
            "callee_created_aliases_ruled_out": False,
            "runtime_generated_pointer_stores_ruled_out": False,
            "stored_or_escaped_aliases_ruled_out": False,
            "slot3_writer_provenance_proven": False, "p1_3d_complete": False,
            "p1_3_control_producer_complete": False, "external_provider_count": 7,
        },
        "limits": [
            "This closes x86 REP/MOVS/STOS/LODS/SCAS/CMPS opcodes only in the 82 unique immediate direct callees reached from the 16 carrier bodies.",
            "The two indirect callsites at 0x00770ec4 and 0x00770f41 are inventoried but their runtime targets are not inferred here.",
            "Hand-unrolled scalar/SIMD copies, deeper callees, reconstructed pointers, callbacks and runtime-generated/copied aliases remain open."
        ],
        "next_step": "Trace the two indirect callsites and hand-unrolled copy/store patterns before changing aggregate/runtime alias gates."
    }

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("exe", type=Path); p.add_argument("sqlite", type=Path); p.add_argument("--output", type=Path)
    a = p.parse_args()
    try:
        result = analyze(a.exe, a.sqlite)
    except (ValueError, subprocess.CalledProcessError, sqlite3.Error) as e:
        p.error(str(e))
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if a.output: a.output.write_text(text, encoding="utf-8")
    else: print(text, end="")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
