from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/hdvehicle_64e8_writer_frontier.json"
DOC = ROOT / "docs/PROCESS_1_HDVEHICLE_64E8_WRITER_FRONTIER.md"


def _payload() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_target_normalization_and_contract_are_pinned() -> None:
    payload = _payload()
    assert payload["format"] == "SHIFT.HDVehicle64e8WriterFrontier/1"
    assert payload["authority"]["retail_executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    target = payload["target"]
    assert target["root_storage"] == "HDVehicle+0x64e8"
    assert target["owned_subobject_base"] == "HDVehicle+0x4330"
    assert target["subobject_offset"] == "0x21b8"
    assert int("0x4330", 16) + int("0x21b8", 16) == int("0x64e8", 16)


def test_literal_writer_surface_is_finite_and_fail_closed() -> None:
    payload = _payload()
    rows = payload["literal_write_candidates"]
    assert payload["candidate_count"] == 4
    assert [row["instruction"] for row in rows] == [
        "0x004b86cf",
        "0x004bb205",
        "0x004bca6b",
        "0x00d775ee",
    ]
    assert all(row["receiver_identity_joined_to_hdvehicle_4330"] is False for row in rows)


def test_constructor_and_update_are_not_promoted_as_direct_writers() -> None:
    paths = _payload()["known_owned_subobject_paths"]
    assert paths["constructor"]["function"] == "FUN_00772200"
    assert paths["constructor"]["direct_literal_write_to_0x21b8"] is False
    assert paths["update"]["function"] == "FUN_00772570"
    assert paths["update"]["direct_literal_write_to_0x21b8"] is False


def test_p1_3_and_provider_gates_remain_open() -> None:
    adjudication = _payload()["adjudication"]
    assert adjudication["full_literal_write_candidate_set_bounded"] is True
    assert adjudication["exact_hdvehicle_64e8_writer_proven"] is False
    assert adjudication["alias_or_callee_writer_exhausted"] is False
    assert adjudication["retail_input_control_provenance_proven"] is False
    assert adjudication["p1_3_control_producer_complete"] is False
    assert adjudication["external_provider_count"] == 7


def test_doc_keeps_receiver_identity_as_required_gate() -> None:
    text = DOC.read_text(encoding="utf-8")
    for token in (
        "0x004b86cf",
        "0x004bb205",
        "0x004bca6b",
        "0x00d775ee",
        "HDVehicle+0x4330",
        "alias/callee writer surface exhausted",
        "provider count",
        "NEXT_STEP",
    ):
        assert token in text
