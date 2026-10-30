#!/usr/bin/env python3
"""Guard current exact-XEX controller-pipeline evidence without claiming menu entry."""

import json
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_retail_controller_pipeline_current_runtime_20261026.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-retail-controller-pipeline.v1"
assert evidence["retail_image"]["sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
run = evidence["run"]
assert run["guest_memory_modified_by_probe"] is False
assert run["runtime_log"]["guest_fault_logged"] is False
assert evidence["runtime"]["gpu_plugin"]["source_state"].startswith("Local Process 2")
assert evidence["runtime"]["host_executable"]["sha256"] == (
    "610d8f53750cef76ecf3f003c7e6e5e1b9873f9068579b43429a819815a0122a"
)
assert evidence["runtime"]["rexglue_runtime"]["sha256"] == (
    "f43d094797bf30c2e552b244c6ec50e4e69bb0b11fee409e07a812ba74158f78"
)
for key in ("gdb_script", "runner_script"):
    record = run[key]
    actual = hashlib.sha256((ROOT / record["path"]).read_bytes()).hexdigest()
    assert actual == record["sha256"]

input_path = evidence["retail_input_path"]
breakpoints = input_path["runtime_breakpoints"]
assert breakpoints["xam_entry_hits"] == breakpoints["host_get_state_hits"] == 1628
assert breakpoints["host_user0_return_samples"] == 101
assert {
    (sample["packet"], sample["buttons"], sample["status"])
    for sample in breakpoints["successful_non_neutral_transitions"]
} == {
    (3, "0x0010", "0x00000000"),
    (5, "0x1000", "0x00000000"),
}
assert {
    state["current"]
    for state in input_path["retail_update_functions"]["observed_non_neutral_states"]
} == {"0x0010", "0x1000"}
assert input_path["retail_update_functions"]["sub_82308E60_hits"] == 1628
assert input_path["retail_update_functions"]["sub_8230CD00_hits"] == 1628
assert input_path["retail_update_functions"]["candidate_dispatcher_hits"] == 0
assert input_path["retail_update_functions"]["candidate_raw_mask_getter_hits"] == 0

limits = evidence["interpretation"]["not_proven"]
assert any("offline-race entry" in item for item in limits)
assert any("captured no pixels" in item for item in limits)
assert "Do not change XAM input semantics" in evidence["interpretation"]["next_p1_step"]

print("current retail controller trace verifies A/Start reach the edge-update path without claiming frontend entry")
