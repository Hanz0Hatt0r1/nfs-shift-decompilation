#!/usr/bin/env python3
"""Guard the complete live-observed conditional dispatcher at 0x8233D0F8."""
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads((ROOT / "evidence/xbox360_function_8233d0f8.json").read_text())
overrides = tomllib.loads((ROOT / "xbox360/rexglue/nfs_shift_retail_function_overrides.toml").read_text())

entry = int(evidence["guest_address"], 16)
code = bytes.fromhex(evidence["entry_bytes_hex"])
assert len(code) == evidence["capture_length_bytes"] == evidence["function_length_bytes"] == 48
words = [int.from_bytes(code[i : i + 4], "big") for i in range(0, len(code), 4)]
assert words == [
    0x81630040, 0x2B0B0000, 0x419A0018, 0x5563003E,
    0x81630000, 0x814B015C, 0x7D4903A6, 0x4E800420,
    0x81630000, 0x814B01A8, 0x7D4903A6, 0x4E800420,
]
assert entry + 8 + 0x18 == 0x8233D118
assert evidence["runtime_trap"]["indirect_call_instruction"] == "0x8233C860"
assert evidence["runtime_trap"]["indirect_target"] == f"0x{entry:08X}"
assert "0x8233D0F8" in overrides["functions"]
assert overrides["functions"]["0x8233D0F8"] == {}
print("0x8233D0F8: 48 live guest bytes and conditional dispatch paths match the retail override")
