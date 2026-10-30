#!/usr/bin/env python3
"""Guard the live-observed conditional status helper at 0x82BED948."""
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads((ROOT / "evidence/xbox360_function_82bed948.json").read_text())
overrides = tomllib.loads((ROOT / "xbox360/rexglue/nfs_shift_retail_function_overrides.toml").read_text())

entry = int(evidence["guest_address"], 16)
code = bytes.fromhex(evidence["bytes_hex"])
assert len(code) == 16, code.hex()
cmplwi, branch, li, blr = (int.from_bytes(code[i : i + 4], "big") for i in range(0, len(code), 4))

assert ((cmplwi >> 26), (cmplwi >> 23) & 7, (cmplwi >> 21) & 1, (cmplwi >> 16) & 31, cmplwi & 0xFFFF) == (10, 6, 0, 4, 0)
assert branch >> 26 == 16 and (branch >> 21) & 31 == 4 and (branch >> 16) & 31 == 26
assert branch & 3 == 0 and (branch & 0xFFFC) == 12
assert entry + 4 + (branch & 0xFFFC) == 0x82BED958
assert ((li >> 26), (li >> 21) & 31, (li >> 16) & 31, li & 0xFFFF) == (14, 3, 0, 0x25)
assert blr == 0x4E800020
assert evidence["runtime_fatal"]["indirect_target"] == f"0x{entry:08X}"
assert evidence["runtime_fatal"]["indirect_call_instruction"] == "0x82BDEAFc"
assert overrides["functions"].get("0x82BED948") == {}
print("0x82BED948: conditional status helper; ReXGlue override present")
