#!/usr/bin/env python3
"""Verify the remaining shallow P1.3D slot3 x87 zero-init candidates."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

FORMAT = "SHIFT.P1D.P13DSlot3X87RemainingClosure/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
REMAINING = [
    "FUN_00766510",
    "FUN_0075c0d0",
    "FUN_007aa940",
    "FUN_007b8630",
    "FUN_0075ada0",
    "FUN_0075afc0",
    "FUN_007876e0",
    "FUN_007ade70",
    "FUN_007b7840",
]

# Exact retail machine anchors for receiver/argument provenance and x87 stores.
EXPECTED = {
    0x0076D118: "mov esi,ecx",
    0x0076D137: "mov ecx,esi",
    0x0076D139: "call 0x766510",
    0x00766531: "fst QWORD PTR [esi+0x40a0]",
    0x00766537: "fst QWORD PTR [esi+0x40a8]",
    0x0076653E: "fst QWORD PTR [esi+0x40b0]",
    0x00766D8B: "fstp QWORD PTR [esi+0x42b0]",
    0x00767498: "fstp QWORD PTR [esi+0x4300]",
    0x00771231: "push 0x0",
    0x00771275: "lea eax,[edi-0x104]",
    0x0077127B: "push eax",
    0x0077127F: "call 0x7b1790",
    0x007B17AE: "mov edi,DWORD PTR [ebx+0x8]",
    0x007B19CF: "mov eax,DWORD PTR [ebx+0xc]",
    0x007B19D2: "test eax,eax",
    0x007B19D4: "je 0x7b19de",
    0x007B19D6: "push eax",
    0x007B19D9: "call 0x75c0d0",
    0x0075C14F: "fstp QWORD PTR [edi+0x10]",
    0x007AAA93: "lea edx,[ebp-0x18]",
    0x007AAA96: "push edx",
    0x007AAA97: "call 0x7aa940",
    0x007AA999: "fst DWORD PTR [esi]",
    0x007AA99B: "fst DWORD PTR [esi+0x4]",
    0x007AA99E: "fstp DWORD PTR [esi+0x8]",
    0x00770FB1: "mov ecx,DWORD PTR [esi+0x339c]",
    0x00770FB7: "call 0x7b8810",
    0x007B8813: "mov ecx,DWORD PTR [esi+0x5c]",
    0x007B8816: "call 0x7b8630",
    0x007B864D: "mov eax,DWORD PTR [edi+0x8]",
    0x007B8650: "mov esi,DWORD PTR [eax+0x18]",
    0x007B86B0: "fst QWORD PTR [esi+0x78]",
    0x007B86E4: "fstp QWORD PTR [esi+0x58]",
    0x00768356: "lea eax,[ebp-0x8]",
    0x0076835C: "push eax",
    0x0076835D: "lea ecx,[ebp-0xc]",
    0x00768360: "push ecx",
    0x00768361: "lea edx,[ebp-0x18]",
    0x00768364: "push edx",
    0x00768365: "lea eax,[ebp-0x24]",
    0x00768368: "push eax",
    0x00768369: "mov ecx,esi",
    0x0076836B: "call 0x75ada0",
    0x0076A2E3: "lea eax,[ebp-0x28]",
    0x0076A2E6: "push eax",
    0x0076A2E7: "lea ecx,[ebp-0x34]",
    0x0076A2EA: "push ecx",
    0x0076A2EB: "lea edx,[ebp-0x4c]",
    0x0076A2EE: "push edx",
    0x0076A302: "call 0x75afc0",
    0x00787745: "lea ecx,[ebp-0xc]",
    0x00787748: "push ecx",
    0x0078774B: "call 0x7876e0",
    0x007876F2: "fst DWORD PTR [eax]",
    0x007876F4: "fstp DWORD PTR [eax+0x4]",
    0x007592AE: "lea ecx,[ebp-0x38]",
    0x007592B1: "push ecx",
    0x007592B4: "call 0x7ade70",
    0x007593E5: "lea eax,[ebp-0x2c]",
    0x007593E8: "push eax",
    0x007593EB: "call 0x7ade70",
    0x007ADF1B: "fst DWORD PTR [esi+0x4]",
    0x007ADF1E: "fstp DWORD PTR [esi+0x8]",
    0x007B82E6: "mov eax,DWORD PTR [esi+0x18]",
    0x007B82ED: "push eax",
    0x007B82EE: "lea ecx,[ebp-0x80]",
    0x007B82F1: "push ecx",
    0x007B82F2: "mov ecx,esi",
    0x007B82F4: "call 0x7b7840",
    0x007B7CDE: "fst QWORD PTR [eax+0x60]",
    0x007B7CF6: "fstp QWORD PTR [eax+0x10]",
}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).lower()


def _disassemble(path: Path) -> dict[int, str]:
    output = subprocess.check_output(
        ["objdump", "-d", "-Mintel", str(path)], text=True, errors="replace"
    )
    rows: dict[int, str] = {}
    pattern = re.compile(r"^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*(.+?)\s*$")
    for line in output.splitlines():
        match = pattern.match(line)
        if match:
            rows[int(match.group(1), 16)] = _norm(match.group(2))
    return rows


def verify(path: Path) -> dict:
    sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    if sha256 != RETAIL_SHA256:
        raise ValueError(f"unexpected SHIFT.exe sha256 {sha256}")

    instructions = _disassemble(path)
    mismatches = []
    for address, expected in EXPECTED.items():
        actual = instructions.get(address)
        if actual != _norm(expected):
            mismatches.append(
                {
                    "address": f"0x{address:08x}",
                    "expected": _norm(expected),
                    "actual": actual,
                }
            )
    if mismatches:
        raise ValueError(f"machine anchor mismatch: {mismatches[:3]}")

    return {
        "format": FORMAT,
        "ready": True,
        "retail_executable_sha256": sha256,
        "candidate_count": len(REMAINING),
        "candidate_functions": REMAINING,
        "verified_machine_anchor_count": len(EXPECTED),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    try:
        payload = verify(args.exe)
    except ValueError as exc:
        parser.error(str(exc))
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
