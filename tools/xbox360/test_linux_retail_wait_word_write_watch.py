#!/usr/bin/env python3
"""Guard the bounded retail WAIT_REG_MEM writer observation."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_retail_wait_word_write_watch_20261026.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-retail-wait-word-write-watch.v1"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert evidence["binaries"]["rexglue_runtime"]["mapped_hash_verified"] is True
assert evidence["binaries"]["gpu_plugin"]["mapped_hash_verified"] is True

run = evidence["run"]
watch = run["watchpoint"]
assert watch["packet_address_source"]["packet_address_field"] == "0x1B964012"
assert watch["packet_address_source"]["guest_physical_word"] == "0x1B964010"
assert watch["guest_memory_physical_base"] == "0x200000000"
assert int(watch["guest_memory_physical_base"], 16) + int(
    watch["packet_address_source"]["guest_physical_word"], 16
) == int(watch["host_physical_alias"], 16)
assert watch["hardware_watchpoint_armed"] is True
assert watch["initial_raw"] == watch["raw_at_first_wait"] == "0x00000000"
assert watch["write_hits_before_first_wait"] == 0

wait = run["first_software_queue_wait"]
assert wait["function"] == "0x823B34A0"
assert wait["head"] <= wait["target"] <= wait["tail"]
assert wait["producer_0x823A4758_hits"] == 0
assert wait["registered_callback_0x82649B68_hits"] == 0
assert run["guest_memory_written_by_probe"] is False

limits = " ".join(evidence["interpretation"]["not_proven"])
assert "device/DMA" in limits
assert "alternate host aliases" in " ".join(evidence["limitations"])
assert "not captured from the same run" in " ".join(evidence["limitations"])

print("retail WAIT_REG_MEM word watch preserves observation limits and queue state")
