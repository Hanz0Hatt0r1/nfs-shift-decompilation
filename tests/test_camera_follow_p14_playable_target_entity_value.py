import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "camera_follow_p14_playable_target_entity_value.json"


def test_shipped_trackcam_player_value_joins_selected_player_id():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.CameraFollowP14PlayableTargetEntityValue/1"
    assert payload["ready"] is True
    assert payload["authority"]["platform"] == "PC retail 1.02"
    assert payload["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert payload["authority"]["resource_archive_sha256"] == "6b2875e2a1ff0fe6c30c8ef6999d1e301808dae028800755cf11d3ccd557caee"

    resource = payload["resource"]
    assert resource["path"] == "scripts/postracenis/default.xml"
    assert resource["sha256"] == "aeab2e475efc106ae2caf397985c5e4600c8788d9f626654fb6294969cf2a3c5"
    event = resource["camera_event"]
    assert event["class"] == "CCameraEvent"
    assert event["camera_type"] == "TrackCam"
    assert event["camera_name"] == ""
    assert event["camera_anchor"] == "Player"
    assert event["target"] == "Player"

    dispatch = payload["event_dispatch"]
    assert dispatch["event_vtable_slot"] == "+0x4c = FUN_006f7770"
    assert dispatch["payload"] == "CCameraEvent+0x14"
    assert dispatch["service_vtable"] == "0x00abec20"
    assert dispatch["service_slot"] == "+0x128 = FUN_004b9670"
    assert dispatch["camera_type_1_handler"] == "FUN_004b9350"

    resolver = payload["player_id_resolution"]
    assert "CCameraEvent+0x1c" in resolver["trackcam_anchor_input"]
    assert "CCameraEvent+0x28" in resolver["trackcam_target_input"]
    assert resolver["resolver_dispatch"] == "+0x14 = FUN_004b6f20"
    assert resolver["resolver_trampoline"] == "FUN_004b72c0"
    assert resolver["camera_manager_slot"] == "+0x2c = FUN_00459b80"
    assert resolver["player_result"] == "FUN_00489ad0()->+0x374->+0x100"
    assert resolver["case_insensitive_literal_match"] is True

    activation = payload["activation"]
    assert "player_id, player_id" in activation["trackcam_blank_camera_name_branch"]["call"]
    assert activation["trackcam_blank_camera_name_branch"]["next"] == "FUN_0080be50 -> FUN_0080e1b0"
    assert "FUN_0080ce80" in activation["mode2_join"]

    adjudication = payload["adjudication"]
    assert adjudication["shipped_playable_trackcam_event_uses_player_anchor"] is True
    assert adjudication["shipped_playable_trackcam_event_uses_player_target"] is True
    assert adjudication["trackcam_player_string_resolves_to_current_player_manager_id"] is True
    assert adjudication["trackcam_activation_param1_is_current_player_manager_id"] is True
    assert adjudication["mode2_selected_player_target_identity_complete_on_trackcam_to_tracking_transition"] is True
    assert adjudication["phase651_request_3_selected_vehicle_identity_complete"] is True
    assert adjudication["phase651_request_3_complete"] is True
    assert adjudication["native_camera_follow_ready"] is False
    assert adjudication["external_provider_count"] == 7


def test_last_player_cam_is_not_used_as_target_identity_proof():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert any("LastPlayerCam" in row and "not used" in row for row in payload["limits"])
