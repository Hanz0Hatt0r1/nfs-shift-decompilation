from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_007530e0_slot2_vld4c8_producer.json"
DOC = ROOT / "docs/PROCESS_1_SLOT2_VLD4C8_PRODUCER.md"


def _payload() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_identity_and_contract_are_pinned() -> None:
    p = _payload()
    assert p["format"] == "SHIFT.Fun007530e0Slot2VehicleLoadData4c8Producer/1"
    assert p["ready"] is True
    assert p["authority"]["retail_executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    assert p["upstream_contract"] == "SHIFT.Fun007530e0Slot2SourceProducer/1"


def test_selected_hdvehicle_receiver_and_source_are_exact() -> None:
    p = _payload()
    call = p["selected_hdvehicle_callsite"]
    assert call["call_instruction"] == "0x0076e21a"
    assert call["receiver_setup"] == "0x0076e20a ECX = [HDVehicle+0x66b4]"
    assert call["source_base_setup"] == "0x0076e1c1 EBX = HDVehicle+0x4330"
    assert call["callee_param_3"] == "HDVehicle+0x4330"
    assert call["callee_mode"] == 4
    assert call["same_vehicle_load_data_receiver_proven"] is True


def test_exact_vld4c8_value_transfer_is_pinned() -> None:
    p = _payload()
    xfer = p["value_transfer"]
    assert xfer["source_load"] == "0x007c48ba EAX = [EDI+0x21b8]"
    assert xfer["store"] == "0x007c48cb fstp qword [ESI+0x4c8]"
    assert xfer["normalized_source"] == "HDVehicle+0x64e8"
    assert xfer["normalization"] == "0x4330 + 0x21b8 = 0x64e8"
    assert xfer["exact_transfer_when_source_not_minus_one"] == (
        "VehicleLoadData+0x4c8 = f64(int32(HDVehicle+0x64e8))"
    )


def test_scope_remains_fail_closed() -> None:
    a = _payload()["adjudication"]
    assert a["vehicle_load_data_4c8_writer_identified"] is True
    assert a["same_vehicle_load_data_receiver_proven"] is True
    assert a["exact_value_transfer_proven"] is True
    assert a["hdvehicle_64e8_upstream_writer_proven"] is False
    assert a["vehicle_load_data_3a0_upstream_writer_proven"] is False
    assert a["vehicle_load_data_3a8_upstream_writer_proven"] is False
    assert a["retail_input_control_provenance_proven"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7


def test_documentation_preserves_semantic_boundary() -> None:
    text = DOC.read_text(encoding="utf-8")
    for token in (
        "HDVehicle+0x64e8",
        "VehicleLoadData+0x4c8",
        "throttle/brake/steering",
        "P1.3 complete",
        "provider count",
        "NEXT_STEP",
    ):
        assert token in text
