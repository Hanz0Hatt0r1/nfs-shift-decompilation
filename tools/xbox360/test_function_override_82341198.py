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
probe = evidence["current_exact_xex_probe_20261025"]
assert probe["xex_sha256"] == evidence["xex_sha256"]
assert probe["host_executable_sha256"] == "6a3ac7224c139dced55fe76bd110b3d66a8c1609a1afdfad9514485daf62702b"
assert probe["runtime_override_sha256"] == "81117e5b5127cc2d511131810e6e7fae7130b9e1238e4850650b7366f0ec2c90"
assert probe["gpu_plugin_sha256"] == "badeb5c4052776fafca38fd265ff8c4c6091d1165ccd1da1a1bd385587a60637"
assert probe["duration_seconds"] >= 70
assert probe["input_injected"] is False
assert probe["breakpoint"] == {"guest_address": "0x82341198", "hits": 0}
assert "0x823B34A0" in probe["main_guest_thread_stack_at_interrupt"]
assert "SIGINT after 75 seconds" in probe["termination"]
assert "point-in-time sample" in probe["interpretation"]
assert overrides["functions"]["0x82341198"] == {}
print("0x82341198: live bytes, tail paths, codegen, build, and override match")
