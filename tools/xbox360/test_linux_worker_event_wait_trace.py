#!/usr/bin/env python3
"""Guard same-run evidence for retail worker event waits before queue stall."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_worker_event_wait_trace_20261026.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-worker-event-wait-trace.v1"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
run = evidence["run"]
assert run["controller_input_sent"] is False
assert run["guest_memory_written_by_probe"] is False
assert run["mapped_hashes_verified_in_inferior"] is True
assert run["binaries"]["rexglue_runtime"]["sha256"] == (
    "2b0d46856da000cecafb46581ddff50da99f549ff335bee9ba489238eed24059"
)
assert run["binaries"]["gpu_plugin"]["sha256"] == (
    "28ad43593d5c5e58920f00a09779b3388e5a9d380a63019c62d1bfdef143a481"
)
script = (ROOT / run["gdb_script"]["path"]).read_bytes()
assert hashlib.sha256(script).hexdigest() == run["gdb_script"]["sha256"]

breakpoints = run["breakpoints"]
assert breakpoints["worker_entry"] == {"resolved": True, "hits": 2}
assert breakpoints["xevent_set"]["resolved"] is True
assert breakpoints["xevent_set"]["all_hits"] > 0
assert breakpoints["xevent_set"]["worker_event_hits"] == 0
assert breakpoints["xevent_pulse"] == {"resolved": True, "worker_event_hits": 0}
assert breakpoints["ke_wait_for_single_object"] == {
    "resolved": True,
    "worker_event_hits": 3,
}
assert breakpoints["producer_823a4758_hits"] == 0
assert breakpoints["registered_callback_82649b68_hits"] == 0
assert breakpoints["first_queue_wait_hits"] == 1

workers = evidence["worker_events"]
assert [worker["worker_guest_object"] for worker in workers] == [
    "0xB7368BE0",
    "0xB7368C30",
]
assert [worker["event_guest_address"] for worker in workers] == [
    "0xB7368C00",
    "0xB7368C50",
]
assert all(worker["header_raw"] == "00000000" for worker in workers)
assert all(worker["signal_state_raw"] == "00000000" for worker in workers)
assert all(worker["wait_reason"] == 3 for worker in workers)
assert all(worker["alertable"] is False for worker in workers)
assert workers[0]["timeout_raw_hex"] == "0xfffffffffffb6c20"
assert workers[0]["timeout_signed_100ns_ticks"] == -300000
assert workers[0]["relative_timeout_ms_before_guest_clock_scaling"] == 30
assert workers[1]["timeout"] == "infinite"

queue = evidence["first_retail_queue_wait"]
assert queue["function"] == "0x823B34A0"
assert queue["head"] == 3 and queue["tail"] == 21
assert queue["predicate_byte"] == "0x14"
assert "another signaling mechanism bypasses XEvent::Set/Pulse" in " ".join(
    evidence["interpretation"]["not_proven"]
)
assert "30ms before guest clock scaling" in " ".join(
    evidence["interpretation"]["supported"]
)
assert "do not synthesize a wakeup" in evidence["interpretation"]["next_p1_step"]

print("retail workers wait on guest events with no observed Set/Pulse before the queue stall")
