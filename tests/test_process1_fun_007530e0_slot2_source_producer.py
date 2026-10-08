from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_007530e0_slot2_source_producer.json"
DOC = ROOT / "docs/PROCESS_1_FUN_007530E0_SLOT2_SOURCE_PRODUCER.md"


def _payload() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_retail_identity_are_pinned() -> None:
    p = _payload()
    assert p["format"] == "SHIFT.Fun007530e0Slot2SourceProducer/1"
    assert p["ready"] is True
    assert p["authority"]["retail_executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )


def test_destination_and_vehicle_load_data_owners_are_explicit() -> None:
    p = _payload()
    assert p["target_fields"] == ["HDVehicle+0x5238", "HDVehicle+0x5240", "HDVehicle+0x524c"]
    assert p["vehicle_load_data_owner"]["pointer"] == "*(HDVehicle+0x66b4)"
    chain = p["call_chain"]
    assert "0x007c3b1e EDI = arg3 = HDVehicle+0x4330" in chain["fun_007c3b00"]
    assert "0x007bfbff ESI = arg1 = HDVehicle+0x4330" in chain["fun_007bfbe0"]


def test_exact_source_to_destination_transfer_is_pinned() -> None:
    transfer = _payload()["copy_transform"]
    assert transfer["function"] == "FUN_007c5a20"
    assert transfer["writes"] == [
        "HDVehicle+0x5238 = f64(VehicleLoadData+0x3a0)",
        "HDVehicle+0x5240 = f64(VehicleLoadData+0x3a8)",
        "HDVehicle+0x524c = FUN_00901310(x87(VehicleLoadData+0x4c8)) return EAX",
    ]
    assert transfer["fun_00901310_integer_rounding_semantics_promoted"] is False


def test_p1_3_and_provider_gates_stay_fail_closed() -> None:
    a = _payload()["adjudication"]
    assert a["slot2_source_field_producer_chain_proven"] is True
    assert a["hdvehicle_destination_identity_proven"] is True
    assert a["vehicle_load_data_source_identity_proven"] is True
    assert a["source_value_transfer_proven"] is True
    assert a["vehicle_load_data_field_upstream_producers_proven"] is False
    assert a["retail_input_control_provenance_proven"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7


def test_doc_names_next_exact_frontier_without_semantic_promotion() -> None:
    text = DOC.read_text(encoding="utf-8")
    for token in (
        "VehicleLoadData+0x3a0",
        "VehicleLoadData+0x3a8",
        "VehicleLoadData+0x4c8",
        "FUN_00901310",
        "retail input/control provenance",
        "provider count",
        "NEXT_STEP",
    ):
        assert token in text
