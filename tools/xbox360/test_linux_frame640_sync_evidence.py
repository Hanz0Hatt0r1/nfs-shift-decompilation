#!/usr/bin/env python3
"""Check the retained synchronized frame-640 runtime evidence."""
import hashlib
import json
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "evidence/xbox360_linux_frame640_sync_b03c9f87_20261025.json"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


record = json.loads(EVIDENCE.read_text())
assert record["schema"] == "shift.xbox360.linux.p1-p2-synchronized-window-frame-evidence.v1"
assert record["target"]["title_id"] == "454108B4"
assert record["target"]["default_xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
run = record["run_exact"]
assert run["renderer_source_commit"] == "b03c9f87"
assert run["renderer_was_verified_in_proc_maps"] is True
assert run["renderer_plugin_sha256"] == (
    "512eb2658935c48a3fddcc5abc0e100da948913fad6eb3f42148b12eb278fa98"
)

visible = record["window_observation"]["visible_capture"]
visible_path = ROOT / visible["path"]
assert visible_path.is_file()
assert sha256(visible_path.read_bytes()) == visible["sha256"]
assert visible["non_black_rgb_pixels"] > 0
assert visible["runtime_seconds"] == record["selected_presenter_frame"][
    "readback_path_appeared_at_runtime_seconds"
]

later = record["window_observation"]["later_captures"]
assert [capture["runtime_seconds"] for capture in later] == [32.044, 40.032]
assert all(capture["non_black_rgb_pixels"] == 0 for capture in later)
assert later[0]["sha256"] == later[1]["sha256"]
assert later[1]["byte_identical_to_32_second_capture"] is True

frontier = record["runtime_frontier"]
assert frontier["submitted_log_entries"] == 789
assert frontier["accepted_copy_convert_entries"] > 0
assert frontier["menu_background_xml_miss_count"] == 4
assert frontier["mixed_msaa_resolve_failure_count"] == 8
assert "not causal proof" in frontier["interpretation"]

bundle_path = ROOT / record["artifacts"]["bundle"]
bundle_data = bundle_path.read_bytes()
assert sha256(bundle_data) == record["artifacts"]["bundle_sha256"]
with tarfile.open(bundle_path, "r:gz") as bundle:
    members = set(bundle.getnames())
    assert {
        "frame640.a2b10g10r10",
        "window-frame640-readback-ready.png",
        "window-32s.png",
        "window-40s.png",
        "nfs_shift_001.log",
        "run.json",
    } <= members

print("synchronized frame-640 artifacts and bounded claims match")
