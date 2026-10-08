from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00791020_hdvehicle_rejection.json"
DOC = ROOT / "docs/PROCESS_1_FUN_00791020_HDVEHICLE_REJECTION.md"


def _payload() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_retail_identity_are_pinned() -> None:
    payload = _payload()
    assert payload["format"] == "SHIFT.Fun00791020HDVehicleRejection/1"
    assert payload["ready"] is True
    assert payload["authority"]["retail_executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )


def test_setup_context_is_a_fresh_0x2b90_object() -> None:
    payload = _payload()
    path = payload["setup_element_path"]
    assert path["scheduler_callsite"] == "0x007152f3"
    assert path["element_initializer"] == "FUN_007125e0"
    assert path["allocated_object_size"] == "0x2b90"
    assert "0x0071263e [element+0] = allocated_object" in path["allocation_sequence"]
    assert path["fun_0074e1a0_setup_context"] == "[element+0]"
    assert path["fun_00791020_receiver"] == "[element+0]+0x340"


def test_allocated_setup_root_cannot_be_selected_hdvehicle_root() -> None:
    payload = _payload()
    witness = payload["hdvehicle_layout_witness"]
    assert witness["proven_hdvehicle_field"] == "HDVehicle+0x66b4"
    assert witness["allocated_setup_object_size"] == "0x2b90"
    assert int("0x66b4", 16) >= int(witness["allocated_setup_object_size"], 16)
    assert witness["same_root_object_possible"] is False


def test_candidate_is_rejected_without_promoting_semantics() -> None:
    payload = _payload()
    adjudication = payload["adjudication"]
    assert adjudication["setup_context_is_selected_hdvehicle_rejected"] is True
    assert adjudication["fun_00791020_rejected_as_hdvehicle_root_writer"] is True
    assert adjudication["fun_00791020_is_fun_00755950_hdvehicle_slot0_writer_proven"] is False
    assert adjudication["retail_input_control_provenance_proven"] is False
    assert adjudication["p1_3_control_producer_complete"] is False
    assert adjudication["external_provider_count"] == 7


def test_document_preserves_fail_closed_boundary() -> None:
    text = DOC.read_text(encoding="utf-8")
    for token in (
        "freshly allocated `0x2b90` object",
        "HDVehicle+0x66b4",
        "not the selected `HDVehicle` root",
        "does **not** assign a semantic class",
        "P1.3 complete",
        "provider count",
        "NEXT_STEP",
    ):
        assert token in text
