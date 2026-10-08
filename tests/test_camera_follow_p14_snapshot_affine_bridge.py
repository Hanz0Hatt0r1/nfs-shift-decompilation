import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "camera_follow_p14_snapshot_affine_bridge.json"


def test_snapshot_affine_bridge_proves_target_vehicle_pose_but_not_player_selection():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.CameraFollowP14SnapshotAffineBridge/1"
    assert payload["ready"] is True

    assignment = payload["target_entry_index_assignment"]
    assert assignment["manager_selector"] == "FUN_00d60660"
    assert assignment["callsite"] == "0x00d606db -> FUN_00485290"
    assert assignment["entry_plus_0xfc_role"] == "numeric vehicle index"
    assert "0x004852a1 entry+0x100 = EAX" in assignment["machine_flow"]
    assert "0x00485224 entry+0xfc = entry+0x100" in assignment["machine_flow"]

    camera = payload["camera_callsite"]
    assert camera["function"] == "FUN_00481420"
    assert "0x00481477 ECX = entry+0xfc" in camera["machine_flow"]
    assert "0x00481486 call FUN_0070dcc0" in camera["machine_flow"]

    lookup = payload["snapshot_lookup"]
    assert lookup["slot_formula"] == "DAT_00c10b20 + numeric_vehicle_index * 0x1fa0"
    assert "slot+0xd70" in lookup["active_snapshot"]
    assert "FUN_00481e20" in lookup["copy"]

    world = payload["world_transform_application"]
    assert world["outer_vehicle_snapshot_contract"] == "SHIFT.OuterVehicleRenderSnapshotAffineBridge/1"
    assert world["outer_vehicle_slot_continuity"] is True
    assert world["target_entry_to_vehicle_render_snapshot_affine_proven"] is True

    adjudication = payload["adjudication"]
    assert adjudication["entry_plus_0xfc_numeric_vehicle_index_proven"] is True
    assert adjudication["camera_target_uses_exact_indexed_vehicle_snapshot_proven"] is True
    assert adjudication["camera_target_world_affine_dependency_proven"] is True
    assert adjudication["entry_attached_runtime_is_world_pose"] is False
    assert adjudication["phase651_request_3_pose_dependency_complete"] is True
    assert adjudication["tracking_camera_target_id_is_selected_player_bmw_entry_proven"] is False
    assert adjudication["phase651_request_3_complete"] is False
    assert adjudication["native_camera_follow_ready"] is False
