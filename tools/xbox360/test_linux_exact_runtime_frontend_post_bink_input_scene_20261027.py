#!/usr/bin/env python3
"""Guard exact-XEX post-Bink scene, input, and retail wait evidence."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_exact_runtime_frontend_post_bink_input_scene_20261027.json")
    .read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-exact-runtime-frontend-post-bink-input-scene.v1"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
binaries = evidence["binaries"]
assert binaries["p1_host_sha256"] == (
    "ff4278b3df0957d31870c933a001e2d8df4d7ced2149053f773c7fdb39087178"
)
assert binaries["p1_runtime_sha256"] == (
    "4d0fb82223695d3e2b76bbc6d6c9a93bad525a4c051a8a2eb585b5422d2373bc"
)
assert binaries["inferior_mapped_hashes_verified"] is True

run = evidence["run"]
assert run["guest_memory_modified_by_probe"] is False
target_elapsed = run["frontend"]["bink_target_reached_seconds"]
pulses = run["controller"]["pulses"]
assert [pulse["button"] for pulse in pulses] == ["Start", "A", "Start"]
assert all(pulse["down_seconds"] > target_elapsed for pulse in pulses)
assert run["controller"]["all_pulses_after_bink_target"] is True
assert run["controller"]["retail_action_predicates"] == {
    "Start_samples": 18,
    "Start_true_samples": 18,
    "A_samples": 0,
}
assert run["controller"]["retail_controller_masks"]["Start_current_mask"] == "0x0010"
assert run["controller"]["retail_controller_masks"]["A_current_mask_observed"] is False

scene = run["frontend"]["scene_update"]
assert run["frontend"]["bink_progress"] == "281/281"
assert scene["function"] == "sub_82DDC6F0"
assert scene["result"] == 1
assert scene["counter_after"] == scene["counter_before"] + 1
assert run["frontend"]["main_menu_observed"] is False
assert run["frontend"]["race_observed"] is False

wait = evidence["retail_wait_static_crosscheck"]
assert wait["function"] == "sub_823B3850"
assert wait["counter_field_offset"] == 11012
assert wait["condition"] == "load manager+11012; branch back while signed value is nonzero"
assert wait["live_counter_read_in_this_capture"] is False

main = run["final_threads"]["retail_main"]
assert main["thread_name"] == "Core 0/0: Main"
assert main["top_frame"] == "sub_823B3850"
assert evidence["retail_code_dump_and_ghidra"]["ppc_big_endian_prologue_matches_retail_disassembly"] is True
assert evidence["retail_code_dump_and_ghidra"]["ghidra_raw_import"]["analysis_reported_success"] is True
assert evidence["retail_code_dump_and_ghidra"]["ghidra_raw_import"]["functions_exported"] == 0

for item in (run["gdb_trace"], evidence["retail_code_dump_and_ghidra"]["capture_script"]):
    assert hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest() == item["sha256"]
runner = ROOT / run["gdb_trace"]["runner_path"]
assert hashlib.sha256(runner.read_bytes()).hexdigest() == run["gdb_trace"]["runner_sha256"]

print("exact-XEX post-Bink trace confirms Start delivery and the original retail wait; menu and race remain unobserved")
