#!/usr/bin/env python3
"""Verify final four P1.3A shallow x87 zero-init candidates."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from pathlib import Path

RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
RESOLVED = ["FUN_0075c0d0", "FUN_007b8630", "FUN_0075ada0", "FUN_007b7840"]
EXPECTED = {
    0x00771231: "push 0x0", 0x0077127F: "call 0x7b1790",
    0x007B19CF: "mov eax,DWORD PTR [ebx+0xc]", 0x007B19D2: "test eax,eax",
    0x007B19D4: "je 0x7b19de", 0x007B19D9: "call 0x75c0d0",
    0x0075C14F: "fstp QWORD PTR [edi+0x10]",
    0x00768356: "lea eax,[ebp-0x8]", 0x0076835D: "lea ecx,[ebp-0xc]",
    0x00768361: "lea edx,[ebp-0x18]", 0x00768365: "lea eax,[ebp-0x24]",
    0x0076836B: "call 0x75ada0",
    0x0075AE09: "fst DWORD PTR [eax]", 0x0075AE0C: "fst DWORD PTR [eax+0x4]",
    0x0075AE0F: "fst DWORD PTR [eax+0x8]", 0x0075AE15: "fst DWORD PTR [eax]",
    0x0075AE17: "fst DWORD PTR [eax+0x4]", 0x0075AE1A: "fst DWORD PTR [eax+0x8]",
    0x0075AE20: "fst DWORD PTR [eax]",
    0x0076DF6E: "mov esi,ecx", 0x0076DF76: "push 0x60", 0x0076DF7B: "call 0x8868d0",
    0x0076DF91: "call 0x7b3070", 0x0076DFA0: "mov DWORD PTR [esi+0x339c],eax",
    0x007B309D: "mov DWORD PTR [esi],0xb0cd90",
    0x00770FB1: "mov ecx,DWORD PTR [esi+0x339c]", 0x00770FB7: "call 0x7b8810",
    0x007B8813: "mov ecx,DWORD PTR [esi+0x5c]", 0x007B8816: "call 0x7b8630",
    0x007B864B: "mov edi,ecx", 0x007B864D: "mov eax,DWORD PTR [edi+0x8]",
    0x007B8650: "mov esi,DWORD PTR [eax+0x18]",
    0x007B86B0: "fst QWORD PTR [esi+0x78]", 0x007B86B3: "fst QWORD PTR [esi+0x80]",
    0x007B86B9: "fstp QWORD PTR [esi+0x88]", 0x007B86D5: "fst QWORD PTR [esi+0x60]",
    0x007B86D8: "fst QWORD PTR [esi+0x68]", 0x007B86DB: "fst QWORD PTR [esi+0x70]",
    0x007B86DE: "fst QWORD PTR [esi+0x48]", 0x007B86E1: "fst QWORD PTR [esi+0x50]",
    0x007B86E4: "fstp QWORD PTR [esi+0x58]",
    0x007B8721: "mov ecx,DWORD PTR [edi+0x8]", 0x007B8729: "call 0x7b8260",
    0x007B82E6: "mov eax,DWORD PTR [esi+0x18]", 0x007B82F4: "call 0x7b7840",
    0x007B7CDE: "fst QWORD PTR [eax+0x60]", 0x007B7CE4: "fst QWORD PTR [eax+0x8]",
    0x007B7CE7: "fst QWORD PTR [eax+0x10]", 0x007B7CED: "fst QWORD PTR [eax+0x48]",
    0x007B7CF3: "fst QWORD PTR [eax+0x8]", 0x007B7CF6: "fstp QWORD PTR [eax+0x10]",
}
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
    return {"retail_executable_sha256": digest, "checked_site_count": len(checked), "checked_sites": checked, "resolved": RESOLVED}

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__); p.add_argument("executable", type=Path); a = p.parse_args()
    print(json.dumps(verify(a.executable), indent=2, sort_keys=True)); return 0
if __name__ == "__main__": raise SystemExit(main())
