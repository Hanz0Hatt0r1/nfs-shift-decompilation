#!/usr/bin/env python3
"""Guard the decoded retail wait cursor and read-only GDB probe."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence_path = ROOT / "evidence/xbox360_linux_retail_wait_cursor_20261025.json"
trace_path = ROOT / "tools/xbox360/trace_guest_ring_wait_cursor.gdb"
evidence = json.loads(evidence_path.read_text())
trace = trace_path.read_text()

assert evidence["schema"] == "shift.xbox360.linux.retail-wait-cursor.v1"
assert evidence["input"]["retail_xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert evidence["capture"]["guest_memory_modified"] is False
assert evidence["capture"]["gdb_script"]["sha256"] == hashlib.sha256(
    trace_path.read_bytes()
).hexdigest()

guest = evidence["guest_observation"]
provenance = guest["expected_cursor_provenance"]
assert provenance["copy_instruction_address"] == "0x823B34B8"
assert provenance["copy_instruction"] == "mr r30,r4"
assert "before 0x823A0310 executes its body" in guest["capture_phase"]
assert guest["expected_cursor_decimal"] == int(guest["expected_cursor_from_guest_r30"], 16)
assert guest["software_ring_head"] < guest["expected_cursor_decimal"] <= guest["software_ring_tail"]
assert guest["wait_record_snapshot_head"] == guest["software_ring_head"]
assert int(guest["predicate_byte_object_plus_0x2ABD"], 16) & 0x02 == 0
assert guest["wait_predicate_hit_count_at_least"] >= max(guest["representative_samples"])

required_trace_fields = (
    "break sub_823A0310",
    "set $r30 = *(unsigned long long*)($ctx+240)",
    "set $snapshot_raw = *(unsigned int*)($base+$record+8)",
    "set $head_ptr_raw = *(unsigned int*)($base+$object+0x2a90)",
    "set $tail_raw = *(unsigned int*)($base+$object+0x2a9c)",
    "set $predicate = *(unsigned char*)($base+$object+0x2abd)",
    "set $wait_hits = $wait_hits + 1",
)
for token in required_trace_fields:
    assert token in trace, f"retail wait trace lost required read-only field: {token}"

for line in trace.splitlines():
    stripped = line.strip()
    assert not stripped.startswith(("set *(unsigned", "set *(char", "set {")), (
        "retail wait trace must not write guest memory: " + stripped
    )

assert any(
    "which component must advance" in statement.lower()
    for statement in evidence["interpretation"]["not_proven"]
)
assert "main menu or an offline race" in evidence["interpretation"]["not_proven"][-1]
print("retail wait cursor evidence keeps guest state read-only and avoids claiming the blocker cause")
