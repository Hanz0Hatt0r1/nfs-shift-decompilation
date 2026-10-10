#!/usr/bin/env python3
"""Bound direct x86 bulk/string-copy opcodes inside the 16 exact-root carriers."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from pathlib import Path

FORMAT = "SHIFT.P1D.Slot3SixteenCarrierBulkOpcodeClosure/1"
EXE_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
SPECS = {
    "FUN_00752fc0": (0x00752FC0, 37), "FUN_00755950": (0x00755950, 66),
    "FUN_00755a60": (0x00755A60, 1297), "FUN_00755f80": (0x00755F80, 132),
    "FUN_00758810": (0x00758810, 347), "FUN_00758b50": (0x00758B50, 1136),
    "FUN_00758fc0": (0x00758FC0, 364), "FUN_00760b50": (0x00760B50, 531),
    "FUN_00763570": (0x00763570, 3276), "FUN_00765c40": (0x00765C40, 2248),
    "FUN_00766510": (0x00766510, 4310), "FUN_007675f0": (0x007675F0, 1340),
    "FUN_007682c0": (0x007682C0, 335), "FUN_00769ef0": (0x00769EF0, 774),
    "FUN_0076d100": (0x0076D100, 508), "FUN_00770e80": (0x00770E80, 1183),
}
EXPECTED_INSTRUCTIONS = {
    "FUN_00752fc0": 7, "FUN_00755950": 19, "FUN_00755a60": 393, "FUN_00755f80": 46,
    "FUN_00758810": 114, "FUN_00758b50": 323, "FUN_00758fc0": 118, "FUN_00760b50": 146,
    "FUN_00763570": 971, "FUN_00765c40": 647, "FUN_00766510": 1128, "FUN_007675f0": 436,
    "FUN_007682c0": 121, "FUN_00769ef0": 252, "FUN_0076d100": 142, "FUN_00770e80": 315,
}
BULK_RE = re.compile(r"\b(?:rep|repe|repz|repne|repnz)\b|\b(?:movs|stos|lods|scas|cmps)[bwdq]?\b", re.I)
INSN_RE = re.compile(r"^\s*([0-9a-f]+):\s", re.I)

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def disasm(exe: Path, start: int, size: int) -> list[str]:
    cmd = ["objdump", "-d", "-M", "intel", f"--start-address={hex(start)}", f"--stop-address={hex(start+size)}", str(exe)]
    out = subprocess.check_output(cmd, text=True, errors="replace")
    return [line.strip() for line in out.splitlines() if INSN_RE.match(line)]

def analyze(exe: Path) -> dict:
    digest = sha256(exe)
    if digest != EXE_SHA256:
        raise ValueError(f"unexpected SHIFT.exe SHA-256: {digest}")
    functions = {}
    hits = []
    for name, (start, size) in SPECS.items():
        lines = disasm(exe, start, size)
        if len(lines) != EXPECTED_INSTRUCTIONS[name]:
            raise ValueError(f"instruction-count drift for {name}: {len(lines)}")
        local_hits = [line for line in lines if BULK_RE.search(line.split("\t")[-1])]
        functions[name] = {"start": f"0x{start:08x}", "size": size, "instruction_count": len(lines), "bulk_opcode_hits": local_hits}
        hits.extend({"function": name, "instruction": line} for line in local_hits)
    return {
        "format": FORMAT, "version": 1, "ready": True, "owner": "Process 1D / P1.3D",
        "authority": {"platform": "PC retail 1.02", "retail_executable_sha256": digest, "machine_bytes_adjudicate": True},
        "scope": {"carrier_count": len(SPECS), "instruction_count": sum(x["instruction_count"] for x in functions.values()), "functions": functions},
        "direct_bulk_opcode_surface": {"hit_count": len(hits), "hits": hits, "rep_prefixed_or_x86_string_opcode_found": bool(hits)},
        "adjudication": {
            "machine_direct_bulk_opcode_16_carrier_subset_complete": True,
            "machine_direct_bulk_opcode_found": bool(hits),
            "aggregate_or_bulk_alias_stores_ruled_out": False,
            "runtime_generated_pointer_stores_ruled_out": False,
            "stored_or_escaped_aliases_ruled_out": False,
            "slot3_writer_provenance_proven": False,
            "p1_3d_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only direct REP-prefixed and x86 MOVS/STOS/LODS/SCAS/CMPS opcode forms inside the 16 pinned carrier bodies.",
            "Call-based memcpy/memmove helpers, hand-unrolled scalar/SIMD copies, reconstructed pointers, callbacks and indirect entry remain open.",
            "Zero string-opcode hits are not promoted to a global no-aggregate-copy claim.",
        ],
        "next_step": "Inventory direct callees and hand-unrolled copy patterns that could persist reconstructed selected-wheel aliases before changing aggregate/runtime storage gates.",
    }

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("exe", type=Path)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    try:
        result = analyze(a.exe)
    except (ValueError, subprocess.CalledProcessError) as e:
        p.error(str(e))
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if a.output:
        a.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
