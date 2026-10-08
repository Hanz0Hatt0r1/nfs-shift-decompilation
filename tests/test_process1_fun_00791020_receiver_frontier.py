from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00791020_receiver_frontier.json"
DOC = ROOT / "docs/PROCESS_1_FUN_00791020_RECEIVER_FRONTIER.md"


def _load() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_authority_and_writer_sites_are_pinned() -> None:
    payload = _load()
    assert payload["format"] == "SHIFT.Fun00791020ReceiverFrontier/1"
    assert payload["ready"] is True
    assert payload["authority"]["platform"] == "PC retail 1.02"
    assert payload["authority"]["retail_executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    writer = payload["candidate_writer"]
    assert writer["function"] == "FUN_00791020"
    assert writer["writes_receiver_plus_0x938"] == ["0x007910f8", "0x0079113e"]
    assert writer["write_width"] == "f32"
    assert writer["selected_hdvehicle_identity_proven"] is False


def test_setup_path_proves_only_plus_0x340_child_receiver() -> None:
    setup = _load()["setup_path"]
    assert setup["outer_call_instruction"] == "0x0074e2be"
    assert setup["outer_callee"] == "FUN_00799ff0"
    assert setup["proven_receiver_expression_at_setup_call"] == "*(setup_context)+0x340"
    assert setup["setup_context_identity"] == "unproven"
    assert setup["same_as_selected_hdvehicle"] is False
    assert setup["fun_00799ff0_preserves_receiver"] == [
        "0x00799ff1 ESI = ECX",
        "0x00799ff3 call FUN_00791020",
    ]


def test_numeric_offset_match_remains_fail_closed() -> None:
    payload = _load()
    join = payload["join_to_fun_00755950_consumer"]
    assert join["consumer_contract"] == "SHIFT.Fun00755950AbsoluteConsumedFieldMachineProof/1"
    assert join["consumer_hdvehicle_slot0_offset"] == "0x938"
    assert join["numeric_offset_match"] is True
    assert join["receiver_identity_join_complete"] is False
    assert join["may_promote_as_upstream_writer"] is False
    adjudication = payload["adjudication"]
    assert adjudication["fun_00791020_receiver_setup_path_proven"] is True
    assert adjudication["receiver_is_plus_0x340_child_object_proven"] is True
    assert adjudication["plus_0x340_child_object_is_selected_hdvehicle_proven"] is False
    assert adjudication["fun_00791020_is_fun_00755950_slot0_writer_proven"] is False
    assert adjudication["p1_3_control_producer_complete"] is False
    assert adjudication["external_provider_count"] == 7


def test_documentation_keeps_identity_and_semantics_open() -> None:
    text = DOC.read_text(encoding="utf-8")
    for token in (
        "*(setup_context) + 0x340",
        "numeric equality alone is not object identity",
        "+0x340 child == selected HDVehicle             = false",
        "FUN_00791020 is wheel-field writer             = false",
        "external provider count                        = 7",
        "No throttle, brake, steering",
        "NEXT_STEP",
    ):
        assert token in text
