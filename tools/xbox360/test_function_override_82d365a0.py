#!/usr/bin/env python3
"""Guard the live-observed indirect retail entry at 0x82D365A0."""
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads((ROOT / "evidence/xbox360_function_82d365a0.json").read_text())
overrides = tomllib.loads((ROOT / "xbox360/rexglue/nfs_shift_retail_function_overrides.toml").read_text())

entry = int(evidence["guest_address"], 16)
code = bytes.fromhex(evidence["entry_bytes_hex"])
assert len(code) == evidence["function_length_bytes"] == 28
words = [int.from_bytes(code[i : i + 4], "big") for i in range(0, len(code), 4)]
assert words == [0x81440000, 0x7C8B2378, 0x7C641B78, 0x7D635B78, 0x816A005C, 0x7D6903A6, 0x4E800420]
assert evidence["runtime_fatal"]["indirect_target"] == f"0x{entry:08X}"
assert evidence["runtime_fatal"]["indirect_call_instruction"] == "0x823F3C00"
assert evidence["dispatched_indirect_target"] == "0x8265BE68"
assert overrides["functions"].get("0x82D365A0") == {}
print("0x82D365A0: complete 28-byte vtable-dispatch thunk matches live GDB evidence; ReXGlue override present")
