#!/usr/bin/env python3
"""Guard the latest exact-XEX ringtrace evidence and its claim boundaries."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_ringtrace_frontend_followthrough_20261026.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux.ringtrace-frontend-followthrough.v1"
assert evidence["target"]["sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert evidence["binaries"]["host"]["sha256"] == (
    "6a3ac7224c139dced55fe76bd110b3d66a8c1609a1afdfad9514485daf62702b"
)
assert evidence["binaries"]["rexglue_runtime"]["sha256"] == (
    "127181adbfb99b65e9d1a8f1d6aed12308e1cf320b86067588ad421f17eda68e"
)
assert evidence["binaries"]["gpu_plugin"]["sha256"] == (
    "dec875819cc6146c820838ac8ee52b45b90b83c7bb70d4d521ecc9dcdb4c6ee1"
)

run = evidence["run"]
assert run["duration_seconds"] == 180.01
assert run["instrumentation"].startswith("No GDB")
assert run["controller"]["button_edges"] == 44
assert run["controller"]["same_run_guest_consumption_proven"] is False
assert len(run["window_capture"]["captures"]) == 4
assert [capture["elapsed_seconds"] for capture in run["window_capture"]["captures"]] == sorted(
    capture["elapsed_seconds"] for capture in run["window_capture"]["captures"]
)

log = run["runtime_log"]
assert log["ring_wake_events"] == log["ring_snapshot_events"] == log["ring_complete_events"]
assert log["ring_complete_events"] == 1529
assert log["final_guest_rptr"] == "0x1F1F"
assert log["guest_faults"] == log["sigsegv"] == log["sigbus"] == 0
assert log["vulkan_frame_refresh_failures"] == 0

not_proven = evidence["interpretation"]["not_proven"]
assert any("offline race" in item for item in not_proven)
assert any("Vulkan 1.1 compatibility" in item for item in not_proven)
assert any("caused the alternating output" in item for item in not_proven)

print("latest exact-XEX ringtrace evidence is internally consistent")
