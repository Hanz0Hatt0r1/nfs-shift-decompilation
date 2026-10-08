import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "camera_follow_p14_manager2a0_join.json"


def test_camera_target_service_reaches_manager_2a0_but_vehicle_identity_stays_open():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.CameraFollowP14Manager2a0Join/1"
    assert payload["ready"] is True
    assert payload["service_wiring"]["proven_value"] == "CameraManager+0x574 = DAT_00bc185c+4"
    interface = payload["render_manager_interface"]
    assert interface["constructor"] == "FUN_0045ef50"
    assert interface["plus_4_interface_vtable"] == "0x00ab55f0"
    assert interface["camera_transform_slot_0x08"] == "FUN_0045d940"
    assert interface["camera_metadata_slot_0x1c"] == "FUN_0045da00"

    join = payload["manager_collection_join"]
    assert join["manager_getter"] == "FUN_00489ad0"
    assert join["collection"] == "manager+0x2a0"
    assert join["indexed_lookup"] == "FUN_0054ed00"

    adjudication = payload["adjudication"]
    assert adjudication["camera_target_service_root_identity_proven"] is True
    assert adjudication["camera_target_transform_uses_manager_2a0_entry_proven"] is True
    assert adjudication["camera_target_metadata_uses_manager_2a0_entry_proven"] is True
    assert adjudication["manager_2a0_entry_is_selected_bmw_vehicle_proven"] is False
    assert adjudication["manager_2a0_entry_pose_is_selected_BODY0_world_pose_proven"] is False
    assert adjudication["phase651_request_3_complete"] is False
    assert adjudication["native_camera_follow_ready"] is False
    assert payload["blocked_by"] == ["P1.3.manager2a0 exact registration/entry identity"]
