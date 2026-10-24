#!/usr/bin/env python3
"""Guard the live-observed retail adjustor at 0x8264F570."""
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads((ROOT / "evidence/xbox360_function_8264f570.json").read_text())
overrides = tomllib.loads((ROOT / "xbox360/rexglue/nfs_shift_retail_function_overrides.toml").read_text())

entry = int(evidence["guest_address"], 16)
code = bytes.fromhex(evidence["bytes_hex"])
assert len(code) == 16, code.hex()
words = [int.from_bytes(code[i : i + 4], "big") for i in range(0, len(code), 4)]

mulli, add, addi, branch = words
assert (mulli >> 26) == 7
assert ((mulli >> 21) & 31, (mulli >> 16) & 31, mulli & 0xFFFF) == (11, 4, 0x08A0)
assert (add >> 26) == 31
assert ((add >> 21) & 31, (add >> 16) & 31, (add >> 11) & 31, (add >> 1) & 0x3FF) == (11, 11, 3, 266)
assert (addi >> 26) == 14
assert ((addi >> 21) & 31, (addi >> 16) & 31, addi & 0xFFFF) == (3, 11, 0x1110)
assert branch >> 26 == 18 and branch & 3 == 0
relative = branch & 0x03FFFFFC
if relative & 0x02000000:
    relative -= 0x04000000
target = (entry + 12 + relative) & 0xFFFFFFFF
assert target == int(evidence["branch_target"], 16) == 0x82661C48, hex(target)
assert overrides["functions"].get("0x8264F570") == {}
assert evidence["runtime_fatal"]["indirect_target"] == "0x8264F570"
assert evidence["runtime_fatal"]["indirect_call_instruction"] == "0x82D74DD8"
print("0x8264F570: address adjustor thunk to 0x82661C48; ReXGlue override present")
