"""Guard the exact-XEX PM4 interrupt and worker-counter evidence."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_pm4_irq_worker_counter_20261027.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-pm4-irq-worker-counter.v1"
assert evidence["target"]["title_id"] == "454108B4"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)

crosswalk = evidence["ring_to_guest_callback"]
records = crosswalk["records"]
assert crosswalk["trace_cap"] == crosswalk["p2_interrupts_logged"] == 128
assert crosswalk["unique_time_matches"] == len(records)
assert [row["p2_interrupt"]["index"] for row in records] == list(range(128))
assert len({row["p1_callback"]["sequence"] for row in records}) == 128
assert crosswalk["p1_source_1_callbacks_in_full_run"] == 2095
assert crosswalk["max_abs_delta_ms"] <= crosswalk["match_window_ms"]
assert crosswalk["all_cpu_masks_equal_dispatched_masks"] is True
assert crosswalk["all_cpu_masks"] == "0x04"
assert crosswalk["all_p1_sources"] == "0x1"
assert crosswalk["p1_callback_functions"] == ["0x823a4758"]
for row in records:
    packet = row["p2_interrupt"]
    callback = row["p1_callback"]
    assert packet["cpu_mask"] == packet["dispatched_cpu_mask"] == 0x04
    assert callback["source"] == "0x1"
    assert callback["function"] == "0x823a4758"
    assert abs(row["delta_ms"]) <= crosswalk["match_window_ms"]

queue = evidence["worker_queue_followthrough"]
assert queue["retail_source_1_callbacks_to_823B8C60"] == 823
assert queue["guest_queue_enqueues"] == queue["guest_worker_executions"]
assert queue["guest_worker_executions"] == queue["KeSetEvent_queue_publications"]

counter = evidence["worker_count_followup"]
assert counter["guest_memory_modified_by_probe"] is False
assert counter["controller_input_sent"] is False
assert counter["initial_value"] == 0
assert [(item["old"], item["new"]) for item in counter["transitions"]] == [
    (0, 1),
    (1, 0),
    (0, 0xFFFFFFFF),
]
assert counter["first_negative_writer"] == "0x823B85D0"
assert counter["stack"][:3] == ["sub_823B85D0", "sub_823B87B0", "sub_823B8AC8"]
assert "unresolved" in counter["interpretation"]

trace = ROOT / evidence["captures"]["counter_gdb_script"]["path"]
assert hashlib.sha256(trace.read_bytes()).hexdigest() == evidence["captures"][
    "counter_gdb_script"
]["sha256"]
claims = evidence["interpretation"]["not_proven"]
assert any("main menu" in claim for claim in claims)
assert any("offline race" in claim for claim in claims)
assert any("defect" in claim for claim in claims)

print("retail PM4 callback crosswalk and worker-count evidence is consistent")
