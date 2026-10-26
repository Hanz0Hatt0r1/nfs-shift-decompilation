#!/usr/bin/env python3
"""Guard the latest retail callback/wait evidence and its limits."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (
        ROOT
        / "evidence/xbox360_linux_pm4_interrupt_order_retail_wait_20261026.json"
    ).read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-pm4-interrupt-order-retail-wait.v1"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert evidence["binaries"]["gpu_plugin"]["mapping_verified"] is True
assert evidence["binaries"]["rexglue_runtime"]["mapping_verified"] is True
assert evidence["run"]["guest_memory_written_by_probe"] is False

trace = evidence["run"]["gdb_trace"]
assert trace["callback_hits_before_first_wait"]["source_0"] > 0
assert trace["callback_hits_before_first_wait"]["source_1"] == 0
assert trace["deferred_consumer_hits"] > 0
assert trace["deferred_callback_queue_indices"] == {"read": 0, "write": 0}
assert trace["software_queue_producer_0x823A4758_hits"] == 0
assert trace["registered_callback_0x82649B68_hits"] == 0

wait = trace["first_wait"]
assert wait["function"] == "0x823B34A0"
assert wait["head"] <= wait["target"] <= wait["tail"]
assert int(wait["predicate_byte"], 16) & int(wait["tested_completion_mask"], 16) == 0

interpretation = evidence["interpretation"]
assert "Why source-1 interrupts" in interpretation["not_proven"][0]
assert "keep retail queue and predicate semantics unchanged" in interpretation[
    "next_p1_step"
]
assert evidence["run"]["termination"].startswith("GDB harness killed")

print("retail PM4 interrupt trace preserves the bounded wait frontier")
