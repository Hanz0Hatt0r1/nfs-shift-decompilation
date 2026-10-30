#!/usr/bin/env python3
"""Guard the latest exact-XEX run using the P2 renderer handover."""

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_p2_handover_frontend_followthrough_20261025.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux.p2-handover-frontend-followthrough.v1"
assert evidence["target"]["sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
plugin = evidence["binaries"]["p2_renderer_plugin"]
assert plugin["source_commit"] == "99cdd93a92a580d562ca3f0c4c88e2e4a9d3b537"
assert plugin["sha256"] == "e2679a4ca54178a312af3f6cc7cc2ba0eb8dd562a8e730a32131068d46736bf4"
assert plugin["elf_build_id"] == "173c8c62e2dea1cf2b5a8161003e6e63e294fb8d"
assert plugin["loaded_mapping_verified"] is True

run = evidence["run"]
assert run["duration_seconds"] >= 120
assert "No GDB" in run["instrumentation"]
assert run["controller"]["press_release_edges"] == 34
captures = run["window_capture"]["captures"]
assert len(captures) == 9
assert [item["elapsed_seconds"] for item in captures] == sorted(
    item["elapsed_seconds"] for item in captures
)
assert all(re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) for item in captures)
assert {item["observation"] for item in captures} == {
    "retail driving-safety warning",
    "black game viewport",
}

log = run["runtime_log"]
assert log["accepted_copy_convert_entries"] == 1103
assert log["menu_background_xml_open_failures"] == 4
assert log["vulkan_frame_refresh_failures"] == 0
assert log["guest_faults"] == log["sigsegv"] == log["sigbus"] == 0
not_proven = evidence["interpretation"]["not_proven"]
assert any("offline race" in item for item in not_proven)
assert any("caused the black viewport" in item for item in not_proven)

print("latest P2 handover exact-XEX run evidence is internally consistent")
