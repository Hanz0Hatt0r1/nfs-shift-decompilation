import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "camera_follow_p14_target_runtime_bridge.json"


def test_target_runtime_bridge_rejects_entry_identity_and_classifies_local_target_state():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.CameraFollowP14TargetRuntimeBridge/1"
    assert payload["ready"] is True
    assert payload["authority"]["platform"] == "PC retail 1.02"

    rejected = payload["rejected_identity"]
    assert rejected["manager_2a0_entry_is_HDVehicle_plus_0x4330"] is False

    attached = payload["entry_attached_runtime"]
    assert attached["pointer_field"] == "entry+0x1e80"
    assert attached["producer"] == "FUN_00481d46"
    assert "FUN_0046c050" in attached["allocation_constructor"]
    assert attached["classification"] == "target-local offset/runtime state"
    assert attached["world_pose_identity"] is False
    assert "FUN_0070dcc0" in attached["reason"]

    dispatch = payload["target_transform_dispatch"]
    assert dispatch["call_chain"] == [
        "FUN_00481420",
        "FUN_004810a0",
        "FUN_004585e6",
        "FUN_004810bf",
    ]
    assert dispatch["selector_2"]["lanes"] == ["+0x10", "+0x14", "+0x18"]
    assert dispatch["selector_5"]["lanes"] == ["+0x1c", "+0x20", "+0x24"]

    adjudication = payload["adjudication"]
    assert adjudication["manager_entry_direct_vehicle_identity_rejected"] is True
    assert adjudication["entry_attached_runtime_local_target_dependency_proven"] is True
    assert adjudication["entry_attached_runtime_is_world_pose"] is False
    assert adjudication["world_pose_dependency_moved_to_snapshot_affine_bridge"] is True
    assert adjudication["phase651_request_3_complete"] is False
    assert adjudication["native_camera_follow_ready"] is False
    assert adjudication["external_provider_count"] == 7
