#!/usr/bin/env python3
"""Guard the live-observed field-load thunk at 0x8265BE68."""
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads((ROOT / "evidence/xbox360_function_8265be68.json").read_text())
overrides = tomllib.loads((ROOT / "xbox360/rexglue/nfs_shift_retail_function_overrides.toml").read_text())

entry = int(evidence["guest_address"], 16)
code = bytes.fromhex(evidence["bytes_hex"])
assert len(code) == 8, code.hex()
lwz, branch = (int.from_bytes(code[i : i + 4], "big") for i in range(0, len(code), 4))
assert (lwz >> 26, (lwz >> 21) & 31, (lwz >> 16) & 31, lwz & 0xFFFF) == (32, 3, 3, 0x58)
assert branch >> 26 == 18 and branch & 3 == 0
relative = branch & 0x03FFFFFC
if relative & 0x02000000:
    relative -= 0x04000000
target = (entry + 4 + relative) & 0xFFFFFFFF
assert target == int(evidence["branch_target"], 16) == 0x8265BA78, hex(target)
assert evidence["runtime_fatal"]["indirect_target"] == f"0x{entry:08X}"
assert evidence["runtime_fatal"]["indirect_call_instruction"] == "0x8264B4F4"
assert overrides["functions"].get("0x8265BE68") == {}
print("0x8265BE68: lwz r3,0x58(r3); b 0x8265BA78; ReXGlue override present")
