#!/usr/bin/env python3
"""Guard the same-run retail interrupt-context guest-virtual write watch."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_interrupt_context_virtual_watch_20261026.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-interrupt-context-virtual-watch.v1"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert evidence["binaries"]["rexglue_runtime"]["mapped_hash_verified"] is False
assert evidence["binaries"]["gpu_plugin"]["mapped_hash_verified"] is True

run = evidence["run"]
assert run["guest_memory_written_by_probe"] is False
trace = run["gdb_trace"]
assert trace["gpu_plugin_hash_verified_in_inferior"] is True
assert trace["runtime_mapping_hash_verified_in_inferior"] is False
watch = trace["interrupt_context_watch"]
assert watch["first_callback_source"] == 0
assert watch["hardware_watchpoints_armed"] == 2
assert watch["write_stop_before_first_wait"] is False
assert watch["source_1_callback_observed_before_first_wait"] is False
assert watch["context_guest_address"] == "0xFB963000"
base = int(watch["host_guest_virtual_mapping_base"], 16)
for item in watch["watchpoints"]:
    assert int(item["host_watch_address"], 16) == base + int(
        item["guest_virtual_address"], 16
    )
    assert item["initial_guest_big_endian_value"] == "0x00000000"
    assert item["value_at_first_wait"] == "0x00000000"

wait = trace["first_software_queue_wait"]
assert wait["function"] == "0x823B34A0"
assert wait["head"] <= wait["target"] <= wait["tail"]
assert wait["predicate_byte"] == "0x14"
assert wait["completion_mask_set"] is False
assert wait["callback_target"] == wait["callback_argument"] == "0x00000000"
assert run["runtime_log"]["same_run_memory_mode_callback_wait_identified"] is False
assert run["controller_input_sent"] is False

limits = " ".join(evidence["interpretation"]["not_proven"])
assert "GPU/device DMA" in limits
assert "another host alias" in limits
assert "Preserve the original queue and predicate semantics" in evidence["interpretation"]["next_step"]

print("retail interrupt-context write watch preserves guest semantics and probe limits")
