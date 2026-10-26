#!/usr/bin/env python3
"""Guard the exact-current-P2 retail frontend wait observation."""

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (
        ROOT
        / "evidence/xbox360_linux_current_p2_renderer_frontend_wait_20261026.json"
    ).read_text()
)

assert evidence["schema"] == (
    "shift.xbox360.linux-current-p2-renderer-frontend-wait.v1"
)
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)

binaries = evidence["binaries"]
assert binaries["gpu_plugin"]["source_commit"] == (
    "3f4a779049410d7e1b48e39cba6c41c0bd794087"
)
assert binaries["gpu_plugin"]["mapped_hash_verified"] is True
assert binaries["rexglue_runtime"]["mapped_hash_verified"] is True
for binary in binaries.values():
    assert re.fullmatch(r"[0-9a-f]{64}", binary["sha256"])

run = evidence["run"]
assert run["controller_input_sent"] is False
assert run["guest_memory_written_by_probe"] is False
trace = run["gdb_trace"]
assert trace["mapping_hashes_verified_in_inferior"] is True
assert trace["callback_hits_before_first_wait"] == {"source_0": 99, "source_1": 0}
assert trace["deferred_queue_indices"] == {"read": 0, "write": 0}
assert trace["software_queue_producer_0x823A4758_hits"] == 0
assert trace["registered_callback_0x82649B68_hits"] == 0

wait = trace["first_wait"]
assert wait["function"] == "0x823B34A0"
assert wait["head"] <= wait["target"] <= wait["tail"]
assert int(wait["predicate_byte"], 16) & int(wait["completion_mask"], 16) == 0

renderer = run["runtime_log"]
assert renderer["vblank_callbacks_logged"] > 0
assert renderer["captured_memory_wait_entry_logged"] is False
assert "GDB stopped and killed" in run["termination"]
assert "main menu" in evidence["interpretation"]["not_proven"][1]
assert "preserve the queue and predicate semantics" in evidence["interpretation"][
    "next_p1_step"
]

print("current P2 DSO reproduces the bounded retail queue wait with predicates intact")
