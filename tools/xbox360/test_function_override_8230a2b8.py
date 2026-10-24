#!/usr/bin/env python3
"""Guard the live-observed object flag helper at 0x8230A2B8."""
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads((ROOT / "evidence/xbox360_function_8230a2b8.json").read_text())
overrides = tomllib.loads((ROOT / "xbox360/rexglue/nfs_shift_retail_function_overrides.toml").read_text())

entry = int(evidence["guest_address"], 16)
code = bytes.fromhex(evidence["bytes_hex"])
assert len(code) == 16, code.hex()
lwz, oris, stw, blr = (int.from_bytes(code[i : i + 4], "big") for i in range(0, len(code), 4))

assert (lwz >> 26, (lwz >> 21) & 31, (lwz >> 16) & 31, lwz & 0xFFFF) == (32, 11, 3, 84)
assert (oris >> 26, (oris >> 21) & 31, (oris >> 16) & 31, oris & 0xFFFF) == (25, 11, 9, 0x8000)
assert (stw >> 26, (stw >> 21) & 31, (stw >> 16) & 31, stw & 0xFFFF) == (36, 9, 3, 84)
assert blr == 0x4E800020
assert evidence["runtime_fatal"]["indirect_target"] == f"0x{entry:08X}"
assert evidence["runtime_fatal"]["indirect_call_instruction"] == "0x82308AE4"
assert overrides["functions"].get("0x8230A2B8") == {}
print("0x8230A2B8: set field +0x54 bit 31 and return; ReXGlue override present")
