#!/usr/bin/env python3
"""Guard the bounded, read-only retail ring-head write watch."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence_path = ROOT / "evidence/xbox360_linux_ring_head_cpu_write_watch_20261025.json"
trace_path = ROOT / "tools/xbox360/trace_guest_ring_head_cpu_write.gdb"
evidence = json.loads(evidence_path.read_text())
probe = evidence["probe"]
watch = probe["watchpoint"]
ring = evidence["runtime_observation"]

assert evidence["schema"] == "shift.xbox360.linux-ring-head-cpu-write-watch.v1"
assert evidence["target"]["retail_xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert probe["guest_memory_modified"] is False
assert watch["head_write_hits"] == 0
assert watch["initial_head"] < watch["expected_cursor"] <= watch["initial_tail"]
assert int(watch["host_mapping_address"], 16) - int(watch["guest_address"], 16) == 0x100000000
assert probe["gdb_script"]["sha256"] == hashlib.sha256(trace_path.read_bytes()).hexdigest()
assert ring["captured_draw_submissions"] > 0
assert ring["draw_submissions_after_first_xml_miss"] == 0
assert evidence["interpretation"]["not_proven"]
assert any("DMA" in claim for claim in evidence["interpretation"]["not_proven"])

trace = trace_path.read_text()
for token in (
    "break sub_823A0310",
    "set $head_ptr_raw = *(unsigned int*)($base+$object+0x2a90)",
    "set $tail_raw = *(unsigned int*)($base+$object+0x2a9c)",
    "watch -location *(unsigned int*)$head_addr",
):
    assert token in trace, f"ring-head trace lost required read-only probe: {token}"
assert "condition $head_watch" not in trace
assert "set *(unsigned" not in trace

print("ring-head watch evidence matches the bounded CPU-write probe without assigning a cause")
