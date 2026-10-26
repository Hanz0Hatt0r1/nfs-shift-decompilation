#!/usr/bin/env python3
"""Guard the current-P2 exact-XEX coherency and guest-memory wait evidence."""

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (
        ROOT
        / "evidence/xbox360_linux_current_p2_coherency_wait_runtime_20261026.json"
    ).read_text()
)

assert evidence["schema"] == (
    "shift.xbox360.linux-current-p2-coherency-wait-runtime.v1"
)
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
for binary in evidence["binaries"].values():
    assert re.fullmatch(r"[0-9a-f]{64}", binary["sha256"])

plugin = evidence["binaries"]["gpu_plugin"]
assert plugin["source_commit"] == "ccdee6b4d125f3a8670806f0ba15f0361588b137"
assert plugin["mapped_hash_verified_in_direct_run"] is True
assert evidence["game_data"]["default_xex_sha256_matches_target"] is True

direct = evidence["direct_run"]
assert direct["controller_input_sent"] is False
assert direct["guest_memory_written_by_probe"] is False
waits = direct["renderer_waits"]
assert waits["coher_status_host_entered"] == waits["coher_status_host_completed"] == 4
assert waits["memory_wait_entered"] == 1
assert waits["memory_wait_completed"] == 0
assert waits["memory_wait_guest_physical_word"] == "0x1B964004"
assert direct["verified_game_window_capture"] is False
assert "clean title shutdown was not observed" in direct["termination"]

trace = evidence["gdb_run"]
assert trace["guest_memory_written_by_probe"] is False
first_wait = trace["first_retail_software_queue_wait"]
assert first_wait["head"] <= first_wait["target"] <= first_wait["tail"]
assert first_wait["completion_mask_set"] is False
memory_wait = trace["memory_wait"]
assert memory_wait["hardware_write_watchpoints_armed"] == 4
assert len(memory_wait["watched_host_aliases"]) == 4
assert memory_wait["source1_callback_hits"] == 0
assert memory_wait["writes_observed_through_watched_aliases"] == 0
assert memory_wait["completion_log_count"] == 0

input_probe = evidence["input_probe"]
assert input_probe["controller"]["created_after_sdl_input_init"] is True
assert input_probe["controller"]["recognized_by_standalone_sdl3_check"] is True
assert input_probe["buttons_sent"][0] == "START"
assert set(input_probe["buttons_sent"][1:]) == {"A"}
assert input_probe["mapped_hashes_verified_in_inferior"] is False
assert input_probe["trace"]["input_system_get_state_hits"] == 0
assert input_probe["trace"]["sdl_enumerate_devices_hits"] == 0
assert input_probe["trace"]["sdl_controller_added_hits"] == 0
assert input_probe["runtime_log"]["guest_memory_wait_completed"] is False
assert input_probe["controller_input_reached_guest"] is False

limits = " ".join(evidence["interpretation"]["not_proven"])
assert "device/DMA" in limits
assert "offline-race entry" in limits
assert "Preserve the retail WAIT_REG_MEM" in evidence["interpretation"]["next_p1_step"]

print("current P2 reaches the unresolved retail guest-memory wait before guest input polling")
