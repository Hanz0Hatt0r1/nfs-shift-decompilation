from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_007682c0_machine_effect_production.json"
KERNEL = ROOT / "native_runtime/src/fun_007682c0_machine_effect.cpp"
CHAIN = ROOT / "native_runtime/src/fun_00770e80_motion_read_machine_input_provider_chain.cpp"
SESSION = ROOT / "native_runtime/src/native_vehicle_provider_session.cpp"
HEADER = ROOT / "native_runtime/include/shift_native_vehicle_provider_session.hpp"


def test_machine_effect_contract_is_pc_authoritative_and_ready() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun007682c0MachineEffectProduction/1"
    assert payload["ready"] is True
    assert payload["platform_authority"] == "PC retail primary"
    assert payload["retail"]["executable_md5"] == "705af8b420e5eb1e3834ac43d5533c6b"
    assert payload["retail"]["xbox_360_recomp_required_for_claim"] is False
    assert len(payload["machine_spans"]) == 5
    assert all(len(row["raw_byte_sha256"]) == 64 for row in payload["machine_spans"])


def test_machine_effect_contract_freezes_x87_and_raw_input_boundaries() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    x87 = payload["x87"]
    raw = payload["raw_inputs"]
    assert x87["fsqrt_instruction"] == "0x00900d6c"
    assert x87["retail_control_word"] == "0x027f"
    assert x87["host_std_sqrt_substitution_allowed"] is False
    assert raw["caller_gate"] == "HDVehicle+0xe0 != 0"
    assert raw["steering"] == "HDVehicle+0x4068 f32"
    assert raw["load_terms_qword"] == [
        "HDVehicle+0xb38",
        "HDVehicle+0x15b8",
        "HDVehicle+0x2038",
        "HDVehicle+0x2ab8",
    ]
    assert raw["projection_field_x"] == "HDVehicle+0x4084 f32"
    assert raw["projection_field_z"] == "HDVehicle+0x408c f32"
    assert raw["response_field_4054"] == "HDVehicle+0x4054 f32"
    assert raw["angle_mode"] == "DAT_00c128cc i32"


def test_active_native_path_no_longer_accepts_late_raw_input_provider() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    native = payload["native_consumption"]
    assert native["external_precomputed_effect_accepted_by_active_session"] is False
    assert native["external_delta_consumer_accepted_by_active_session"] is False
    assert native["effect_arithmetic_internal"] is True
    assert native["body0_delta_application_internal"] is True

    header = HEADER.read_text(encoding="utf-8")
    session = SESSION.read_text(encoding="utf-8")
    chain = CHAIN.read_text(encoding="utf-8")
    kernel = KERNEL.read_text(encoding="utf-8")
    assert "NativeVehicleMotionReadInputProvider" not in header
    assert "motion_read_input{}" not in header
    assert "providers_.motion_read_input" not in session
    assert "providers_.race_mode" in session
    assert "execute_explicit_motion_read_machine_input_update" in session
    assert "execute_fun_007682c0_machine_effect" in chain
    assert "apply_fun_007682c0_body0_accumulator_y_delta" in chain
    assert "fsqrt" in kernel
    assert "std::sqrt(" not in kernel


def test_original_machine_effect_artifact_remains_historical_evidence() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    handoff = payload["handoff"]
    blockers = payload["remaining_blockers"]
    assert handoff["FUN_007682c0_effect_production_internalized"] is True
    assert handoff["FUN_007595d0_response_arithmetic_internalized"] is True
    assert handoff["FUN_0075ada0_geometry_internalized"] is True
    assert handoff["x87_fsqrt_boundary_internalized"] is True
    assert handoff["active_external_provider_count"] == 8
    assert [row["id"] for row in blockers] == [
        "fun-007682c0-raw-input-producer-refresh"
    ]
    assert payload["scope"]["runtime_capture_required"] is False
    assert payload["scope"]["original_game_execution_required"] is False
