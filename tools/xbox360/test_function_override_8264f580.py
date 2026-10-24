#!/usr/bin/env python3
"""Guard the observed retail thunk and the ReXGlue function-discovery override."""
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads((ROOT / "evidence/xbox360_function_8264f580.json").read_text())
overrides = tomllib.loads((ROOT / "xbox360/rexglue/nfs_shift_retail_function_overrides.toml").read_text())
entry = int(evidence["guest_address"], 16)
code = bytes.fromhex(evidence["bytes_hex"])
assert len(code) == 8, code.hex()

li = int.from_bytes(code[:4], "big")
assert li >> 26 == 14 and (li >> 21) & 31 == 6 and (li >> 16) & 31 == 0 and li & 0xffff == 1

branch = int.from_bytes(code[4:], "big")
assert branch >> 26 == 18 and branch & 3 == 0
relative = branch & 0x03fffffc
if relative & 0x02000000:
    relative -= 0x04000000
target = (entry + 4 + relative) & 0xffffffff
assert target == 0x8264D9D0, hex(target)
assert overrides["functions"].get("0x8264F580") == {}
print("0x8264F580: li r6,1; b 0x8264D9D0; ReXGlue override present")
