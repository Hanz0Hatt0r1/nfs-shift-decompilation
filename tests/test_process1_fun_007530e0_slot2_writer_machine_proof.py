from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_007530e0_slot2_writer_machine_proof.json"
DOC = ROOT / "docs/PROCESS_1_FUN_007530E0_SLOT2_WRITER_MACHINE_PROOF.md"


def _payload() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_retail_identity_are_pinned() -> None:
    payload = _payload()
    assert payload["format"] == "SHIFT.Fun007530e0Slot2WriterMachineProof/1"
    assert payload["ready"] is True
    assert payload["authority"]["platform"] == "PC retail 1.02"
    assert payload["authority"]["retail_executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )


def test_consumer_and_writer_join_target_slot2() -> None:
    payload = _payload()
    consumer = payload["consumer_join"]
    writer = payload["writer_function"]
    assert consumer["target_slot"] == 2
    assert consumer["target_absolute_offset"] == "HDVehicle+0x1e38"
    assert consumer["target_width"] == "f64"
    assert writer["entry"] == "0x007530e0"
    assert writer["sole_direct_callsite"] == "0x0076ce7b"
    assert writer["direct_callsite_count"] == 1
    assert "0x00753102 fstp qword [ecx+0x1e38]" in writer["instructions"]
    assert writer["exact_update"]["store_reference"] == "HDVehicle+0x2e10 = x"


def test_caller_keeps_same_hdvehicle_receiver() -> None:
    caller = _payload()["caller_receiver_proof"]
    assert caller["caller"] == "FUN_0076b280"
    assert caller["existing_hdvehicle_contract"] == "SHIFT.BMWOffset33bStoreProvenance/1"
    assert caller["caller_prologue"] == "0x0076b2c9 ESI = ECX"
    assert caller["call_receiver_setup"] == "0x0076ce5e ECX = ESI"
    assert caller["same_hdvehicle_receiver_proven"] is True


def test_source_owner_is_hdvehicle_plus_4330() -> None:
    source = _payload()["source_owner_proof"]
    assert source["enclosing_initializer"] == "FUN_0076df50"
    assert source["source_base_instruction"] == "0x0076e1c1 EBX = HDVehicle+0x4330"
    assert source["first_physical_stack_argument"] == "HDVehicle+0x4330"
    assert source["second_physical_stack_argument"] == "*(HDVehicle+0x66b4)"
    assert source["source_owner_proven"] is True


def test_argument_fields_are_normalized_to_hdvehicle() -> None:
    argument = _payload()["caller_argument_proof"]
    assert argument["source_pointer_load"] == "0x0076ce56 EAX = [EBX+0x8] = HDVehicle+0x4330"
    assert argument["normalized_fields"] == {
        "base": "HDVehicle+0x4330",
        "f64_addend": "HDVehicle+0x5238",
        "f64_scale": "HDVehicle+0x5240",
        "int32_index": "HDVehicle+0x524c",
    }
    assert argument["exact_argument_formula"] == (
        "x = f64(HDVehicle+0x5238) + f64(int32(HDVehicle+0x524c)) * f64(HDVehicle+0x5240)"
    )
    assert argument["control_semantics_proven"] is False


def test_p1_3_and_provider_gates_remain_fail_closed() -> None:
    adjudication = _payload()["adjudication"]
    assert adjudication["slot2_absolute_writer_identified"] is True
    assert adjudication["same_hdvehicle_receiver_proven"] is True
    assert adjudication["writer_value_formula_proven"] is True
    assert adjudication["first_stack_argument_owner_proven"] is True
    assert adjudication["normalized_source_fields_proven"] is True
    assert adjudication["source_field_value_producers_proven"] is False
    assert adjudication["retail_input_control_provenance_proven"] is False
    assert adjudication["p1_3_control_producer_complete"] is False
    assert adjudication["external_provider_count"] == 7


def test_doc_preserves_semantic_boundary_and_next_step() -> None:
    text = DOC.read_text(encoding="utf-8")
    for token in (
        "HDVehicle+0x1e38",
        "HDVehicle+0x4330",
        "HDVehicle+0x5238",
        "HDVehicle+0x5240",
        "HDVehicle+0x524c",
        "retail input/control provenance",
        "provider count",
        "NEXT_STEP",
    ):
        assert token in text
