#!/usr/bin/env python3
"""Guard bounded Linux cross-run evidence for the latest P2 plugin."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_p2_latest_plugin_crossrun_20261026.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-p2-plugin-p1-runtime-crossrun.v1"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
binaries = evidence["binaries"]
assert binaries["p1_runtime"]["sha256"] == (
    "f43d094797bf30c2e552b244c6ec50e4e69bb0b11fee409e07a812ba74158f78"
)
assert binaries["p2_linux_plugin"]["sha256"] == (
    "3b1afafad8e4fc7fc7e35e6bb81ab8e337156b108a5c7e4de49d0869787b3fb0"
)
abi = evidence["abi_check"]
assert abi["ldd_r_runtime_resolved_to_p1_build"] is True
assert abi["unresolved_dynamic_symbols_observed"] == 0
assert abi["gpu_plugin_loader_accepted_plugin"] is True
assert abi["duplicate_cvar_registration_warnings"] > 0

run = evidence["run"]
for item in [run["first_frontier_script"], run["continuation"]["script"]]:
    script = (ROOT / item["path"]).read_bytes()
    assert hashlib.sha256(script).hexdigest() == item["sha256"]
assert run["guest_memory_written_by_probe"] is False
assert run["mapped_hashes_verified_in_inferior"] is True
assert [q["queue_head"] for q in run["worker_queue_entry"]] == [0, 0]
assert [q["queue_tail"] for q in run["worker_queue_entry"]] == [0, 0]
assert [w["guest_address"] for w in run["renderer_ring_observations"]["event_write_shd"]] == [
    "0x17AF4004",
    "0x17AF4000",
]
assert run["first_retail_queue_wait"]["head"] == 3
assert run["first_retail_queue_wait"]["tail"] == 21
assert run["first_retail_queue_wait"]["predicate_byte"] == "0x14"

android = evidence["process2_android_reference"]
assert android["wait"]["guest_address"] == "0x1B964004"
assert android["wait"]["byte_offset"] == 1180
assert "separate runs" in " ".join(android["not_proven"])
assert "does not establish whether a later Linux batch reaches" in " ".join(
    android["not_proven"]
)

print("latest P2 Linux plugin reproduces the retail queue frontier with empty worker queues")
