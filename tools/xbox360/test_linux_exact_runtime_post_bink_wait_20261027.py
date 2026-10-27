"""Guard the exact-XEX post-Bink wait and late-input evidence."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_exact_runtime_post_bink_wait_20261027.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-exact-runtime-post-bink-wait.v1"
assert evidence["target"]["title_id"] == "454108B4"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert evidence["binaries"]["runtime_and_plugin_mapped_hashes_verified"] is True

run = evidence["run"]
assert run["guest_memory_modified_by_probe"] is False
assert [pulse["button"] for pulse in run["controller"]["pulses"]] == [
    "Start",
    "A",
    "Start",
]
assert all(pulse["at_seconds"] > 71.762 for pulse in run["controller"]["pulses"])
assert run["controller"]["retail_action_samples"] == 0
assert run["controller"]["host_state_masks_observed"] == ["0x0000"]

wait = evidence["retail_wait"]
assert wait["target_reached"]["progress"] == wait["target_reached"]["target"] == 281
assert wait["counter_guest_address"] == "0xB7368A04"
assert [
    (item["old"], item["new"], item["writer"])
    for item in wait["first_counter_transitions"]
] == [
    ("0x00000000", "0x00000001", "sub_823B31A0"),
    ("0x00000001", "0x00000000", "sub_823B85D0"),
    ("0x00000000", "0xFFFFFFFF", "sub_823B85D0"),
]
assert wait["main_thread_at_final_sample"]["guest_function"] == "sub_823B3850"
assert "while nonzero" in wait["main_thread_at_final_sample"]["retail_loop"]
assert wait["input_and_scene_followthrough"]["retail_start_or_a_predicate_samples"] == 0
assert wait["input_and_scene_followthrough"]["frontend_action_samples"] == 0

trace = ROOT / run["gdb_trace"]["path"]
assert hashlib.sha256(trace.read_bytes()).hexdigest() == run["gdb_trace"]["sha256"]
runner = ROOT / run["runner"]["path"]
assert hashlib.sha256(runner.read_bytes()).hexdigest() == run["runner"]["sha256"]

claims = evidence["interpretation"]["not_proven"]
assert any("full contract" in claim for claim in claims)
assert any("miss the brief zero" in claim for claim in claims)
assert any("main menu" in claim for claim in claims)

print("exact-XEX post-Bink wait evidence preserves observed counter, thread, and claim limits")
