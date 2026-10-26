#!/usr/bin/env python3
"""Guard the experimental early-RPTR exact-XEX retest evidence."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_p2_early_rptr_retest_20261026.json").read_text()
)
prior = json.loads(
    (ROOT / "evidence/xbox360_linux_guest_wait_owner_trace_20261026.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-p2-early-rptr-retail-retest.v1"
assert evidence["target"]["xex_sha256"] == prior["target"]["xex_sha256"]
assert evidence["p2_handoff"]["status"] == "experimental"
binaries = evidence["binaries"]
assert binaries["p1_runtime"]["sha256"] == (
    "f43d094797bf30c2e552b244c6ec50e4e69bb0b11fee409e07a812ba74158f78"
)
assert binaries["p2_linux_plugin"]["sha256"] == (
    "0837991a5d2ac07c81e5fc352be9b5520d3d7d2b224547d7af76c95d5e985e01"
)

direct = evidence["direct_run"]["runtime_log"]
assert direct["coher_status_host_waits_entered"] == 4
assert direct["coher_status_host_waits_completed"] == 4
assert direct["snapshot_rptr_writebacks"] == ["0x16", "0x19", "0x1C", "0x31"]
assert direct["target_wait_entered"] is True
assert direct["target_wait_completed"] is False

capture = evidence["same_candidate_capture"]
wait = capture["wait"]
assert wait["packet"] == "c0043c00000000131b96400600000001ffffffff00000100"
assert wait["guest_physical_word"] == "0x1B964004"
assert wait["reference"] == "0x00000001"
assert wait["physical_alias_bytes"] == wait["context_vE_alias_bytes"] == "00000000"
root = capture["root_ring_capture"]
assert root["bytes"] == 2048
assert root["aliases_equal"] is True
assert root["physical_sha256"] == root["vA_sha256"] == prior["ring_root_capture"]["physical_capture"]["sha256"]
assert [item["sha256"] for item in root["nested_indirect_buffers_before_wait"]] == [
    item["sha256"] for item in prior["ring_root_capture"]["nested_indirect_buffers_before_wait"]
]
assert [item["guest_address"] for item in root["nested_indirect_buffers_before_wait"]] == [
    "0x0975B660",
    "0x0975C3A0",
    "0x0975CFE0",
]
assert root["later_packets"][0]["byte_offset"] == "0x518"
assert root["later_packets"][1]["byte_offset"] == "0x700"

print("early RPTR advances the ring, but the exact retail memory wait remains unsignaled")
