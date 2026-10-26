#!/usr/bin/env python3
"""Guard the exact-XEX scratch-wait and UI follow-through evidence."""
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_p2_scratch_writeback_ui_followthrough_20261026.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux.p2-scratch-writeback-ui-followthrough.v1"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert evidence["binaries"]["p2_renderer_plugin"]["sha256"] == (
    "f1404a4f57fb073f12cc0b34da4f74a3e75d8d6f2ffb49e62708c9a1b09bb6b6"
)

scratch = evidence["scratch_wait"]
assert scratch["writeback"]["register"] == "SCRATCH_REG1"
assert scratch["writeback"]["guest_word"] == scratch["retail_wait"]["guest_word"] == "0x1B964004"
assert scratch["writeback"]["before"] == "0x00000000"
assert scratch["writeback"]["after"] == scratch["retail_wait"]["reference"] == "0x00000001"
assert scratch["retail_wait"]["result"] == "completed"
assert scratch["retail_wait"]["polls"] == scratch["retail_wait"]["elapsed_ms"] == 0

followthrough = evidence["frontend_followthrough"]
assert followthrough["menu_background_xml_open_failures"] == 4
assert followthrough["vulkan_frame_refresh_failures"] == 1
assert followthrough["first_following_successful_draw_submission"]["local_time"] > (
    followthrough["failed_refresh"]["local_time"]
)
assert followthrough["draw_submission_entries_after_last_missing_xml"] == 1353
assert followthrough["guest_fault_log_entries"] == 0

captures = evidence["run"]["window_capture"]["captures"]
assert [item["scheduled_seconds"] for item in captures] == sorted(
    item["scheduled_seconds"] for item in captures
)
assert all(re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) for item in captures)
observations = {item["observation"] for item in captures}
assert "retail Language Select screen" in observations
assert "retail driving-safety disclaimer" in observations
assert "black viewport with horizontal loading lines; no menu visible" in observations

not_proven = " ".join(evidence["interpretation"]["not_proven"])
assert "offline race" in not_proven and "guest frontend" in not_proven

print("retail scratch WAIT_REG_MEM completion and follow-through evidence is consistent")
