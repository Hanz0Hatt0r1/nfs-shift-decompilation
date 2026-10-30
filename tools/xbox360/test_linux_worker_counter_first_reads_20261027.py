#!/usr/bin/env python3
"""Guard read-only evidence for retail worker-counter wrap consumption."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_worker_counter_first_reads_20261027.json").read_text()
)
run = evidence["run"]
counter = run["counter"]
transitions = counter["first_transitions"]
reads = counter["first_reads"]
script = ROOT / run["gdb_script"]["path"]

assert evidence["schema"] == "shift.xbox360.linux-worker-counter-first-reads.v1"
assert run["controller_input_sent"] is False
assert run["guest_memory_modified_by_probe"] is False
assert run["duration_seconds"] == 105.474
assert counter["guest_address"] == "0xB7368A04"
assert counter["host_alias"] == "0x1B7368A04"
assert [(x["old"], x["new"]) for x in transitions[:3]] == [
    ("0x00000000", "0x00000001"),
    ("0x00000001", "0x00000000"),
    ("0x00000000", "0xFFFFFFFF"),
]
assert counter["write_watch_total"] == 836
assert counter["read_watch_total"] == counter["read_watch_disabled_after"] == 12
assert reads[0]["function"] == "sub_823B31A0"
assert reads[0]["value"] == "0xFFFFFFFF"
assert reads[4]["function"] == "sub_823B85D0"
assert reads[4]["offset"] == 1578
assert counter["first_read_stack"][:4] == [
    "sub_823B31A0",
    "sub_823B33A0",
    "sub_823B34A0",
    "sub_823B3850",
]
assert "signed cmpwi" in evidence["retail_static_crosscheck"]["field_test"]
assert "does not establish" in evidence["interpretation"]["supported"][2]
assert "do not patch the worker count" in evidence["interpretation"]["next_step"]
assert hashlib.sha256(script.read_bytes()).hexdigest() == run["gdb_script"]["sha256"]

print("retail worker-counter wrap is read by the signed queue/wait path; no P1 fix is justified")
