import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "camera_follow_p14_target_dependency_frontier.json"


def test_target_dependency_frontier_rejects_override_as_vehicle_and_stays_fail_closed():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.CameraFollowP14TargetDependencyFrontier/1"
    assert payload["version"] == 2
    assert payload["ready"] is True
    assert payload["authority"]["platform"] == "PC retail 1.02"

    chain = payload["proven_chain"]
    assert "FUN_0081f7c0" in chain["mode2_source_camera_store"]
    assert "DAT_00c25fb8" in chain["tracking_rtti_symbol"]
    assert "OverridedBy" in chain["override_selector"]
    assert "FUN_00812970" in chain["override_store"]
    assert "FUN_00812ed0" in chain["active_camera_resolver"]
    assert "FUN_00812de0" in chain["target_metadata_path"]
    assert "+0x574" in chain["target_metadata_path"]

    adjudication = payload["adjudication"]
    assert adjudication["mode2_runtime_argument_is_vehicle"] is False
    assert adjudication["mode2_source_vtable_identity_proven"] is True
    assert adjudication["source_plus_0x64_is_tracking_camera_proven"] is True
    assert adjudication["tracking_camera_plus_0xe8_is_vehicle"] is False
    assert adjudication["tracking_camera_plus_0xe8_is_camera_override_proven"] is True
    assert adjudication["camera_target_service_dependency_proven"] is True
    assert adjudication["target_service_record_is_selected_bmw_vehicle_proven"] is False
    assert adjudication["target_service_record_pose_is_BODY0_world_pose_proven"] is False
    assert adjudication["camera_follow_vehicle_pose_dependency_complete"] is False
    assert adjudication["camera_follow_update_order_complete"] is False
    assert adjudication["native_camera_follow_ready"] is False
    assert adjudication["external_provider_count"] == 7
