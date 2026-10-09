#!/usr/bin/env python3
"""Verify the P1.3A x87 reuse tranche against PC retail SHIFT.exe."""
from __future__ import annotations
import argparse, hashlib, re, subprocess
from pathlib import Path

RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
EXPECTED_SITES = {
    "FUN_00763570": {0x0076379A: "fstp QWORD PTR [edi+0x41d8]", 0x007637DF: "fstp QWORD PTR [edi+0x41d8]"},
    "FUN_00770e80": {0x00770F2F: "fst DWORD PTR [esi+0x4024]", 0x00770F35: "fst DWORD PTR [esi+0x4028]", 0x00770F3B: "fstp DWORD PTR [esi+0x402c]", 0x007712F0: "fst QWORD PTR [esi+0x3ff0]", 0x0077130F: "fstp QWORD PTR [esi+0x4018]"},
    "FUN_00755a60": {0x00755E2E: "fstp QWORD PTR [esi+0x850]"},
    "FUN_00760b50": {0x00760C8A: "fst QWORD PTR [esi+0x8b0]", 0x00760C90: "fst QWORD PTR [esi+0x868]"},
    "FUN_0076e560": {0x0076E97B: "fst QWORD PTR [esi+0x3e58]", 0x0076E9D0: "fstp QWORD PTR [esi+0x3e50]"},
    "FUN_00647a10": {0x00647A5A: "fst QWORD PTR [esi+0xe0]", 0x00647A62: "fstp QWORD PTR [esi+0xf0]", 0x00647AA8: "fstp DWORD PTR [esi+0x104]"},
    "FUN_0070fae0": {0x0070FB99: "fstp QWORD PTR [esi+0x440]", 0x0070FC31: "fst DWORD PTR [esi+0x42c]", 0x0070FC62: "fstp DWORD PTR [esi+0x424]"},
    "FUN_0076f030": {0x0076F03D: "fst QWORD PTR [esi+0x18]"},
    "FUN_0088f110": {0x0088F116: "fst DWORD PTR [esi+0x4]", 0x0088F165: "fst DWORD PTR [esi+0x54]"},
}
REMAINING = (
    "FUN_00766510", "FUN_0075c0d0", "FUN_007aa940", "FUN_007b8630", "FUN_0075ada0",
    "FUN_0075afc0", "FUN_007876e0", "FUN_007ade70", "FUN_007b7840",
)

LINE_RE = re.compile(r"^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([^\s]+)\s*(.*)$")

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()

def verify(executable: Path) -> dict:
    digest=sha256(executable)
    if digest != RETAIL_SHA256: raise ValueError(f"retail hash mismatch: {digest}")
    out=subprocess.run(["objdump","-d","-M","intel",str(executable)],check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
    decoded={}
    for line in out.splitlines():
        m=LINE_RE.match(line)
        if m: decoded[int(m.group(1),16)] = f"{m.group(2)} {m.group(3).strip()}".strip()
    checked=[]
    for function, sites in EXPECTED_SITES.items():
        for address, expected in sites.items():
            actual=decoded.get(address)
            if actual != expected: raise ValueError(f"{address:#x}: expected {expected!r}, got {actual!r}")
            checked.append({"function":function,"site":f"0x{address:08x}","instruction":actual})
    return {"retail_executable_sha256":digest,"checked_site_count":len(checked),"checked_sites":checked,"remaining_candidates":list(REMAINING)}

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("executable",type=Path); a=p.parse_args()
    import json; print(json.dumps(verify(a.executable),indent=2,sort_keys=True)); return 0
if __name__ == "__main__": raise SystemExit(main())
