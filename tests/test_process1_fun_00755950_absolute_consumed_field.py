from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00755950_absolute_consumed_field_machine_proof.json"
DOC = ROOT / "docs/PROCESS_1_FUN_00755950_ABSOLUTE_CONSUMED_FIELD.md"


def _load() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_pc_retail_authority_and_consumer_slots_are_pinned() -> None:
    payload = _load()
    assert payload["format"] == "SHIFT.Fun00755950AbsoluteConsumedFieldMachineProof/1"
    assert payload["ready"] is True
    assert payload["authority"]["platform"] == "PC retail 1.02"
    assert payload["authority"]["retail_executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    consumer = payload["consumer"]
    assert consumer["call_instruction"] == "0x00758d6b"
    assert consumer["read_instruction"] == "0x00755958"
    assert consumer["read_operand"] == "f64 [EDX+0x538]"
    assert consumer["slot_offsets"] == ["0x938", "0x13b8", "0x1e38", "0x28b8"]


def test_fun_007618f0_same_literal_offset_is_rejected_after_base_normalization() -> None:
    payload = _load()
    rejected = payload["false_candidate_exclusion"]
    assert rejected["function"] == "FUN_007618f0"
    assert rejected["receiver_proven_as"] == "HDVehicle"
    assert rejected["candidate_write_instruction"] == "0x00761b67"
    assert rejected["normalized_hdvehicle_offset_expression"] == "0xc80+slot*0xa80"
    assert rejected["slot_offsets"] == ["0xc80", "0x1700", "0x2180", "0x2c00"]
    assert rejected["matches_fun_00755950_consumed_slots"] is False


def test_next_writer_candidate_remains_receiver_gated() -> None:
    payload = _load()
    candidates = payload["machine_writer_candidates_needing_receiver_join"]
    assert candidates == [
        {
            "function": "FUN_00791020",
            "writes": ["f32 receiver+0x938"],
            "write_instructions": ["0x007910f8", "0x0079113e"],
            "direct_callers_seen_in_retail_machine": ["0x00799f7e", "0x00799ff3"],
            "receiver_equals_selected_hdvehicle_proven": False,
        }
    ]
    adjudication = payload["adjudication"]
    assert adjudication["fun_00755950_absolute_consumed_slots_proven"] is True
    assert adjudication["fun_007618f0_literal_0x538_writer_is_same_field"] is False
    assert adjudication["exact_upstream_writer_owner_proven"] is False
    assert adjudication["retail_input_control_provenance_proven"] is False
    assert adjudication["p1_3_control_producer_complete"] is False
    assert adjudication["external_provider_count"] == 7


def test_documentation_preserves_nonsemantic_boundary() -> None:
    text = DOC.read_text(encoding="utf-8")
    for token in (
        "HDVehicle + 0x938",
        "HDVehicle + 0xC80",
        "incorrect by exactly `0x348` bytes",
        "FUN_00791020",
        "exact upstream writer owner proven          = false",
        "external provider count                      = 7",
        "No throttle, brake, steering",
        "NEXT_STEP",
    ):
        assert token in text
