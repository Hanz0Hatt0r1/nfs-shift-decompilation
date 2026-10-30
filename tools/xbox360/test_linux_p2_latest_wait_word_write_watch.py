#!/usr/bin/env python3
"""Guard the latest exact-XEX Linux WAIT_REG_MEM write-watch evidence."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_p2_latest_wait_word_write_watch_20261026.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-p2-latest-wait-word-write-watch.v1"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
binaries = evidence["binaries"]
assert binaries["p1_runtime"]["sha256"] == (
    "f43d094797bf30c2e552b244c6ec50e4e69bb0b11fee409e07a812ba74158f78"
)
assert binaries["p2_linux_plugin"]["sha256"] == (
    "f2a963ddfe4a38acf3b4858182cd38c92101ec54692b578e61626672c961292c"
)
assert binaries["host_sha256"] == (
    "610d8f53750cef76ecf3f003c7e6e5e1b9873f9068579b43429a819815a0122a"
)

run = evidence["run"]
assert run["guest_memory_written_by_probe"] is False
assert run["plugin_compatibility"]["loader_accepted_plugin"] is True
assert run["plugin_compatibility"]["duplicate_cvar_registration_warnings"] == 15
wait = run["wait"]
assert wait["operation"] == "WAIT_REG_MEM"
assert wait["guest_address"] == "0x1B964004"
assert wait["reference"] == "0x00000001"
assert wait["mask"] == "0xFFFFFFFF"
assert wait["byte_offset"] == 1180
assert wait["coher_status_host_waits_completed_before_it"] == 4

watch = run["write_watch"]
script = (ROOT / watch["script"]["path"]).read_bytes()
assert hashlib.sha256(script).hexdigest() == watch["script"]["sha256"]
assert watch["watchpoints_armed_after_zero_samples"] is True
assert watch["guest_memory_write_stops_observed"] == 0
assert watch["watchpoint_active_seconds_before_timeout_approximately"] > 18
assert watch["both_aliases_used_same_backing"] is True
assert {item["sampled_value"] for item in watch["guest_memory_aliases"]} == {"0x00000000"}
assert {item["host_address"] for item in watch["guest_memory_aliases"]} == {
    "0x21B964004",
    "0x1FB963004",
}
assert {item["backing_file_offset"] for item in watch["guest_memory_aliases"]} == {
    "0x11B964004"
}
assert watch["timeout_exit_code"] == 137
assert "no clean title shutdown" in watch["termination"]

capture = evidence["command_buffer_capture"]
assert capture["separate_run_same_binary_hashes"] is True
assert capture["host_sha256"] == binaries["host_sha256"]
capture_script = (ROOT / capture["capture_script"]["path"]).read_bytes()
assert hashlib.sha256(capture_script).hexdigest() == capture["capture_script"]["sha256"]
packets = capture["packets_in_stream_order"]
assert packets[0]["byte_offset"] == 1180
assert packets[0]["guest_address"] == "0x1B964004"
interrupt = next(item for item in packets if item["opcode"] == "PM4_INTERRUPT")
event_write = next(item for item in packets if item["opcode"] == "PM4_EVENT_WRITE")
assert packets[0]["byte_offset"] < interrupt["byte_offset"] < event_write["byte_offset"]
assert capture["runtime_log_reached_first_wait_before_later_packets"] is True
assert "does not prove their execution" in capture["limitation"]

print("latest Linux retail WAIT_REG_MEM remains unchanged with both CPU write aliases watched")
