import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "camera_follow_p14_target_dependency_frontier.json"


def test_target_dependency_frontier_is_exact_and_fail_closed():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.CameraFollowP14TargetDependencyFrontier/1"
    assert payload["ready"] is True
    assert payload["authority"]["platform"] == "PC retail 1.02"
    chain = payload["proven_chain"]
    assert "FUN_0081f7c0" in chain["mode2_source_target_store"]
    assert chain["active_target_resolver"] == "FUN_0081f2e0"
    assert "FUN_00812970" in chain["tracking_target_acquisition"]
    assert chain["target_position_query"] == "FUN_0081f330 -> FUN_008155f0"

    adjudication = payload["adjudication"]
    assert adjudication["mode2_runtime_argument_is_vehicle"] is False
    assert adjudication["mode2_source_vtable_identity_proven"] is True
    assert adjudication["tracking_target_object_dependency_proven"] is True
    assert adjudication["tracking_target_is_selected_bmw_vehicle_proven"] is False
    assert adjudication["tracking_target_pose_is_BODY0_world_pose_proven"] is False
    assert adjudication["camera_follow_vehicle_pose_dependency_complete"] is False
    assert adjudication["camera_follow_update_order_complete"] is False
    assert adjudication["native_camera_follow_ready"] is False
    assert adjudication["external_provider_count"] == 7
