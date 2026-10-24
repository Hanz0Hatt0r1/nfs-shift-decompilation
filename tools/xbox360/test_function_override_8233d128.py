#!/usr/bin/env python3
"""Guard the complete live-observed conditional dispatcher at 0x8233D128."""
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads((ROOT / "evidence/xbox360_function_8233d128.json").read_text())
overrides = tomllib.loads((ROOT / "xbox360/rexglue/nfs_shift_retail_function_overrides.toml").read_text())

entry = int(evidence["guest_address"], 16)
code = bytes.fromhex(evidence["entry_bytes_hex"])
assert len(code) == evidence["capture_length_bytes"] == evidence["function_length_bytes"] == 48
words = [int.from_bytes(code[i : i + 4], "big") for i in range(0, len(code), 4)]
assert words == [
    0x81630040, 0x2B0B0000, 0x419A0018, 0x5563003E,
    0x81630000, 0x814B0164, 0x7D4903A6, 0x4E800420,
    0x81630000, 0x814B01B0, 0x7D4903A6, 0x4E800420,
]
assert entry + 8 + 0x18 == 0x8233D148
assert evidence["runtime_fatal"]["indirect_target"] == f"0x{entry:08X}"
assert evidence["runtime_fatal"]["indirect_call_instruction"] == "0x82328C44"
assert "0x8233D128" in overrides["functions"]
assert overrides["functions"]["0x8233D128"] == {}
assert evidence["codegen_validation"]["runtime_execution"].endswith("0x8233D0F8, where the next InvalidFunctionTrap occurred.")
print("0x8233D128: 48 live guest bytes, runtime dispatch, and override match")
