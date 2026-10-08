import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "camera_follow_p14_target_entity_activation_bridge.json"


def test_target_entity_activation_bridge_closes_string_to_target_id_but_not_player_value():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.CameraFollowP14TargetEntityActivationBridge/1"
    assert payload["ready"] is True

    event = payload["event_record"]
    assert event["constructor"] == "FUN_0050a030"
    assert event["allocation_bytes"] == "0x30"
    assert event["target_entity"]["offset"] == "+0x20"
    assert event["target_entity"]["name"] == "target entity"
    assert "0x00d8cd79 push 0x20" in event["target_entity"]["machine_anchor"]
    assert event["default_target_entity_is_player"] is False

    resolver = payload["activation_resolver"]
    assert resolver["function"] == "FUN_0050a9c0"
    assert resolver["resolved_service_slot"] == "CameraManager+0x574 vtable+0x2c = FUN_00459b80"
    assert resolver["target_entity_to_manager_id_proven"] is True
    assert "0x0050ad29 push target-entity string" in resolver["machine_flow"]
    assert "0x0050ad2c EBX = returned target manager-entry ID" in resolver["machine_flow"]

    publication = payload["activation_publication"]
    assert publication["downstream_contract"] == "SHIFT.CameraFollowP14ActiveTargetIdProducer/1"
    assert publication["target_entity_string_to_active_data_plus_0x74_proven"] is True
    assert "FUN_0080e1b0 param_1" in publication["target_id_argument"]

    player = payload["selected_player_join"]
    assert player["FUN_00459b80_player_or_teammate_returns_selected_player_id"] is True
    assert player["playable_event_target_entity_value_is_player_or_teammate"] is False
    assert player["status"] == "target-entity-value-open"

    adjudication = payload["adjudication"]
    assert adjudication["event_plus_0x20_is_target_entity_string"] is True
    assert adjudication["target_entity_string_to_FUN_00459b80_proven"] is True
    assert adjudication["resolver_result_to_FUN_0080e1b0_param_1_proven"] is True
    assert adjudication["playable_target_entity_is_selected_player_literal_proven"] is False
    assert adjudication["selected_player_target_identity_complete"] is False
    assert adjudication["native_camera_follow_ready"] is False
    assert adjudication["external_provider_count"] == 7
