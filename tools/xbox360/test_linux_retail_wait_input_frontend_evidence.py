#!/usr/bin/env python3
"""Guard the input-correlated retail wait snapshot and its claim boundaries."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_retail_wait_input_frontend_20261026.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-retail-wait-input-frontend.v1"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert evidence["binaries"]["host"]["mapping_verified"] is True
assert evidence["binaries"]["rexglue_runtime"]["mapping_verified"] is True
assert evidence["binaries"]["gpu_plugin"]["mapping_verified"] is True

run = evidence["run"]
assert run["exit_code"] == 0
assert run["gdb"]["guest_data_written"] is False
assert [pulse["button"] for pulse in run["controller"]["pulses"]] == ["A", "Start", "A"]
assert run["controller"]["same_run_retail_consumption_proven"] is False

captures = run["window_captures"]["captures"]
assert len(captures) == 3
assert len({capture["sha256"] for capture in captures}) == 1
assert run["window_captures"]["same_safety_disclaimer_frame"] is True

queue = evidence["retail_queue"]
assert queue["head"] <= queue["wait_target_decimal"] < queue["tail"]
assert queue["wait_target_decimal"] == 5523
assert queue["head"] == 5515 and queue["tail"] == 5525
assert int(queue["predicate"], 16) & int(queue["tested_completion_mask"], 16) == 0
assert queue["global_831B3820"] == "0x00000000"
assert queue["call_chain_top_down"][:4] == [
    "sub_823A0310", "sub_823B34A0", "sub_823B3850", "sub_823A0760"
]

frame = evidence["runtime_activity"]["frame_400"]
assert frame["non_black_rgb_pixels"] == 920156
assert frame["max_abs_8bit_rgb_channel_difference"] == 0
assert frame["mse_rgb"] == 0.0
assert evidence["runtime_activity"]["copy_convert_accepts"] == 1201
assert evidence["runtime_activity"]["draw_submission_entries"] == 1202

not_proven = evidence["interpretation"]["not_proven"]
assert any("consumed" in claim for claim in not_proven)
assert any("which producer/completion callback" in claim for claim in not_proven)
assert any("offline race" in claim for claim in not_proven)

print("retail wait/input evidence and claim boundaries are internally consistent")
