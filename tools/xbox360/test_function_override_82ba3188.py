#!/usr/bin/env python3
"""Guard the live-observed indirect retail entry at 0x82BA3188."""
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads((ROOT / "evidence/xbox360_function_82ba3188.json").read_text())
overrides = tomllib.loads((ROOT / "xbox360/rexglue/nfs_shift_retail_function_overrides.toml").read_text())

entry = int(evidence["guest_address"], 16)
code = bytes.fromhex(evidence["entry_bytes_hex"])
assert len(code) == evidence["capture_length_bytes"] == 16
words = [int.from_bytes(code[i : i + 4], "big") for i in range(0, len(code), 4)]
assert words == [0x81630048, 0x386B0040, 0x816B0040, 0x816B0014]
full = bytes.fromhex(evidence["full_function_bytes_hex"])
assert len(full) == evidence["function_length_bytes"] == 24
full_words = [int.from_bytes(full[i : i + 4], "big") for i in range(0, len(full), 4)]
assert full_words == [0x81630048, 0x386B0040, 0x816B0040, 0x816B0014, 0x7D6903A6, 0x4E800420]
assert evidence["dispatched_indirect_target"] == "0x82B9DD08"
assert evidence["runtime_fatal"]["indirect_target"] == f"0x{entry:08X}"
assert evidence["runtime_fatal"]["indirect_call_instruction"] == "0x82B985EC"
assert evidence["function_length_bytes"] == 24
assert evidence["codegen_reconstruction"][-2:] == ["mtctr r11", "bctr"]
assert overrides["functions"].get("0x82BA3188") == {}
print("0x82BA3188: complete 24-byte dispatch thunk matches live GDB evidence; ReXGlue override present")
