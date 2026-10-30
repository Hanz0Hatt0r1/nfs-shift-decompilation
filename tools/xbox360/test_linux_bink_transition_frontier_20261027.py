"""Guard the exact-XEX Bink target and post-wrapper frontier evidence."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
evidence = json.loads(
    (ROOT / "evidence/xbox360_linux_bink_transition_frontier_20261027.json").read_text()
)

assert evidence["schema"] == "shift.xbox360.linux-bink-transition-frontier.v1"
assert evidence["target"]["xex_sha256"] == (
    "8c86a34f369f9d064126342daccb2cfe4646cfe735df6a032812a40a9c0a2c58"
)
asset = evidence["target"]["movie_asset"]
assert asset["declared_frame_count"] == 281
assert asset["retail_frame_target"] == "0x00000119"

bink = evidence["bink_frontier"]
assert bink["frame_target"] == 281
assert bink["guest_bink_object"] == "0xE6795040"
assert bink["first_observation"]["progress"] == 1
assert bink["last_observation"]["progress"] == bink["frame_target"]
assert bink["gdb_hit_counts"] == {
    "manager_0x82679C50": 220,
    "video_wrapper_0x82678FD0": 219,
    "post_wrapper_update_0x82679510": 220,
}
assert bink["post_target_calls_observed"] == 0
assert bink["outer_manager_caller_lr"] == "0x82E2CB80"

chain = evidence["static_call_chain"]
assert chain["nested_dispatch"]["function"] == "0x82E2CB50"
assert chain["nested_dispatch"]["guest_return_address"] == "0x82E2CB80"
assert chain["parent_update"]["function"] == "0x82E2C5A8"
assert chain["parent_update"]["then_returns"] == 1
assert chain["scene_object_update"]["function"] == "0x82DDC6F0"
assert chain["scene_object_update"]["on_success_increments"] == "object+356"

trace = evidence["run"]["trace_script"]
trace_path = ROOT / trace["path"]
assert hashlib.sha256(trace_path.read_bytes()).hexdigest() == trace["sha256"]
assert evidence["run"]["guest_memory_modified_by_probe"] is False
assert evidence["run"]["controller"]["guest_consumption_verified"] is False
assert evidence["run"]["renderer_logs"][0]["frame_refresh_failures"] == 1
assert all(log["guest_faults"] == 0 for log in evidence["run"]["renderer_logs"])

not_proven = evidence["interpretation"]["not_proven"]
assert any("decoded or visibly presented" in claim for claim in not_proven)
assert any("visible main menu" in claim for claim in not_proven)
assert any("consumed" in claim for claim in not_proven)
assert "0x82E2CD10" in evidence["interpretation"]["next_step"]
assert "without changing retail semantics" in evidence["interpretation"]["next_step"]

print("retail Bink target and scene-object dispatch frontier evidence is consistent")
