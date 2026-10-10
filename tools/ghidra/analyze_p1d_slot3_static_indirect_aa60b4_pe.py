#!/usr/bin/env python3
"""Resolve and bound the two FUN_00770e80 calls through read-only slot 0x00aa60b4."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from pathlib import Path

FORMAT = "SHIFT.P1D.Slot3StaticIndirectAA60B4Closure/1"
EXE_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
SLOT_VA = 0x00AA60B4
STATIC_TARGET = 0x00778052
CALLSITES = [0x00770EC4, 0x00770F41]
CALL_BYTES_SHA256 = "2660366b05130e6840d03e93764a016366a111012cb1d8e3275fd792df2a6dca"
FRAGMENT = (0x00778052, 0x0077806F, "c4b76757adce88d4cdf64c40b72c934bf5a7a60a0cb5b529f3e5274124ae84d1")
FUN63F350 = (0x0063F350, 154, "078f68e1e3715a4acb0cf375671e6e0164848fbf554641d78cf77292a6b7d0f1")
FUN63F300 = (0x0063F300, 77, "568124aa784f7f57e9f3ca85c78cc524f7673a030db4cc1ff3bbbf6e697078e4")
SLOT_SHA256 = "645ad0d4ac2c159435cb407e7008790d2f26b34c0ef1f47327a44994167d7ba6"
SECTIONS = [
    (0x00401000, 0x006A4489, 0x00000400, ".text", True),
    (0x00AA6000, 0x000DABB7, 0x006A4A00, ".rdata", True),
    (0x00B81000, 0x0003B600, 0x0077F600, ".data", False),
]
INSN_RE = re.compile(r"^\s*([0-9a-f]+):\s+((?:[0-9a-f]{2}\s+)+)\s*(.*)$", re.I)

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def read_va(exe: Path, va: int, size: int) -> tuple[bytes, str, bool]:
    for base, span, off, name, readonly in SECTIONS:
        if base <= va and va + size <= base + span:
            with exe.open("rb") as f:
                f.seek(off + va - base)
                return f.read(size), name, readonly
    raise ValueError(f"VA outside pinned sections: 0x{va:08x}")

def disasm(exe: Path, start: int, stop: int) -> list[dict]:
    out = subprocess.check_output(["objdump", "-d", "-M", "intel", f"--start-address={hex(start)}", f"--stop-address={hex(stop)}", str(exe)], text=True, errors="replace")
    rows = []
    for line in out.splitlines():
        m = INSN_RE.match(line)
        if m:
            rows.append({"address": int(m.group(1), 16), "text": m.group(3).strip()})
    return rows

def esi_sites(rows: list[dict]) -> list[dict]:
    return [r for r in rows if re.search(r"\besi\b", r["text"], re.I)]

def analyze(exe: Path) -> dict:
    digest = sha256_file(exe)
    if digest != EXE_SHA256:
        raise ValueError(f"unexpected SHIFT.exe SHA-256: {digest}")
    slot, section, readonly = read_va(exe, SLOT_VA, 4)
    target = int.from_bytes(slot, "little")
    if sha256_bytes(slot) != SLOT_SHA256 or target != STATIC_TARGET or section != ".rdata" or not readonly:
        raise ValueError("static pointer slot drift")
    for site in CALLSITES:
        b, _, _ = read_va(exe, site, 6)
        if sha256_bytes(b) != CALL_BYTES_SHA256 or b != bytes.fromhex("ff15b460aa00"):
            raise ValueError(f"callsite drift at 0x{site:08x}")
    fs, fe, fh = FRAGMENT
    frag, _, _ = read_va(exe, fs, fe - fs)
    if sha256_bytes(frag) != fh:
        raise ValueError("0x00778052 fragment drift")
    f350, _, _ = read_va(exe, FUN63F350[0], FUN63F350[1])
    f300, _, _ = read_va(exe, FUN63F300[0], FUN63F300[1])
    if sha256_bytes(f350) != FUN63F350[2] or sha256_bytes(f300) != FUN63F300[2]:
        raise ValueError("callee body drift")
    frag_rows = disasm(exe, fs, fe)
    r350 = disasm(exe, FUN63F350[0], FUN63F350[0] + FUN63F350[1])
    r300 = disasm(exe, FUN63F300[0], FUN63F300[0] + FUN63F300[1])
    if len(frag_rows) != 9 or len(r350) != 62 or len(r300) != 34:
        raise ValueError("instruction-count drift")
    frag_esi = esi_sites(frag_rows)
    e350 = esi_sites(r350)
    e300 = esi_sites(r300)
    if [(r["address"], r["text"]) for r in frag_esi] != [
        (0x00778056, "mov    ecx,esi"), (0x0077806C, "or     esi,0xffffffff")
    ]:
        raise ValueError("fragment ESI-use drift")
    # Exact root arrives in ESI from merged FUN_00770e80 carrier proof. Before the clobber it is only moved to ECX.
    if any("push   esi" in r["text"] or ("[" in r["text"] and r["text"].endswith(",esi")) for r in frag_esi if r["address"] < 0x0077806C):
        raise ValueError("unexpected exact-root persistence in fragment")
    # FUN_0063f350 receives exact root in ECX, copies it to ESI, forwards once to FUN_0063f300, then overwrites ESI on the success path.
    expected_350 = {0x0063F357,0x0063F359,0x0063F35F,0x0063F367,0x0063F37B,0x0063F382,0x0063F399,0x0063F3C5,0x0063F3CC,0x0063F3D3,0x0063F3D5,0x0063F3E6}
    if {r["address"] for r in e350} != expected_350:
        raise ValueError("FUN_0063f350 ESI-use drift")
    # FUN_0063f300 receives exact root in ECX, reads fields, then replaces ESI with its output argument before any push/store of ESI.
    expected_300 = {0x0063F304,0x0063F306,0x0063F30C,0x0063F314,0x0063F327,0x0063F329,0x0063F330,0x0063F337,0x0063F339,0x0063F348}
    if {r["address"] for r in e300} != expected_300:
        raise ValueError("FUN_0063f300 ESI-use drift")
    return {
        "format": FORMAT, "version": 1, "ready": True, "owner": "Process 1D / P1.3D",
        "authority": {"platform": "PC retail 1.02", "retail_executable_sha256": digest, "machine_bytes_adjudicate": True},
        "static_slot": {"address": "0x00aa60b4", "section": section, "section_readonly_in_image": readonly, "value": "0x00778052", "value_sha256": SLOT_SHA256},
        "callsites": [{"address": f"0x{x:08x}", "encoding": "ff 15 b4 60 aa 00", "caller_exact_root_register": "ESI=HDVehicle"} for x in CALLSITES],
        "target_chain": {
            "static_target": "0x00778052 (interior of FUN_00777fe0)",
            "target_fragment_instruction_count": len(frag_rows), "target_fragment_sha256": FRAGMENT[2],
            "target_fragment_exact_root_forward": "0x00778056 ECX=ESI -> 0x0077805b FUN_0063f350",
            "target_fragment_exact_root_clobber": "0x0077806c ESI=-1",
            "fun0063f350_instruction_count": len(r350), "fun0063f350_sha256": FUN63F350[2],
            "fun0063f350_exact_root_forward": "0x0063f37b ECX=ESI -> 0x0063f37d FUN_0063f300",
            "fun0063f300_instruction_count": len(r300), "fun0063f300_sha256": FUN63F300[2],
            "selected_wheel_root_materialization_found": False, "exact_root_persistent_store_found": False,
        },
        "adjudication": {
            "fun00770e80_aa60b4_static_indirect_subset_complete": True,
            "aa60b4_runtime_unknown_target": False,
            "aa60b4_exact_hdvehicle_root_persistent_store_found": False,
            "aa60b4_selected_wheel_alias_found": False,
            "other_indirect_entry_ruled_out": False, "callee_created_aliases_ruled_out": False,
            "runtime_generated_pointer_stores_ruled_out": False, "stored_or_escaped_aliases_ruled_out": False,
            "slot3_writer_provenance_proven": False, "p1_3d_complete": False,
            "p1_3_control_producer_complete": False, "external_provider_count": 7,
        },
        "limits": [
            "This closes only the two FUN_00770e80 call-through-memory sites that use image slot 0x00aa60b4.",
            "Read-only is an image-section property; arbitrary runtime code patching is not globally ruled out.",
            "The target is an interior entry that inherits caller ESI/EBP state; no generic function-entry equivalence is assumed.",
            "Other indirect calls, callbacks, reconstructed pointers and runtime-generated/copied aliases remain open."
        ],
        "next_step": "Continue with other indirect/callback entry surfaces and hand-unrolled pointer-copy patterns before changing global alias gates."
    }

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__); p.add_argument("exe", type=Path); p.add_argument("--output", type=Path); a=p.parse_args()
    try: result=analyze(a.exe)
    except (ValueError, subprocess.CalledProcessError) as e: p.error(str(e))
    text=json.dumps(result, indent=2, sort_keys=True)+"\n"
    if a.output: a.output.write_text(text, encoding="utf-8")
    else: print(text,end="")
    return 0
if __name__ == "__main__": raise SystemExit(main())
