#!/usr/bin/env python3
"""Guard the bounded private-memory runtime smoke and its limitations."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (
        ROOT
        / "evidence/xbox360_linux_private_memory_current_p2_runtime_20261026.json"
    ).read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-private-memory-current-p2-runtime.v1"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)

run = evidence["run"]
assert run["exit_code"] == 0
assert run["termination"].startswith("SIGINT")
assert run["mapping_hashes_verified"] is True
assert run["mapped_libraries"]["librexruntime.so"] == evidence["binaries"][
    "rexglue_runtime"
]["sha256"]
assert run["mapped_libraries"]["librexgpu-shift-nativerd.so"] == evidence[
    "binaries"
]["gpu_plugin"]["sha256"]
assert run["runtime_log"]["scheduler_warning_count"] == 1
assert run["runtime_log"]["sigbus_mentions"] == 0
assert run["runtime_log"]["guest_fault_mentions"] == 0
assert run["renderer_wait"] == {
    "guest_physical_word": "0x1B964004",
    "reference": "0x00000001",
    "mask": "0xFFFFFFFF",
    "endian": 2,
    "compare": 3,
    "source": "0x095D0120",
    "depth": 1,
    "outer_byte_offset": "0x49C",
    "entry_timestamp": "2026-10-26 15:48:37.804",
    "completion_logged_before_sigint": False,
}

shared = run["shared_memory"]
assert shared["same_object_present_after_run"] is True
assert shared["proc_map_or_fd_references_after_run"] == []
assert shared["unlinked_after_reference_check"] is True
assert shared["named_xenia_memory_objects_after_cleanup"] == []
assert evidence["regression"]["result"] == "passed"
limits = " ".join(evidence["limitations"])
assert "main menu" in limits and "offline race" in limits

print("bounded current-P2 runtime evidence preserves wait and startup limits")
