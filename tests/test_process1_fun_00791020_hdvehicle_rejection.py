from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00791020_hdvehicle_rejection.json"
DOC = ROOT / "docs/PROCESS_1_FUN_00791020_HDVEHICLE_REJECTION.md"


def _payload() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_machine_chain_are_pinned() -> None:
    payload = _payload()
    assert payload["format"] == "SHIFT.Fun00791020HDVehicleRejection/1"
    assert payload["authority"]["retail_executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    chain = payload["machine_chain"]
    assert chain["scheduler_callsite"] == "0x007152f3"
    assert chain["initializer"] == "FUN_007125e0"
    assert chain["allocation_size"] == "0x2b90"
    assert chain["constructor"] == "FUN_0072ed20"
    assert chain["pointer_store"] == "0x0071263e [element+0] = allocated_object"
    assert chain["fun_00791020_receiver"] == "[element+0]+0x340"


def test_fresh_setup_root_is_not_selected_hdvehicle_root() -> None:
    payload = _payload()
    witness = payload["selected_hdvehicle_layout_witness"]
    assert witness["proven_field"] == "HDVehicle+0x66b4"
    assert witness["fresh_setup_allocation_size"] == "0x2b90"
    assert int("0x66b4", 16) >= int("0x2b90", 16)
    assert witness["same_root_object_possible"] is False


def test_rejection_keeps_p1_3_fail_closed() -> None:
    adjudication = _payload()["adjudication"]
    assert adjudication["setup_context_is_selected_hdvehicle_rejected"] is True
    assert adjudication["fun_00791020_rejected_as_selected_hdvehicle_root_writer"] is True
    assert adjudication["numeric_offset_match_is_same_object_proof"] is False
    assert adjudication["retail_input_control_provenance_proven"] is False
    assert adjudication["p1_3_control_producer_complete"] is False
    assert adjudication["external_provider_count"] == 7


def test_doc_preserves_next_writer_frontier() -> None:
    text = DOC.read_text(encoding="utf-8")
    for token in (
        "freshly allocated `0x2b90` object",
        "HDVehicle+0x66b4",
        "not the selected `HDVehicle` root",
        "No semantic class name is assigned",
        "HDVehicle+0x938/+0x13b8/+0x1e38/+0x28b8",
        "provider count",
        "NEXT_STEP",
    ):
        assert token in text
