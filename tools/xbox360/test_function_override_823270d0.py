#!/usr/bin/env python3
"""Guard the full live-observed conditional dispatcher at 0x823270D0."""
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads((ROOT / "evidence/xbox360_function_823270d0.json").read_text())
overrides = tomllib.loads((ROOT / "xbox360/rexglue/nfs_shift_retail_function_overrides.toml").read_text())

entry = int(evidence["guest_address"], 16)
code = bytes.fromhex(evidence["entry_bytes_hex"])
assert len(code) == evidence["capture_length_bytes"] == evidence["function_length_bytes"] == 60
words = [int.from_bytes(code[i : i + 4], "big") for i in range(0, len(code), 4)]
assert words == [
    0x2F050003, 0x419A0024, 0x2F050000, 0x409A000C, 0x2F040000,
    0x419A0014, 0x81630000, 0x814B0088, 0x7D4903A6, 0x4E800420,
    0x81630000, 0x7CA42B78, 0x814B0080, 0x7D4903A6, 0x4E800420,
]
assert entry + 4 + 0x24 == 0x823270F8
assert entry + 12 + 0x0C == 0x823270E8
assert entry + 20 + 0x14 == 0x823270F8
assert evidence["runtime_trap"]["indirect_call_instruction"] == "0x823FA1D4"
assert evidence["runtime_trap"]["indirect_call_return_address"] == "0x823FA1D8"
assert evidence["runtime_trap"]["indirect_target"] == f"0x{entry:08X}"
assert evidence["decoded_instructions"][3] == "bne cr6,0x823270E8"
assert "r5==3 or (r5==0 and r4==0)" in evidence["semantics"]
assert "0x823270D0" in overrides["functions"]
assert overrides["functions"]["0x823270D0"] == {}
print("0x823270D0: all 60 live bytes and both local dispatch branches match the retail override")
