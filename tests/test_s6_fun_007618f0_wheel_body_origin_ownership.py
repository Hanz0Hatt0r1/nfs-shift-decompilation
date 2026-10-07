from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_007618f0_wheel_body_origin_ownership.json"
HEADER = ROOT / "native_runtime/include/shift_fun_007618f0_wheel_body_origin_ownership.hpp"
PHASE728 = ROOT / "native_runtime/include/shift_fun_007618f0_local_sample_producer.hpp"
TOPOLOGY = ROOT / "native_runtime/include/shift_bmw_wheel_spindle_body_topology.hpp"
BODY = ROOT / "native_runtime/include/shift_body_record_adapter.hpp"


def test_phase737_evidence_joins_phase634_702_to_phase728_inputs() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun007618f0WheelBodyOriginOwnershipEvidence/1"
    assert payload["phase"] == 737
    assert payload["pc_authority"]["sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    join = payload["ownership_join"]
    assert "HDVehicle+0x820" in join["phase634_proof"]
    assert "HDVehicle+0x12a0" in join["phase634_proof"]
    assert "FL=3" in join["phase702_proof"]
    assert "FR=4" in join["phase702_proof"]
    assert join["body_record_stride"] == "0x170"
    assert join["body_origin_offsets"] == ["0x00", "0x08", "0x10"]
    assert join["phase728_inputs_closed"] == {
        "hdvehicle_pointer_vec_0820": "current persistent BODY[3] origin",
        "hdvehicle_pointer_vec_12a0": "current persistent BODY[4] origin",
    }


def test_phase737_native_contract_uses_proven_bmw_body_indices() -> None:
    header = HEADER.read_text(encoding="utf-8")
    topology = TOPOLOGY.read_text(encoding="utf-8")
    body = BODY.read_text(encoding="utf-8")
    phase728 = PHASE728.read_text(encoding="utf-8")

    assert "kFun007618f0HdVehicleWheelPointer0820 = 0x820u" in header
    assert "kFun007618f0HdVehicleWheelPointer12a0 = 0x12a0u" in header
    assert "bmw_m3_e36_retail_wheel_spindle_body_topology()" in header
    assert "topology.wheel_body_indices[kFun007618f0FlWheelSlot]" in header
    assert "topology.wheel_body_indices[kFun007618f0FrWheelSlot]" in header
    assert "body_record_offset::kOrigin" in header
    assert "compose_fun_007618f0_input_from_current_bmw_wheel_bodies" in header

    assert "wheel_body_indices{{3u, 4u, 7u, 8u}}" in topology
    assert "kBmwM3E36RetailBodyCount = 11u" in topology
    assert "kBodyRecordSize = 0x170u" in body
    assert "kOrigin = {0x00u, 0x08u, 0x10u}" in body
    assert "hdvehicle_pointer_vec_0820" in phase728
    assert "hdvehicle_pointer_vec_12a0" in phase728


def test_phase737_leaves_only_second_source_fields_external() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["ownership_join"]["remaining_phase728_inputs"] == [
        "second FUN_007618f0 source argument f64 at +0x338",
        "second FUN_007618f0 source argument inline f64 vec3 at +0x918",
    ]
    handoff = payload["native_handoff"]
    assert handoff["selected_body_count"] == 11
    assert handoff["wheel_body_indices"] == [3, 4]
    assert handoff["external_wheel_origin_vectors_required"] is False
    assert handoff["top_level_external_provider_count"] == 7


def test_phase737_does_not_prematurely_claim_runtime_anchor_closure() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    timing = payload["runtime_timing"]
    assert timing["current_body_buffer_is_persistent"] is True
    assert timing["phase729_current_body_observer_available_per_fun_0076d100_pass"] is True
    assert timing["pass1_observes_post_first_half_step_body_state"] is True
    assert timing["phase737_wired_into_fun_00765c40_production_anchor"] is False
    assert "second FUN_007618f0 source argument" in timing["reason_not_wired"]
