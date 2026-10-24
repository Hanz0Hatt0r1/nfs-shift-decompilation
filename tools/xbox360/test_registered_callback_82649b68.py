#!/usr/bin/env python3
"""Guard retail registered-callback address and state-transition analysis."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_registered_callback_82649b68_20261024.json").read_text()
)

assert evidence["input"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert evidence["input"]["live_elf_sha256"] == (
    "2ffe352bda115285e58661cb5fc5ebe0a8c845d1e7a9ae07bee89e514636c00c"
)

static = evidence["static_basis"]
function = static["function"]
assert function["start"] == "0x82649B68"
assert function["end_exclusive"] == "0x82649C94"
assert function["instruction_count"] == 75
assert function["input_r3"] == "not read before being overwritten at 0x82649B78"
assert function["first_r3_write"]["value"] == "0x83122BB0"
assert function["helper_call"] == "0x82649B7C -> 0x821A7BA8"

state = static["state"]
assert state["base"] == "0x83122B90"
assert state["global_flag"] == "0x8308D0F0"

instructions = static["critical_instructions"]
subtract = instructions["delta_subtract"]
assert subtract["bytes_big_endian"] == "7d291850"
assert subtract["canonical_decode"] == "subf r9,r9,r3"
assert subtract["result"] == "r9 = helper_return_r3 - previous_sample"
assert instructions["delta_accumulate"]["result"] == (
    "r10 = new_delta + previous_delta"
)

assert instructions["global_flag_loads"] == [
    {
        "address": "0x82649C0C",
        "bytes_big_endian": "8148d0f0",
        "effective_address": "0x8308D0F0",
    },
    {
        "address": "0x82649C60",
        "bytes_big_endian": "8148d0f0",
        "effective_address": "0x8308D0F0",
    },
]
assert [item["value"] for item in instructions["global_flag_stores"]] == [0, 1]

thresholds = static["thresholds"]
assert thresholds["selector_zero"]["accepted_range_inclusive"] == [68, 133]
assert thresholds["selector_nonzero"]["accepted_range_inclusive"] == [81, 160]

transitions = static["qualified_transitions"]
assert [item["predicate"] for item in transitions] == [1, 0]
assert [item["counter_field"] for item in transitions] == [
    "0x83122B8C",
    "0x83122B90",
]
assert [item["global_flag_condition"] for item in transitions] == [
    "nonzero",
    "zero",
]
assert [item["global_flag_write"]["value"] for item in transitions] == [0, 1]

runtime = evidence["separately_supplied_runtime_context"]
assert runtime["setter_observation"] == {
    "object": "0xB7365F00",
    "callback": "0x82649B68",
}
assert runtime["breakpoint_observation"]["callback_0x82649B68_hits"] == 0
assert "does not prove permanent unreachability" in runtime["limitation"]

scope = evidence["scope"]
assert scope["invocation_proven"] is False
assert scope["frontend_progress_proven"] is False
assert scope["offline_race_proven"] is False

print("retail callback dataflow, threshold bands, and asymmetric gate transitions match evidence")
