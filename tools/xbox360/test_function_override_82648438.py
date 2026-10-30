#!/usr/bin/env python3
"""Guard the live-observed store-and-return helper at 0x82648438."""
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads((ROOT / "evidence/xbox360_function_82648438.json").read_text())
overrides = tomllib.loads((ROOT / "xbox360/rexglue/nfs_shift_retail_function_overrides.toml").read_text())

entry = int(evidence["guest_address"], 16)
code = bytes.fromhex(evidence["bytes_hex"])
assert len(code) == 8, code.hex()
stw, blr = (int.from_bytes(code[i : i + 4], "big") for i in range(0, len(code), 4))
assert (stw >> 26, (stw >> 21) & 31, (stw >> 16) & 31, stw & 0xFFFF) == (36, 4, 3, 0x314)
assert blr == 0x4E800020
assert evidence["runtime_fatal"]["indirect_target"] == f"0x{entry:08X}"
assert evidence["runtime_fatal"]["indirect_call_instruction"] == "0x82E2C6C4"
assert overrides["functions"].get("0x82648438") == {}
print("0x82648438: store r4 at object offset +0x314 and return; ReXGlue override present")
