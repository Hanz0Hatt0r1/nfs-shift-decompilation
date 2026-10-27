#!/usr/bin/env python3
"""Guard exact-runtime retail controller pipeline evidence."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_exact_runtime_controller_pipeline_20261027.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-exact-runtime-controller-pipeline.v1"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert evidence["binaries"]["p1_runtime_sha256"] == (
    "6c56ca970160d9e3e6e28155c48ee11556763f206f6a49b78fdad2ca3f02ebb2"
)
assert evidence["binaries"]["p1_runtime_path_resolved_from_inferior_maps"] is True

run = evidence["run"]
assert run["duration_seconds"] >= 60
assert run["gdb_instrumented"] is True
assert run["guest_memory_modified_by_probe"] is False
assert run["controller"]["pulses_scheduled_after_retail_controller_update"] is True
assert [pulse["button"] for pulse in run["controller"]["pulses"]] == ["Start", "A", "Start"]
trace = run["tracing"]
assert trace["execution_runner"]["sha256"] == (
    "bb282e4b157a16be839da66ef1539e9b1161d5b1e61a3b8fffcb6d44c8938a8f"
)
assert trace["reproduction_runner"]["sha256"] == (
    "c10209424c95a3bde879b9f240dcfe6e766a1ef7309a898fa4583526fd55e675"
)

path = evidence["retail_input_path"]
counts = path["counts"]
assert counts["XamInputGetState_entry"] == counts["InputSystem_GetState"] == 1508
assert counts["successful_user0_returns_sampled"] == 377
assert counts["sampled_button_masks"] == {"0x0000": 199, "0x0010": 96, "0x1000": 82}
assert counts["sub_8230CD00_hits"] == counts["sub_82308E60_hits"] == 1508
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
assert "frontend action handler consumed" in claims["not_proven"][0]
assert "Trace the active frontend scene" in claims["next_p1_step"]

print("exact runtime delivered Start/A through XAM to retail edge tracking; frontend action remains unverified")
