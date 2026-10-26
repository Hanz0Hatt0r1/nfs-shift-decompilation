#!/usr/bin/env python3
"""Guard the hash-verified current Linux retail worker/queue frontier."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_current_runtime_frontier_20261027.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-current-runtime-retail-frontier.v1"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
run = evidence["run"]
assert run["mapped_hashes_verified_in_inferior"] is True
assert run["controller_input_sent"] is False
assert run["guest_memory_written_by_probe"] is False
script = (ROOT / run["gdb_script"]["path"]).read_bytes()
assert hashlib.sha256(script).hexdigest() == run["gdb_script"]["sha256"]

assert run["breakpoints"] == {
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
assert (queue["head"], queue["tail"], queue["predicate_byte"]) == (3, 21, "0x14")
assert queue["completion_mask_set"] is False
assert evidence["binaries"]["rexglue_runtime"]["sha256"] == (
    "d8faeb3973a1a2564dea021f19d0418fa718268dadebd414b0006a94a9062253"
)
assert evidence["binaries"]["gpu_plugin"]["sha256"] == (
    "f4da45fa6d72dae885d7cac942c7b8a7db1f1ea11094cad6438f96c036f2e4fd"
)
assert "Preserve the retail worker events and queue predicate" in evidence[
    "interpretation"
]["next_step"]

print("current Linux runtime reproduces the exact retail worker and queue frontier")
