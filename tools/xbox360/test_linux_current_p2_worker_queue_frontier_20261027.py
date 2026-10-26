"""Guard the exact-XEX worker and software-queue frontier with latest P2."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (
        ROOT
        / "evidence/xbox360_linux_current_p2_worker_queue_frontier_20261027.json"
    ).read_text()
)

assert evidence["schema"] == (
    "shift.xbox360.linux-current-p2-worker-queue-frontier.v1"
)
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert evidence["binaries"]["p1_runtime"]["sha256"] == (
    "d8faeb3973a1a2564dea021f19d0418fa718268dadebd414b0006a94a9062253"
)
assert evidence["binaries"]["p2_linux_plugin"]["source_commit"] == (
    "9afec9ead95484a63471912ed2e40c5f043bac46"
)
assert evidence["run"]["mapped_runtime_sha256_verified"] == (
    evidence["binaries"]["p1_runtime"]["sha256"]
)
assert evidence["run"]["mapped_plugin_sha256_verified"] == (
    evidence["binaries"]["p2_linux_plugin"]["sha256"]
)
breakpoints = evidence["run"]["breakpoints"]
assert breakpoints == {
    "worker_entry_hits": 2,
    "worker_event_wait_hits": 2,
    "producer_823a4758_hits_before_queue_wait": 0,
    "registered_callback_82649b68_hits_before_queue_wait": 0,
    "first_queue_wait_hits": 1,
}
workers = evidence["worker_events"]
assert [worker["event_guest_address"] for worker in workers] == [
    "0xB7368C00",
    "0xB7368C50",
]
assert all(worker["header_raw"] == "00000000" for worker in workers)
assert all(worker["signal_state_raw"] == "00000000" for worker in workers)
assert all(worker["wait_reason"] == 3 and not worker["alertable"] for worker in workers)
queue = evidence["first_retail_queue_wait"]
assert (queue["head"], queue["tail"], queue["predicate_byte"]) == (
    3,
    21,
    "0x14",
)
assert queue["completion_mask"] == "0x02"
assert queue["completion_mask_set"] is False
assert evidence["run"]["controller_input_sent"] is False
assert evidence["run"]["guest_memory_modified_by_probe"] is False
assert "do not synthesize signals" in evidence["interpretation"]["next_step"]

print("latest P2 DSO preserves the recorded retail worker/queue frontier")
