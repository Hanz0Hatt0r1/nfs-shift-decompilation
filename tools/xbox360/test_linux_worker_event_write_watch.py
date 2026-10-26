#!/usr/bin/env python3
"""Guard the bounded retail worker-event write-watch evidence."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_worker_event_write_watch_20261026.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-worker-event-write-watch.v1"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
run = evidence["run"]
assert run["guest_memory_modified_by_probe"] is False
assert run["mapped_hashes_verified_in_inferior"] is False
assert run["binaries"]["host"]["sha256"] == (
    "610d8f53750cef76ecf3f003c7e6e5e1b9873f9068579b43429a819815a0122a"
)
assert run["binaries"]["rexglue_runtime"]["sha256"] == (
    "f43d094797bf30c2e552b244c6ec50e4e69bb0b11fee409e07a812ba74158f78"
)
assert run["binaries"]["gpu_plugin"]["sha256"] == (
    "f1404a4f57fb073f12cc0b34da4f74a3e75d8d6f2ffb49e62708c9a1b09bb6b6"
)
script = (ROOT / run["gdb_script"]["path"]).read_bytes()
assert hashlib.sha256(script).hexdigest() == run["gdb_script"]["sha256"]

watch = evidence["worker_event_state_watch"]
assert watch["watchpoints_installed"] == 2
assert watch["writes_observed"] == 0
assert [event["event_guest_address"] for event in watch["events"]] == [
    "0xB7368C00",
    "0xB7368C50",
]
assert all(event["initial_state"] == "0x00000000" for event in watch["events"])

queue = evidence["retail_queue"]
assert queue["wait_helper"] == "0x823B34A0"
assert queue["minimum_entries_observed"] == 1200
assert queue["first_sample"]["head"] == 3
assert queue["last_sample"]["head"] == 3249
assert queue["last_sample"]["tail"] == 3259
assert queue["sampled_predicate_bytes"] == ["0x14", "0x04"]
assert queue["completion_mask_set_in_samples"] is False
assert "queue advancing" in evidence["interpretation"]["next_p1_step"]

print("retail worker-event states stayed unchanged while the queue head advanced")
