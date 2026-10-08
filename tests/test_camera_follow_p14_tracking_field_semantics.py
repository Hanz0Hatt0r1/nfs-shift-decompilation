import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "camera_follow_p14_tracking_field_semantics.json"


def test_tracking_field_semantics_separate_target_from_override_linkage():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.CameraFollowP14TrackingFieldSemantics/1"
    assert payload["ready"] is True
    assert payload["authority"]["platform"] == "PC retail 1.02"

    reflection = payload["reflection"]
    assert reflection["target"]["name_string"] == "Target"
    assert reflection["target"]["field_offset"] == "0x78"
    assert reflection["overrided_by"]["name_string"] == "OverridedBy"
    assert reflection["overrided_by"]["field_offset"] == "0xd4"

    override = payload["override_resolution"]
    assert override["runtime_override_field"] == "TrackingCamera byte +0xd4"
    assert override["candidate_name_field"] == "candidate byte +0x60"
    assert override["comparison_function"]["classification"] == "null-terminated byte-string equality"
    assert "TrackingCamera byte +0xe8" in override["attachment"]

    adjudication = payload["adjudication"]
    assert adjudication["plus_0xd4_is_target"] is False
    assert adjudication["plus_0xd4_is_overrided_by"] is True
    assert adjudication["plus_0x78_is_reflection_target_field"] is True
    assert adjudication["fun_0081f070_is_player_vehicle_target_resolution"] is False
    assert adjudication["fun_0081f070_is_tracking_camera_override_resolution"] is True
    assert adjudication["selected_player_target_identity_complete"] is False
    assert adjudication["native_camera_follow_ready"] is False
    assert adjudication["external_provider_count"] == 7
