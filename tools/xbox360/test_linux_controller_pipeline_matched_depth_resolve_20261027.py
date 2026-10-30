#!/usr/bin/env python3
"""Guard matched-runtime retail controller pipeline evidence."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_controller_pipeline_matched_depth_resolve_20261027.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-controller-pipeline-matched-depth-resolve.v1"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert evidence["binaries"]["p2_runtime_sha256"] == (
    "f049d64a46ab04e8d5fcb71800c92d86a5cc6a5fbd38a6b1bf1a623c86398a80"
)
assert evidence["binaries"]["p2_plugin_sha256"] == (
    "abc7bf5df779be7dce4fdae719c05c89a35ad8ce222f95b3337478f24bddc402"
)

run = evidence["run"]
assert run["duration_seconds"] >= 60
assert run["gdb_instrumented"] is True
assert run["probe_guest_memory_writes"] is False
assert run["controller"]["pulse_duration_ms"] == 3000
assert len(run["controller"]["pulses"]) == 6

path = evidence["retail_input_path"]
counts = path["counts"]
assert counts["XamInputGetState_entry"] == counts["InputSystem_GetState"] == 1520
assert counts["successful_user0_returns_sampled"] == 95
assert counts["sampled_button_masks"] == {"0x0000": 59, "0x0010": 18, "0x1000": 18}
assert counts["sub_8230CD00_hits"] == counts["sub_82308E60_hits"] == 1520
assert path["retail_controller_object"] == "0xBCAEB260"

edges = path["observed_edges"]
assert [(edge["function"], edge["edge"]) for edge in edges] == [
    ("sub_8230CD00", "0x0010"),
    ("sub_82308E60", "0x0010"),
    ("sub_8230CD00", "0x1000"),
    ("sub_82308E60", "0x1000"),
]
returns = path["matching_xam_return_samples"]
assert {sample["buttons"] for sample in returns} >= {"0x0010", "0x1000"}
assert all(sample["status"] == "0x0" for sample in returns)

claims = evidence["interpretation"]
assert "host-to-retail input delivery failure" in claims["supported"][-1]
assert "active frontend action handler consumed" in claims["not_proven"][0]
assert "visible main menu" in claims["not_proven"][1]
assert "Keep XAM and retail controller semantics unchanged" in claims["next_p1_step"]

print("matched runtime delivered A/Start through XAM to retail edge tracking; frontend action remains unverified")
