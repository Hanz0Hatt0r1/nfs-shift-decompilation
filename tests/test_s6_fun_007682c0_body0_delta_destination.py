from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / "evidence/fun_007682c0_body0_delta_destination.json"
BMW_BIND = ROOT / "evidence/bmw_body0_vehicle_root_bind_relation.json"
BODY_ADAPTER_HEADER = ROOT / "native_runtime/include/shift_body_record_adapter.hpp"
BODY_ADAPTER_SOURCE = ROOT / "native_runtime/src/body_record_adapter.cpp"
MOTION_SOURCE = ROOT / "native_runtime/src/fun_00770e80_motion_read_effect_provider_chain.cpp"
SESSION_SOURCE = ROOT / "native_runtime/src/native_vehicle_provider_session.cpp"


def test_pc_source_destination_proof_joins_existing_bmw_body0_identity() -> None:
    proof = json.loads(PROOF.read_text(encoding="utf-8"))
    bind = json.loads(BMW_BIND.read_text(encoding="utf-8"))

    assert proof["format"] == "SHIFT.Fun007682c0Body0DeltaDestination/1"
    assert proof["ready"] is True
    assert proof["platform_authority"] == "PC retail primary"
    assert proof["source"]["file"] == "SHIFT.exe.c"
    assert proof["source"]["sha256"] == (
        "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
    )
    assert proof["source"]["retail_executable_md5"] == "705af8b420e5eb1e3834ac43d5533c6b"
    assert proof["source"]["xbox_360_recomp_required_for_claim"] is False

    destination = proof["destination"]
    assert destination["pointer_load_source_line"] == 760240
    assert destination["pointer_load"] == "iVar1 = *(int *)((int)this + 0x33a0)"
    assert destination["application_source_lines"] == [760242, 760243]
    assert destination["vehicle_pointer_field"] == "HDVehicle+0x33a0"
    assert destination["body_record_offset"] == "0x50"
    assert "f32 add" in destination["source_numeric_shape"]

    aliases = bind["identity_aliases"]
    assert proof["identity_join"]["contract"] == bind["format"]
    assert aliases["global_HDVehicle"] == proof["identity_join"]["global_HDVehicle"]
    assert aliases["chassis_BODY_pointer_field"] == "HDVehicle+0x33a0"
    assert aliases["chassis_BODY_pointer_field"] == proof["identity_join"]["chassis_BODY_pointer_field"]
    assert proof["identity_join"]["selected_chassis_BODY_index"] == 0
    assert proof["identity_join"]["destination_is_retail_BMW_chassis_BODY0"] is True


def test_native_chain_consumes_body0_destination_without_external_consumer() -> None:
    proof = json.loads(PROOF.read_text(encoding="utf-8"))
    header = BODY_ADAPTER_HEADER.read_text(encoding="utf-8")
    adapter = BODY_ADAPTER_SOURCE.read_text(encoding="utf-8")
    motion = MOTION_SOURCE.read_text(encoding="utf-8")
    session = SESSION_SOURCE.read_text(encoding="utf-8")

    assert proof["handoff"]["FUN_007682c0_delta_application_internalization_ready"] is True
    assert proof["handoff"]["FUN_007682c0_delta_consumer_external_provider_required"] is False
    assert proof["handoff"]["active_external_provider_count_after_consumption"] == 8

    assert "apply_fun_007682c0_body0_accumulator_y_delta" in header
    assert "body_record_offset::kAccumulatorA[1]" in adapter
    assert "const float current_f32 = static_cast<float>(current)" in adapter
    assert "const float delta_f32 = static_cast<float>(accumulator_y_delta)" in adapter
    assert "const float next_f32 = current_f32 + delta_f32" in adapter
    assert "write_f64_le(record, offset, static_cast<double>(next_f32))" in adapter

    assert "adapted.post_pass_body_mutator" in motion
    assert "apply_fun_007682c0_body0_accumulator_y_delta" in motion
    assert "if (delta_consumer)" in motion
    assert "all active physics-pass providers" in motion

    assert "all eight active external provider boundaries" in session
    required_prefix = session.split("NativeVehicleProviderSession::NativeVehicleProviderSession", 1)[0]
    assert "!providers.motion_read_delta_consumer" not in required_prefix
    assert "if (providers_.motion_read_delta_consumer)" in session


def test_proof_keeps_effect_production_and_complete_semantics_fail_closed() -> None:
    proof = json.loads(PROOF.read_text(encoding="utf-8"))
    limits = proof["limits"]

    assert limits["FUN_007682c0_effect_production_internalized"] is False
    assert limits["FUN_007595d0_complete_input_production_proven"] is False
    assert limits["x87_magnitude_and_response_boundaries_proven"] is False
    assert limits["complete_FUN_007682c0_semantics_claimed"] is False
    assert limits["xbox_360_recomp_substituted_for_pc_authority"] is False
    assert limits["runtime_capture_required"] is False
    assert limits["original_game_execution_required"] is False
