#!/usr/bin/env python3
"""Guard the live-observed Xbox 360 dispatcher at 0x82341198."""
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads((ROOT / "evidence/xbox360_frontier_82341198.json").read_text())
overrides = tomllib.loads(
    (ROOT / "xbox360/rexglue/nfs_shift_retail_function_overrides.toml").read_text()
)

entry = int(evidence["guest_address"], 16)
code = bytes.fromhex(evidence["entry_bytes_hex"])
assert len(code) == evidence["capture_length_bytes"] == 68
assert evidence["function_extent_verified"] is True
words = [int.from_bytes(code[i : i + 4], "big") for i in range(0, len(code), 4)]
assert words == [
    0x81630008, 0x2B0B0003, 0x4D990020, 0x7D6903A6, 0x2F0B0000,
    0x405A000C, 0x405A0010, 0x409A000C, 0x38800014, 0x4BFEABCC,
    0x3D60831B, 0x38800000, 0x816B300C, 0x2B0B0000, 0x419A0008,
    0x4BFEAFAC, 0x4BFEAF68,
]

def sign_extend(value, bits):
    sign = 1 << (bits - 1)
    return value - (1 << bits) if value & sign else value

def b_target(pc, word):
    assert word >> 26 == 16 and not word & 2  # relative B-form, AA=0
    return (pc + sign_extend(word & 0xFFFC, 16)) & 0xFFFFFFFF

def i_target(pc, word):
    assert word >> 26 == 18 and not word & 2  # relative I-form, AA=0
    return (pc + sign_extend(word & 0x03FFFFFC, 26)) & 0xFFFFFFFF

# The CTR-zero/CR6.EQ-false branches and CR6.EQ-false branch split values
# 0-1 from 2-3 after the upper-bound check.
assert (words[2] >> 21) & 0x1F == 12 and (words[2] >> 16) & 0x1F == 25
assert (words[5] >> 21) & 0x1F == 2 and (words[5] >> 16) & 0x1F == 26
assert (words[6] >> 21) & 0x1F == 2 and (words[6] >> 16) & 0x1F == 26
assert (words[7] >> 21) & 0x1F == 4 and (words[7] >> 16) & 0x1F == 26
assert b_target(entry + 20, words[5]) == 0x823411B8
assert b_target(entry + 24, words[6]) == 0x823411C0
assert b_target(entry + 28, words[7]) == 0x823411C0
assert i_target(entry + 36, words[9]) == 0x8232BD88
assert b_target(entry + 56, words[14]) == 0x823411D8
assert i_target(entry + 60, words[15]) == 0x8232C180
assert i_target(entry + 64, words[16]) == 0x8232C140
assert evidence["control_flow"]["tail_branches_set_link_register"] is False
assert evidence["control_flow"]["tail_targets_registered_in_matching_codegen_partition"] == [
    "0x8232BD88", "0x8232C140", "0x8232C180"
]
assert evidence["control_flow"]["states_0_or_1"]["r4"] == 20
assert evidence["control_flow"]["states_2_or_3"]["r4"] == 0
assert evidence["control_flow"]["states_2_or_3"]["selector_address"] == "0x831B300C"
assert evidence["codegen_validation"]["generated_symbol"] == "sub_82341198"
assert evidence["codegen_validation"]["next_registered_entry"] == "0x823411DC"
assert evidence["build_validation"]["result"] == "success"
assert evidence["postbuild_runtime_attempt"]["entered_xstart"] is True
assert evidence["postbuild_runtime_attempt"]["entered_82341198"] is False
assert overrides["functions"]["0x82341198"] == {}
print("0x82341198: live bytes, tail paths, codegen, build, and override match")
