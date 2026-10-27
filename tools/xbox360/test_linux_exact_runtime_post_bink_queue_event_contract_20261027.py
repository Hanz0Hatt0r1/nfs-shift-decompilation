"""Guard exact-XEX queue/event evidence and its claim limits."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_exact_runtime_post_bink_queue_event_contract_20261027.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-exact-runtime-post-bink-queue-event-contract.v1"
assert evidence["target"]["title_id"] == "454108B4"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)

binaries = evidence["binaries"]
assert binaries["input_files_sha256_verified"] is True
assert binaries["runtime_and_plugin_inferior_mapped_hashes_verified"] is True

run = evidence["run"]
assert run["duration_seconds"] == 40.739
assert run["guest_memory_modified_by_probe"] is False
assert run["termination"].startswith("GDB detached and sent SIGINT")
assert run["controller"]["all_pulses_preceded_bink_target"] is True
assert run["controller"]["retail_action_consumption_traced"] is False

queue = evidence["retail_queue"]
assert queue["bink_target_reached"]["progress"] == queue["bink_target_reached"]["target"] == 281
assert queue["bink_target_reached"]["elapsed_seconds"] == 25.367
assert queue["manager_guest_object"] == "0xB7365F00"
assert queue["manager_guest_object"] != queue["worker_guest_object"]
assert int(queue["manager_guest_object"], 16) + queue["manager_counter_offset"] == int(
    queue["counter_guest_address"], 16
)
assert int(queue["worker_guest_object"], 16) + queue["worker_counter_offset"] == int(
    queue["counter_guest_address"], 16
)

producer = queue["producer"]
assert producer["entry_count"] == 772
assert producer["entries_with_nonzero_counter_delta"] == 2
assert producer["nonzero_delta_sample"]["delta"] == 1
assert [sample["entry"] for sample in producer["nonzero_delta_samples"]] == [754, 765]

enqueue = queue["callback_enqueue"]
assert enqueue["entry_count"] == 215
assert enqueue["first_queue_event_pair_matches"] == 24

worker = queue["worker"]
ring = worker["ring_queue"]
assert ring["guest_object"] == "0xB7368BE0"
assert ring["producer_index_offset"] == 56
assert ring["consumer_index_offset"] == 60
assert "increments +60" in ring["index_roles_static_crosscheck"]
samples = ring["sampled_handler_entries"]
assert len(samples) == 12
assert [(sample["producer"], sample["consumer"]) for sample in samples[:4]] == [
    (1, 1), (2, 2), (3, 2), (4, 2)
]
assert [sample["stream"] for sample in samples[:4]] == [
    "0xB7368A18", "0xC9691278", "0xC967E654", "0xC969D2F8"
]
assert [sample["field72"] for sample in samples[:4]] == [
    "0xC9684914", "0x00000000", "0x00000000", "0x00000000"
]
assert samples[2]["token"] == "0xC969D2EC"
assert samples[3]["token"] == "0xC96912F0"
assert worker["matching_completion_handler_entries"] == 218
assert worker["entry_token_counts"] == {
    "0xC0000000": 216,
    "0xC969D2EC": 1,
    "0xC96912F0": 1,
}
assert worker["counter_watchpoint_write_count"] == 109
assert worker["first_counter_writes"] == [
    "0x00000001", "0x00000000", "0x00000000", "0x00000000", "0xFFFFFFFF"
]
assert worker["event_api_entry_counts"] == {
    "KeSetEvent": 214,
    "KeResetEvent": 214,
    "KeWaitForSingleObject": 171,
}
assert "only when worker+72 is zero" in worker["retail_static_crosscheck"]["counter_condition"]

main = queue["final_thread_snapshot"]
assert main["guest_function"] == "sub_823B3850"
assert main["host_frame"].endswith("nfs_shift_recomp.167.cpp:4994")
assert "while it is nonzero" in main["retail_loop"]
assert main["counter_value_read_at_final_snapshot"] is False
assert queue["gpu_thread_snapshot"]["host_thread"] == "SHIFT Native GP"

for artifact in (run["gdb_trace"], run["runner"]):
    path = ROOT / artifact["path"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"]

claims = evidence["interpretation"]["not_proven"]
assert any("P1 event/scheduler emulation" in claim for claim in claims)
assert any("controller pulses were consumed" in claim for claim in claims)
assert any("visible main menu" in claim for claim in claims)

print("exact-XEX queue evidence preserves worker underflow, main wait, and attribution limits")
