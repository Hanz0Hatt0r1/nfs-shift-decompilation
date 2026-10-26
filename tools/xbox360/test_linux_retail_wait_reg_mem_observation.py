#!/usr/bin/env python3
"""Guard the bounded retail memory-wait observation and its limits."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_retail_wait_reg_mem_observation_20261026.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-retail-wait-reg-mem-observation.v1"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert evidence["binaries"]["gpu_plugin"]["source_commit"].startswith("6277bda6")
assert evidence["run"]["guest_memory_written_by_probe"] is False

trace = evidence["run"]["gdb_trace"]
assert trace["hardware_write_watchpoints_armed"] == 4
assert trace["writes_observed_through_watched_aliases"] == 0
assert trace["source1_callback_hits"] == 0
assert {item["alias"] for item in trace["host_alias_watchpoints"]} == {
    "physical", "vA0000000", "vC0000000", "vE0000000_with_host_offset_0x1000"
}
assert all(item["initial_bytes"] == "00000000" for item in trace["host_alias_watchpoints"])

wait = evidence["run"]["renderer_wait"]
assert wait["guest_physical_word"] == "0x1B964004"
assert wait["reference"] == "0x00000001"
assert wait["mask"] == "0xFFFFFFFF"
assert wait["entry_log_count"] == 1
assert wait["completion_log_count"] == 0
assert wait["ring_snapshot"]["snapshot_ok"] is True
assert wait["ring_snapshot"]["expand_ok"] is True

limits = " ".join(evidence["interpretation"]["not_proven"])
assert "device/DMA" in limits
assert "unobserved alias" in limits
assert "Which retail producer" in limits

follow_up = evidence["follow_up_run"]
assert "shader programs" in " ".join(follow_up["interpretation"]["not_proven"])
assert follow_up["binaries"]["gpu_plugin"]["mapping_verified"] is True
assert follow_up["binaries"]["gpu_plugin"]["sha256"] == (
    "879b711ef16109a52b26df838ce2562e09d53d7c6daf89a102159abdd309c91b"
)
order = follow_up["packet_order"]
wait_offset = int(order["blocking_memory_wait"]["outer_byte_offset"], 16)
assert wait_offset == 0x49C
assert int(order["subsequent_interrupt"]["outer_byte_offset"], 16) > wait_offset
assert int(order["subsequent_event_write"]["outer_byte_offset"], 16) > wait_offset
assert order["pm4_event_write_observations_before_stall"] == 0
nested = follow_up["captured_buffers"]["nested_indirect_buffers"]
assert [item["dword_count"] for item in nested] == [74, 13, 48]
assert [item["sha256"] for item in nested] == [
    "515d445533bd11926618e9d1cbd5a4f7eaf51930dd27b7935b1efecf24845d7b",
    "7faaea1a5e85dd8155e2ec67f1c3c63ba1bf57e1d52165c44f254b6099f684a9",
    "4f2445f960ffe0265688c12b9081c0cdb17e8c0a4c8191cbfecb6bfd6bb8dbfc",
]
assert order["nested_buffer_packet_observations"]["0975B660"]["opcode_counts"] == {
    "0x2B": 2, "0x3B": 1
}
assert order["nested_buffer_packet_observations"]["0975CFE0"]["opcode_counts"] == {
    "0x36": 24
}
assert order["blocking_memory_wait"]["guest_physical_word"] == "0x1B964004"
assert follow_up["captured_buffers"]["outer_indirect_buffer"]["sha256"] == (
    "0314df2bd6d5142ec11417cffdb6b192bf4b046d22418528772f476ca3cc2580"
)

print("retail WAIT_REG_MEM evidence preserves bounded aliases, packet order, and causality limits")
