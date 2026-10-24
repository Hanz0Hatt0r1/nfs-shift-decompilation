#!/usr/bin/env python3
"""Guard the retail writer shared by the registered-callback gate and flag."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_callback_gate_writer_826489d0_20261024.json").read_text()
)

assert evidence["input"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert evidence["input"]["live_elf_sha256"] == (
    "2ffe352bda115285e58661cb5fc5ebe0a8c845d1e7a9ae07bee89e514636c00c"
)

writer = evidence["static_basis"]["writer"]
assert writer["start"] == "0x826489D0"
assert writer["end_exclusive"] == "0x826489F8"
assert writer["instruction_count"] == 10
assert writer["instructions"][2] == ["0x826489D8", "4d9a0020", "bclr 12,26"]
assert writer["stores_on_nonzero_guard"]["callback_gate"]["address"] == (
    "0x83122BA4"
)
assert writer["stores_on_nonzero_guard"]["callback_global_flag"]["address"] == (
    "0x8308D0F0"
)
assert writer["stores_on_nonzero_guard"]["callback_global_flag"]["value"] == (
    "1 if r4==0, otherwise 0"
)

# cntlzw returns 32 only for a zero word. The following rotate/mask extracts
# bit 5 of that count and moves it into output bit 0.
for count in range(33):
    rotated = ((count << 27) | (count >> 5)) & 0xFFFFFFFF
    flag = rotated & 1
    assert flag == (1 if count == 32 else 0)

consumer = evidence["static_basis"]["consumer_fragment"]
assert consumer["start"] == "0x8264A1A4"
assert consumer["end_exclusive"] == "0x8264A1DC"
assert consumer["instruction_count"] == 14
assert consumer["derived_expectation"] == (
    "When global flag is nonzero, comparison target and fallback argument are 2; "
    "when it is zero, both are 0x80000000."
)

runtime = evidence["runtime_context"]
assert runtime["writer_hit_observed"] is False
assert runtime["writer_breakpoint_observation_supplied"] is False
assert "No same-run sample" in runtime["limitation"]
assert evidence["scope"]["frontend_progress_proven"] is False
assert evidence["scope"]["offline_race_proven"] is False

print("retail callback gate writer, zero-input flag derivation, and consumer sentinels match evidence")
