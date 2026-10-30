#!/usr/bin/env python3
"""Guard exact-XEX A-first retail input evidence."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_exact_runtime_frontend_a_first_20261027.json")
    .read_text()
)

assert evidence["schema"] == (
    "shift.xbox360.linux-exact-runtime-frontend-a-first-controller.v1"
)
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
binaries = evidence["binaries"]
assert binaries["p1_host"]["sha256"] == (
    "ff4278b3df0957d31870c933a001e2d8df4d7ced2149053f773c7fdb39087178"
)
assert binaries["rexglue_runtime"]["sha256"] == (
    "4d0fb82223695d3e2b76bbc6d6c9a93bad525a4c051a8a2eb585b5422d2373bc"
)
assert binaries["p2_linux_plugin"]["sha256"] == (
    "771201891a6ae28c0745f57beccf9c6474ce175c7bb3f5edadcce4c457a8a12b"
)
assert binaries["inferior_mapped_hashes_verified"] is True

run = evidence["run"]
assert run["guest_memory_modified_by_probe"] is False
controller = run["controller"]
target = controller["bink_target_reached_seconds"]
pulses = controller["pulses"]
assert [pulse["button"] for pulse in pulses] == ["A", "Start", "A"]
assert all(pulse["down_seconds"] > target for pulse in pulses)
assert controller["all_pulses_after_bink_target"] is True
input_path = controller["retail_input_observation"]
assert input_path["A_current_mask"] == "0x1000"
assert input_path["A_button_bytes_observed"] == ["0x80", "0xC0"]
assert input_path["A_predicate_samples"] == 18
assert input_path["first_six_logged_A_predicate_results"] == [1] * 6
assert input_path["Start_mask_change_observed"] is False
assert input_path["Start_predicate_samples"] == 0

frontend = run["frontend"]
assert frontend["bink_progress"] == "281/281"
assert frontend["main_menu_observed"] is False
assert frontend["race_observed"] is False
main = run["final_threads"]["retail_main"]
assert main["thread_name"] == "Core 0/0: Main"
assert main["top_frame"] == "sub_823B3850"

artifacts = run["trace_artifacts"]
for key in ("runner", "gdb_script"):
    item = artifacts[key]
    assert hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest() == item["sha256"]

print("exact-XEX A-first run reaches the retail A predicate; menu and race remain unobserved")
