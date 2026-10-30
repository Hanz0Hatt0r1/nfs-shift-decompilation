#!/usr/bin/env python3
"""Guard exact-XEX wait-owner packet-order and alias evidence."""

import json
import hashlib
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_guest_wait_owner_trace_20261026.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-guest-wait-owner-trace.v1"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
run = evidence["run"]
assert run["controller_input_sent"] is False
assert run["guest_memory_written_by_probe"] is False
assert run["mapped_hashes_verified_in_inferior"] is True
assert run["binaries"]["gpu_plugin"]["sha256"] == (
    "28ad43593d5c5e58920f00a09779b3388e5a9d380a63019c62d1bfdef143a481"
)
assert run["binaries"]["gpu_plugin"]["build_id"] == "319df66e1087310121eff259e91432afa03572e1"
assert run["binaries"]["rexglue_runtime"]["sha256"] == (
    "2b0d46856da000cecafb46581ddff50da99f549ff335bee9ba489238eed24059"
)
script = (ROOT / run["gdb_script"]["path"]).read_bytes()
assert hashlib.sha256(script).hexdigest() == run["gdb_script"]["sha256"]
assert run["runtime_log"]["coher_status_host_waits_entered"] == 4
assert run["runtime_log"]["coher_status_host_waits_completed"] == 4
assert run["runtime_log"]["target_waits_entered"] == 1
assert run["runtime_log"]["target_waits_completed"] == 0
assert run["runtime_log"]["memory_write_candidate_packet_logs_before_wait"] == 0
assert run["runtime_log"]["pm4_event_write_packet_logs_before_wait"] == 0

wait = evidence["wait"]
assert wait["guest_physical_word"] == "0x1B964004"
assert wait["poll_address_field"] == "0x1B964006"
assert wait["reference"] == "0x00000001"
assert wait["mask"] == "0xFFFFFFFF"
assert wait["packet"] == "c0043c00000000131b96400600000001ffffffff00000100"
assert wait["physical_word_sample"] == "00000000"
assert wait["context_vE_word_sample"] == "00000000"

root = evidence["ring_root_capture"]
assert root["capture_bytes"] == 2048
assert root["aliases_equal"] is True
assert root["physical_capture"]["sha256"] == root["vA_capture"]["sha256"]
assert len(root["nested_indirect_buffers_before_wait"]) == 3
assert [item["guest_address"] for item in root["nested_indirect_buffers_before_wait"]] == [
    "0x0975B660",
    "0x0975C3A0",
    "0x0975CFE0",
]
assert root["nested_indirect_buffers_before_wait"][2]["type3_opcode_counts"] == {
    "0x36": 24
}
shader_evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_retail_wait_shader_export_audit_20261026.json").read_text()
)
assert root["nested_indirect_buffers_before_wait"][0]["sha256"] == (
    shader_evidence["capture"]["nested_shader_buffer"]["sha256"]
)
assert root["nested_indirect_buffers_before_wait"][2]["sha256"] == (
    shader_evidence["capture"]["nested_draw_buffer"]["sha256"]
)
assert root["later_packets_in_same_capture"][0]["byte_offset"] == "0x518"
assert root["later_packets_in_same_capture"][1]["byte_offset"] == "0x700"
assert int(root["later_packets_in_same_capture"][0]["byte_offset"], 16) > int(
    wait["byte_offset"], 16
)
assert int(root["later_packets_in_same_capture"][1]["byte_offset"], 16) > int(
    wait["byte_offset"], 16
)

not_proven = " ".join(evidence["interpretation"]["not_proven"])
assert "another CPU producer" in not_proven
assert "offline race" in not_proven
assert "Keep the guest wait and predicate unchanged" in evidence["interpretation"]["next_p1_step"]

print("exact retail wait is before the later interrupt/event packets; its writer remains unknown")
