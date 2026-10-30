#!/usr/bin/env python3
"""Guard the current P2-branch exact-retail frontend follow-through evidence."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_current_p2_branch_frontend_followthrough_20261027.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-current-p2-frontend-followthrough.v1"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
sources = evidence["sources"]
assert sources["p1"]["runtime_sha256"] == (
    "d8faeb3973a1a2564dea021f19d0418fa718268dadebd414b0006a94a9062253"
)
assert sources["p2"]["pull_request"] == 2161
assert sources["p2"]["pull_request_state"] == "OPEN"
assert sources["p2"]["commit"] == "e7a474578efe7bee4e37d71fe58df875993c3e4f"
assert sources["p2"]["linux_dynamic_resolution_clean"] is True

run = evidence["run"]
assert run["duration_seconds"] >= 100
assert "Clean title shutdown was not observed" in run["termination"]
assert run["mapped_binary_hashes_verified"] is True
assert run["guest_memory_modified_by_probe"] is False
assert run["renderer_plugin_claimed_merged"] is False
assert len(run["controller"]["pulses"]) == 5
assert run["controller"]["guest_observation_proven"] is False
captures = run["target_window_captures"]
assert len(captures) == 4
assert "disclaimer visible" in captures[0]["observation"]
assert "black" in captures[1]["observation"]
assert "no main-menu UI" in captures[-1]["observation"]
assert all(len(capture["sha256"]) == 64 for capture in captures)

logs = run["renderer_logs"]
assert logs["primary"]["sha256"] == (
    "8d8be48f922bcdfbada12c2bbec710d5d3b0451126ad706a20edb4199a67525f"
)
assert logs["rotated"]["sha256"] == (
    "17fd806b36f8f4e0763b01e3c9fb24c5df28e2f67848d562e00438aa59ee000c"
)
waits = logs["captured_wait_reg_mem"]
assert len(waits) == 6
assert all(wait["polls"] == 0 for wait in waits)
assert waits[0]["guest"] == "0x1B964004"
assert waits[0]["reference"] == "0x00000001"
assert waits[0]["byte_offset"] == "0x1180"
assert logs["unsupported_wait_forms"] == 2
assert logs["missing_menu_background_xml_opens"] == 4
assert logs["mixed_copy_convert_extent_refresh_failures"] == 1
assert logs["guest_fault_log_entries"] == 0
assert "game progress from renderer submission counts" in evidence["interpretation"]["not_proven"][-1]
assert "Keep retail wait/input semantics unchanged" in evidence["interpretation"]["next_p1_step"]

print("current P2-branch DSO clears six captured waits; retail main menu and race remain unverified")
