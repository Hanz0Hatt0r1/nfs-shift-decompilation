#!/usr/bin/env python3
"""Guard the live-observed constant-return helper at 0x8233BBE0."""
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads((ROOT / "evidence/xbox360_function_8233bbe0.json").read_text())
overrides = tomllib.loads((ROOT / "xbox360/rexglue/nfs_shift_retail_function_overrides.toml").read_text())

entry = int(evidence["guest_address"], 16)
code = bytes.fromhex(evidence["bytes_hex"])
assert len(code) == 8, code.hex()
li, blr = (int.from_bytes(code[i : i + 4], "big") for i in range(0, len(code), 4))
assert (li >> 26, (li >> 21) & 31, (li >> 16) & 31, li & 0xFFFF) == (14, 3, 0, 22)
assert blr == 0x4E800020
assert evidence["runtime_fatal"]["indirect_target"] == f"0x{entry:08X}"
assert evidence["runtime_fatal"]["indirect_call_instruction"] == "0x8234095C"
assert overrides["functions"].get("0x8233BBE0") == {}
print("0x8233BBE0: li r3,22; blr; ReXGlue override present")
