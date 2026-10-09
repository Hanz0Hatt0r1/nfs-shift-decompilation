#!/usr/bin/env python3
"""Verify the second P1.3A x87 zero-init semantic tranche."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from pathlib import Path

RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
EXPECTED = {
    0x0076D137: "mov ecx,esi",
    0x0076D139: "call 0x766510",
    0x0076652F: "mov esi,ecx",
    0x00766531: "fst QWORD PTR [esi+0x40a0]",
    0x00766537: "fst QWORD PTR [esi+0x40a8]",
    0x0076653E: "fst QWORD PTR [esi+0x40b0]",
    0x00766D8B: "fstp QWORD PTR [esi+0x42b0]",
    0x00767498: "fstp QWORD PTR [esi+0x4300]",

    0x007AAA93: "lea edx,[ebp-0x18]",
    0x007AAA96: "push edx",
    0x007AAA97: "call 0x7aa940",
    0x007AA999: "fst DWORD PTR [esi]",
    0x007AA99B: "fst DWORD PTR [esi+0x4]",
    0x007AA99E: "fstp DWORD PTR [esi+0x8]",

    0x0076A2E3: "lea eax,[ebp-0x28]",
    0x0076A2E7: "lea ecx,[ebp-0x34]",
    0x0076A2EB: "lea edx,[ebp-0x4c]",
    0x0076A302: "call 0x75afc0",
    0x0075AFD0: "mov eax,DWORD PTR [ebp+0x14]",
    0x0075AFD3: "fst DWORD PTR [eax]",
    0x0075AFD6: "fst DWORD PTR [eax+0x4]",
    0x0075AFD9: "fst DWORD PTR [eax+0x8]",
    0x0075AFDC: "mov eax,DWORD PTR [ebp+0x18]",
    0x0075AFE7: "mov eax,DWORD PTR [ebp+0x1c]",
    0x0075AFEF: "fstp DWORD PTR [eax+0x8]",

    0x00787745: "lea ecx,[ebp-0xc]",
    0x00787748: "push ecx",
    0x0078774B: "call 0x7876e0",
    0x007876EA: "mov eax,DWORD PTR [ebp+0x8]",
    0x007876F2: "fst DWORD PTR [eax]",
    0x007876F4: "fstp DWORD PTR [eax+0x4]",

    0x007592AE: "lea ecx,[ebp-0x38]",
    0x007592B1: "push ecx",
    0x007592B4: "call 0x7ade70",
    0x007593E5: "lea eax,[ebp-0x2c]",
    0x007593E8: "push eax",
    0x007593EB: "call 0x7ade70",
    0x007ADE96: "mov esi,DWORD PTR [ebp+0x8]",
    0x007ADF1B: "fst DWORD PTR [esi+0x4]",
    0x007ADF1E: "fstp DWORD PTR [esi+0x8]",
}
RESOLVED = ["FUN_00766510", "FUN_007aa940", "FUN_0075afc0", "FUN_007876e0", "FUN_007ade70"]
REMAINING = ["FUN_0075c0d0", "FUN_007b8630", "FUN_0075ada0", "FUN_007b7840"]
LINE_RE = re.compile(r"^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([^\s]+)\s*(.*)$")

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def verify(executable: Path) -> dict:
    digest = sha256(executable)
    if digest != RETAIL_SHA256:
        raise ValueError(f"retail hash mismatch: {digest}")
    text = subprocess.run(["objdump", "-d", "-M", "intel", str(executable)], check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
    decoded = {}
    for line in text.splitlines():
        m = LINE_RE.match(line)
        if m:
            decoded[int(m.group(1), 16)] = f"{m.group(2)} {m.group(3).strip()}".strip()
    checked = []
    for address, expected in EXPECTED.items():
        actual = decoded.get(address)
        if actual != expected:
            raise ValueError(f"{address:#x}: expected {expected!r}, got {actual!r}")
        checked.append({"site": f"0x{address:08x}", "instruction": actual})
    return {"retail_executable_sha256": digest, "checked_site_count": len(checked), "checked_sites": checked, "resolved": RESOLVED, "remaining": REMAINING}

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("executable", type=Path)
    a = p.parse_args()
    print(json.dumps(verify(a.executable), indent=2, sort_keys=True))
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
