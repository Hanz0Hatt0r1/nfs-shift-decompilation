#!/usr/bin/env python3
"""Guard same-run retail frontier evidence for the rebuilt Linux P1 runtime."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (
        ROOT
        / "evidence/xbox360_linux_release_runtime_rebuild_frontier_20261026.json"
    ).read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-release-runtime-rebuild-frontier.v1"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
build = evidence["build"]
assert build["configuration"] == "linux-amd64 Release"
assert build["target"] == "librexruntime.so"
assert build["exit_code"] == 0
assert build["runtime_sha256"] == evidence["run"]["runtime_sha256"]
assert evidence["run"]["mapped_hashes_verified_in_inferior"] is True
assert evidence["run"]["guest_memory_written_by_probe"] is False
assert evidence["run"]["controller_input_sent"] is False

script = (ROOT / evidence["run"]["gdb_script"]["path"]).read_bytes()
assert hashlib.sha256(script).hexdigest() == evidence["run"]["gdb_script"]["sha256"]

breakpoints = evidence["run"]["breakpoints"]
assert breakpoints == {
    "worker_entry_hits": 2,
    "worker_event_wait_hits": 2,
    "producer_823a4758_hits": 0,
    "registered_callback_82649b68_hits": 0,
    "first_queue_wait_hits": 1,
}
assert [worker["event_guest_address"] for worker in evidence["worker_events"]] == [
    "0xB7368C00",
    "0xB7368C50",
]
queue = evidence["first_retail_queue_wait"]
assert queue["head"] == 3 and queue["tail"] == 21
assert queue["predicate_byte"] == "0x14"
assert "does not establish a P1 scheduler defect" in " ".join(
    evidence["interpretation"]["supported"]
)
assert "Keep guest event, queue, and predicate state intact" in evidence[
    "interpretation"
]["next_step"]

print("rebuilt Linux runtime reproduces the exact retail queue-wait frontier")
