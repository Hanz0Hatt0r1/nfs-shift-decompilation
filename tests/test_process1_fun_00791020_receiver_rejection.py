from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00791020_receiver_rejection.json"
DOC = ROOT / "docs/PROCESS_1_FUN_00791020_RECEIVER_REJECTION.md"


def _payload() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_identity_and_retail_hash_are_pinned() -> None:
    payload = _payload()
    assert payload["format"] == "SHIFT.Fun00791020ReceiverRejection/1"
    assert payload["ready"] is True
    assert payload["authority"]["platform"] == "PC retail 1.02"
    assert payload["authority"]["retail_executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )


def test_manager_record_is_joined_to_hdvehicle_owner_slot() -> None:
    payload = _payload()
    publish = payload["selected_record_publication"]
    owner = payload["hdvehicle_owner_join"]
    assert publish["selected_record_store"].startswith("0x0074dde6")
    assert "0x00c10b34" in publish["selected_record_store"]
    assert owner["selected_record_load_before_call"].startswith("0x0074dabe")
    assert owner["hdvehicle_record_store"].startswith("0x0076e157")
    assert "HDVehicle+0x3fe8" in owner["hdvehicle_record_store"]
    assert owner["existing_owner_expression"] == "actual_participant = *([HDVehicle+0x3fe8])"


def test_fun_00791020_receiver_resolves_to_participant_child_not_hdvehicle() -> None:
    payload = _payload()
    resolved = payload["fun_00791020_receiver_resolution"]
    assert resolved["setup_record_dereference"].startswith("0x0074e2b6")
    assert resolved["setup_child_adjust"].startswith("0x0074e2b8")
    assert resolved["resolved_receiver"] == "actual_participant+0x340"
    assert resolved["absolute_actual_participant_write_offset"] == "0xc78"
    assert resolved["selected_hdvehicle_receiver"] is False


def test_numeric_offset_candidate_is_rejected_fail_closed() -> None:
    payload = _payload()
    comparison = payload["consumer_comparison"]
    adjudication = payload["adjudication"]
    assert comparison["slot0_consumed_absolute_offset"] == "HDVehicle+0x938"
    assert comparison["fun_00791020_absolute_write"] == "actual_participant+0xc78"
    assert comparison["same_object_base"] is False
    assert comparison["numeric_0x938_match_rejected"] is True
    assert comparison["fun_00791020_is_slot0_writer"] is False
    assert adjudication["fun_00791020_rejected_as_fun_00755950_slot0_writer"] is True
    assert adjudication["retail_input_control_provenance_proven"] is False
    assert adjudication["p1_3_control_producer_complete"] is False
    assert adjudication["external_provider_count"] == 7


def test_doc_preserves_semantic_boundary_and_next_absolute_offsets() -> None:
    text = DOC.read_text(encoding="utf-8")
    for token in (
        "matching numeric `+0x938` is not object identity",
        "actual_participant+0xc78",
        "HDVehicle+0x938",
        "HDVehicle+0x13b8",
        "HDVehicle+0x1e38",
        "HDVehicle+0x28b8",
        "retail input/control provenance",
        "provider count",
        "NEXT_STEP",
    ):
        assert token in text
