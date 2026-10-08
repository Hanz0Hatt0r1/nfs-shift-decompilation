import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "camera_follow_p14_active_target_id_producer.json"


def test_active_target_id_producer_is_exact_but_player_source_stays_open():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.CameraFollowP14ActiveTargetIdProducer/1"
    assert payload["ready"] is True
    assert payload["authority"]["retail_executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )

    activation = payload["mode2_activation"]
    assert activation["function"] == "FUN_0080e1b0"
    assert activation["target_id_argument"] == "param_1"
    assert "lane+0x26a4 = param_1" in activation["current_target_publication"]

    publication = payload["active_camera_data_publication"]
    assert publication["target_setter"] == "FUN_0080ce80(mode2_source,param_1)"
    assert any("active_data+0x74 = param_1" in row for row in publication["target_setter_flow"])
    assert publication["lookat_setter"] == "FUN_0080cea0(mode2_source,param_2)"
    assert any("active_data+0x7c = param_2" in row for row in publication["lookat_setter_flow"])
    assert publication["active_target_id_producer_proven"] is True
    assert publication["active_lookat_id_producer_proven"] is True

    steady = payload["steady_state_reuse"]
    assert steady["function"] == "FUN_00812050"
    assert steady["preserves_target_id"] is True
    assert any("camera_lane+0x26a4" in row for row in steady["flow"])

    adjudication = payload["adjudication"]
    assert adjudication["active_camera_plus_0x74_write_site_known"] is True
    assert adjudication["active_camera_plus_0x74_value_is_FUN_0080e1b0_param_1"] is True
    assert adjudication["camera_lane_plus_0x26a4_tracks_same_target_id"] is True
    assert adjudication["initial_activation_param_1_selected_player_proven"] is False
    assert adjudication["selected_player_target_identity_complete"] is False
    assert adjudication["native_camera_follow_ready"] is False
    assert adjudication["external_provider_count"] == 7
