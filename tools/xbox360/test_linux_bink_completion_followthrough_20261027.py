"""Guard the exact-XEX Bink completion and scene-update follow-through."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_bink_completion_followthrough_20261027.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-bink-completion-followthrough.v1"
target = evidence["target"]
assert target["title_id"] == "454108B4"
assert target["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40c9a0c2c58"
)
assert target["movie_asset"]["declared_frame_count"] == 281

run = evidence["run"]
assert run["guest_memory_modified_by_probe"] is False
assert run["controller_input_sent"] is False
assert run["mapped_libraries_verified"]["runtime_sha256"] == evidence["binaries"][
    "p1_runtime_sha256"
]
assert run["mapped_libraries_verified"]["plugin_sha256"] == evidence["binaries"][
    "p2_linux_plugin"
]["sha256"]
script = ROOT / run["trace_script"]["path"]
assert hashlib.sha256(script.read_bytes()).hexdigest() == run["trace_script"]["sha256"]

bink = evidence["bink_completion"]
assert bink["frame_target"] == 281
assert bink["target_observation"]["progress"] == bink["target_observation"]["target"]
assert bink["target_observation"]["target"] == bink["frame_target"]
assert bink["target_observation"]["function"] == "0x82679510"

scene = bink["scene_update"]
assert scene["function"] == "0x82DDC6F0"
assert scene["child_update_function"] == "0x82E2C5A8"
assert scene["c5a8_return_value"] == scene["scene_return_value"] == 1
assert scene["object_plus_356_after_return"] == scene["object_plus_356_before_return"] + 1

completion = bink["following_child_completion"]
assert completion["function"] == "0x82E2CD10"
assert completion["entry_progress"] == completion["entry_target"] == 281
assert completion["entry_object_plus_12"] == 1
assert completion["return_value"] == 0
assert all(value == 0 for value in completion["bink_fields_after_return"].values())

not_proven = evidence["interpretation"]["not_proven"]
assert any("visibly presented" in claim for claim in not_proven)
assert any("visible main menu" in claim for claim in not_proven)
assert any("offline-race" in claim for claim in not_proven)
assert "Preserve retail event and queue semantics" in evidence["interpretation"]["next_step"]

print("retail Bink completion and scene-update follow-through evidence is consistent")
