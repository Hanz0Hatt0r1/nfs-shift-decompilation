import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "camera_follow_p14_target_id_service_bridge.json"


def test_target_id_service_bridge_separates_ids_from_target_selectors():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.CameraFollowP14TargetIdServiceBridge/1"
    assert payload["ready"] is True
    assert payload["authority"]["platform"] == "PC retail 1.02"

    layout = payload["camera_data_layout"]
    assert layout["target_id"] == {"offset": "0x74", "default": -1, "reflected": False}
    assert layout["target_selector"]["offset"] == "0x78"
    assert layout["target_selector"]["default"] == 6
    assert layout["target_selector"]["reflected_name"] == "Target"
    assert layout["lookat_id"] == {"offset": "0x7c", "default": -1, "reflected": False}
    assert layout["lookat_selector"]["offset"] == "0x80"
    assert layout["lookat_selector"]["reflected_name"] == "LookAt"

    service = payload["service_wiring"]
    assert service["manager_field"] == "CameraManager+0x574"
    assert service["installed_interface"] == "DAT_00bc185c+4"
    assert service["interface_vtable"] == "0x00ab55f0"
    assert service["vtable_slots"]["+0x08"] == "FUN_0045d940"
    assert service["vtable_slots"]["+0x2c"] == "FUN_00459b80"

    dispatch = payload["target_transform_dispatch"]
    assert dispatch["target_id_sources"] == ["active camera data +0x74", "active camera data +0x7c"]
    assert "FUN_0054ed00" in "\n".join(dispatch["manager_lookup"]["machine"])

    resolver = payload["name_to_target_id"]
    assert resolver["player_literals"] == ["player", "teammate"]
    assert resolver["player_result_path"] == "FUN_00489ad0()->+0x374->+0x100"

    adjudication = payload["adjudication"]
    assert adjudication["target_plus_0x78_is_manager_entry_id"] is False
    assert adjudication["target_plus_0x78_is_service_selector"] is True
    assert adjudication["runtime_plus_0x74_is_target_manager_lookup_id"] is True
    assert adjudication["literal_player_resolves_to_current_player_manager_id"] is True
    assert adjudication["active_playable_camera_plus_0x74_proven_from_literal_player_resolver"] is False
    assert adjudication["selected_player_target_identity_complete"] is False
    assert adjudication["native_camera_follow_ready"] is False
    assert adjudication["external_provider_count"] == 7
