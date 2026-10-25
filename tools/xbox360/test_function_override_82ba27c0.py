#!/usr/bin/env python3
"""Guard the exact retail 0x82BA27C0 adjustor thunk and override entry."""
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_function_82ba27c0.json").read_text()
)
overrides = tomllib.loads(
    (ROOT / "xbox360/rexglue/nfs_shift_retail_function_overrides.toml").read_text()
)

assert evidence["guest_address"] == "0x82BA27C0"
assert evidence["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert evidence["entry_bytes_hex"] == "3863fffc4800007c"
assert evidence["function_length_bytes"] == 8

entry = int(evidence["guest_address"], 16)
code = bytes.fromhex(evidence["entry_bytes_hex"])
words = [int.from_bytes(code[i : i + 4], "big") for i in range(0, len(code), 4)]
assert words == [0x3863FFFC, 0x4800007C]
assert evidence["decoded_instructions"] == ["addi r3,r3,-4", "b 0x82BA2840"]

branch = evidence["branch"]
displacement = words[1] & 0x03FFFFFC
if displacement & 0x02000000:
    displacement -= 0x04000000
assert branch["instruction_address"] == f"0x{entry + 4:08X}"
assert branch["displacement"] == f"0x{displacement:X}"
assert branch["target"] == f"0x{entry + 4 + displacement:08X}" == "0x82BA2840"
assert branch["target_has_existing_generated_body"] is True
assert overrides["functions"].get("0x82BA27C0") == {}

validation = evidence["runtime_validation"]
assert validation["codegen"]["generated_function_symbol"] == "sub_82BA27C0"
assert validation["codegen"]["registered_in"] == [
    "nfs_shift_register.cpp",
    "nfs_shift_init.cpp",
]
assert validation["build"]["result"] == "successful"
assert validation["bounded_smoke"]["direct_thunk_hit_observed"] is False
assert evidence["external_report"]["status"] == "unverified_report"

print("0x82BA27C0: exact adjustor-thunk bytes, tail target, and ReXGlue override match evidence")
