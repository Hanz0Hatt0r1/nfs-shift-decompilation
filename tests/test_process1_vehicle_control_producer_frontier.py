from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/process1_vehicle_control_producer_frontier.json"
DOC = ROOT / "docs/PROCESS_1_VEHICLE_CONTROL_PRODUCER_FRONTIER.md"


def _load() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_authority_and_scheduler_chain_are_pinned() -> None:
    payload = _load()
    assert payload["format"] == "SHIFT.Process1VehicleControlProducerFrontier/1"
    assert payload["ready"] is True
    assert payload["authority"]["platform"] == "PC retail 1.02"
    assert payload["authority"]["new_machine_or_source_claims_in_this_join"] is False
    scheduler = payload["scheduler_side_closed_chain"]
    assert scheduler["path"] == ["FUN_00715380", "FUN_00713050", "FUN_00794a30", "FUN_00770e80"]
    assert scheduler["outer_receiver"] == "DAT_00c13700"
    assert scheduler["caller_channel_offsets"] == ["+0x1aa8", "+0x1ab0"]
    assert scheduler["outer_receiver_offsets"] == ["+0x98", "+0xa0"]
    assert scheduler["retail_cadence_admitted"] is True
    assert scheduler["player_control_semantics_proven_for_these_channels"] is False


def test_wheel_structure_is_closed_but_control_owner_is_not() -> None:
    payload = _load()
    wheel = payload["wheel_side_closed_structure"]
    assert wheel["physics_pass"] == "FUN_0076d100"
    assert wheel["wheel_update"] == "FUN_00758b50"
    assert wheel["wheel_count"] == 4
    assert wheel["wheel_state_base"] == "+0x848"
    assert wheel["wheel_runtime_base"] == "+0x400"
    assert wheel["wheel_stride"] == "0xa80"
    assert wheel["source_contract"] == "SHIFT.WheelKinematicsSourceEvidence/1"
    assert wheel["complete_callsite_control_state_ownership_proven"] is False


def test_fail_closed_control_adjudication() -> None:
    adjudication = _load()["boundary_adjudication"]
    assert adjudication["outer_update_scheduler_channels_may_be_named_player_input"] is False
    assert adjudication["native_VehicleControlIntent_is_retail_provenance"] is False
    assert adjudication["retail_input_to_drivetrain_value_transfer_proven"] is False
    assert adjudication["retail_input_to_wheel_state_value_transfer_proven"] is False
    assert adjudication["fun_00758b50_concrete_control_state_owner_proven"] is False
    assert adjudication["p1_3_control_producer_complete"] is False
    assert adjudication["retail_control_chain_complete"] is False
    assert adjudication["external_provider_count"] == 7


def test_documentation_preserves_scheduler_vs_control_boundary() -> None:
    text = DOC.read_text(encoding="utf-8")
    for token in (
        "FUN_00715380",
        "FUN_00713050",
        "FUN_00794a30",
        "FUN_00770e80",
        "FUN_00758b50",
        "VehicleControlIntent",
        "identified as player control: **false**",
        "retail control chain complete: **false**",
        "external-provider count: **7**",
        "NEXT_STEP",
    ):
        assert token in text
