#!/usr/bin/env python3
"""Guard the exact-XEX XThread resume-to-execution cross-check."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_xthread_resume_execute_crosscheck_20261026.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-xthread-resume-execute-crosscheck.v1"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
trace = evidence["run"]["gdb_trace"]
pairs = trace["resume_to_execute_pairs_observed"]
assert len(pairs) == 8
assert all(p["resume_call_observed"] and p["execute_entry_observed"] for p in pairs)
assert all(p["creation_flags"] == "0x00000001" for p in pairs)
assert {p["guest_thread_id"] for p in pairs} == set(range(6, 14))
workers = trace["unsuspended_worker_threads"]
assert [p["guest_thread_id"] for p in workers] == [14, 15]
assert all(p["guest_start_address"] == "0x823B8AC8" for p in workers)
wait = trace["first_software_queue_wait"]
assert wait["function"] == "0x823B34A0"
assert (wait["queue_head"], wait["target"], wait["queue_tail"]) == (3, 13, 21)
assert wait["predicate_byte"] == "0x14" and not wait["completion_mask_set"]
assert evidence["binaries"]["rexglue_runtime"]["mapped_hash_verified_in_inferior"] is False
limits = " ".join(evidence["interpretation"]["not_proven"])
assert "method return register" in limits
assert "why bit 0x02 remains clear" in limits
assert evidence["run"]["guest_memory_written_by_probe"] is False

print("XThread resume/execution cross-check preserves scheduler limits and retail predicate")
