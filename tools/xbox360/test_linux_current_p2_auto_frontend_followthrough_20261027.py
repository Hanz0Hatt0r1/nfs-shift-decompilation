"""Guard the exact-XEX no-input frontend run against the P2 Linux DSO."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_current_p2_auto_frontend_followthrough_20261027.json").read_text()
)
assert evidence["schema"] == "shift.xbox360.linux-current-p2-auto-frontend-followthrough.v1"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
assert evidence["target"]["movie_asset"]["sha256"] == (
    "34a9ffeb18fb8410f7857e9abff361888050677f166aad3834a3a4125595cd1c"
)
assert evidence["binaries"]["p1_host_sha256"] == (
    "6a3ac7224c139dced55fe76bd110b3d66a8c1609a1afdfad9514485daf62702b"
)
assert evidence["binaries"]["p1_runtime_sha256"] == (
    "d8faeb3973a1a2564dea021f19d0418fa718268dadebd414b0006a94a9062253"
)
plugin = evidence["binaries"]["p2_linux_plugin"]
assert plugin["source_commit"] == "9afec9ead95484a63471912ed2e40c5f043bac46"
assert plugin["sha256"] == "01a2908cfec4492cb6702a0217343d58a8c9d7618e836bef8e598bdfbdc2c0e7"
run = evidence["run"]
assert run["duration_seconds"] == 145.535
assert run["controller_input_sent"] is False
assert run["mapped_binary_hashes_verified"] is True
assert run["runtime_log"]["accepted_copy_convert_entries"] == 497
assert run["runtime_log"]["completed_coher_status_host_waits"] == 10407
assert run["runtime_log"]["guest_fault_entries"] == 0
assert run["runtime_log"]["vulkan_frame_refresh_failures"] == 1
assert run["runtime_log"]["menu_background_xml_misses"] == 0
assert run["runtime_log"]["bink_or_movie_path_strings"] == 0
captures = run["captures"]
assert [capture["elapsed_seconds"] for capture in captures] == [
    30.423,
    60.109,
    90.165,
    120.172,
    145.106,
]
assert all("no menu UI" in capture["observation"] for capture in captures)
assert evidence["interpretation"]["not_proven"]

print("latest no-input exact-XEX run remains short of the retail main menu")
