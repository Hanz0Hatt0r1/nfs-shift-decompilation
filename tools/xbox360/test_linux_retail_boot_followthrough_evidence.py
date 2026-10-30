#!/usr/bin/env python3
"""Guard the exact-XEX retail boot follow-through evidence bundle."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence_path = ROOT / "evidence/xbox360_linux_retail_boot_followthrough_20261026.json"
evidence = json.loads(evidence_path.read_text())

assert evidence["schema"] == "shift.xbox360.linux.retail-boot-followthrough.v1"
assert evidence["target"]["sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert evidence["run"]["duration_seconds"] >= 120
assert "did not exit naturally" in evidence["run"]["termination"]
assert "No GDB breakpoints" in evidence["run"]["instrumentation"]

captures = evidence["run"]["window_capture"]["captures"]
assert len(captures) == 9
assert [capture["elapsed_seconds"] for capture in captures] == sorted(
    capture["elapsed_seconds"] for capture in captures
)
for capture in captures:
    image_path = ROOT / capture["path"]
    assert image_path.is_file(), f"missing retail window capture: {capture['path']}"
    assert hashlib.sha256(image_path.read_bytes()).hexdigest() == capture["sha256"]

stats = evidence["run"]["runtime_log"]
assert stats["accepted_copy_convert_entries"] == 1136
assert stats["vulkan_frame_refresh_failures"] == 0
assert stats["cameraconfig_xml_open_failures"] == 1
assert stats["menu_background_xml_open_failures"] == 4
assert stats["guest_fault_entries"] == 0

interpretation = evidence["interpretation"]
assert any("caused the blank viewport" in item for item in interpretation["not_proven"])
assert any("offline-race entry" in item for item in interpretation["not_proven"])
assert all(status == "in_progress" for status in interpretation["gate_status"].values())

print("exact-XEX boot follow-through evidence and window hashes are consistent")
