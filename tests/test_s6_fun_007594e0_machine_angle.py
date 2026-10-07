from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_007594e0_machine_angle.json"
HEADER = ROOT / "native_runtime/include/shift_fun_007594e0_machine_angle.hpp"
SOURCE = ROOT / "native_runtime/src/fun_007594e0_machine_angle.cpp"
PROJECTION = ROOT / "native_runtime/include/shift_fun_007682c0_projection_state.hpp"
SESSION = ROOT / "native_runtime/src/native_vehicle_provider_session.cpp"


def test_pc_machine_angle_evidence_is_hash_locked_and_positive() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun007594e0MachineAngle/1"
    assert payload["ready"] is True
    assert payload["platform_authority"] == "PC retail primary"
    assert payload["retail"]["executable_md5"] == "705af8b420e5eb1e3834ac43d5533c6b"
    spans = {row["function"]: row for row in payload["machine_spans"]}
    assert spans["FUN_007594e0"]["raw_byte_sha256"] == (
        "a3b85095f536be8f707ad1f5431e28912cd5b492748b5776234fd8d5ba6c9088"
    )
    assert spans["FUN_0076f970 writer site"]["raw_byte_sha256"] == (
        "f0952defd5357bdbcdb0985f287e3031012e6477da2b0b6adb18952108613816"
    )


def test_formula_keeps_retail_basis_gate_x87_and_signed_zero_semantics() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    formula = payload["machine_formula"]
    assert formula["gate"] == "strict planar_squared > 0.1 f64"
    assert formula["retail_x87_control_word"] == "0x027f"
    assert formula["x87_instruction"] == "FPATAN"
    assert formula["signed_zero_quadrants_preserved"] is True
    assert formula["host_std_atan2_substitution_allowed"] is False
    source = SOURCE.read_text(encoding="utf-8")
    assert "fpatan" in source
    assert "0x027fu" in source
    assert "std::atan2" not in source


def test_legacy_compatibility_marker_cannot_supply_steering_or_angle_mode() -> None:
    projection = PROJECTION.read_text(encoding="utf-8")
    struct_text = projection.split("struct Fun007682c0ExternalMachineInput", 1)[1].split("};", 1)[0]
    assert "float steering" not in struct_text
    assert "angle_mode" not in struct_text
    compose_text = projection.split("compose_fun_007682c0_machine_input", 1)[1]
    assert "float steering" in compose_text
    assert "RaceModePlayerDifficulty" in compose_text
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["native_consumption"]["external_steering_field_required"] is False


def test_session_derives_one_steering_value_before_both_passes() -> None:
    session = SESSION.read_text(encoding="utf-8")
    machine_call = session.index("execute_fun_007594e0_machine_angle")
    pass_provider = session.index("Fun0076d100MotionReadMachineInputProvider pass_provider")
    compose = session.index("compose_fun_007682c0_machine_input")
    assert machine_call < pass_provider < compose
    assert "providers_.motion_read_input" not in session
    assert "const float steering = machine_angle.steering" in session
    assert "[this, &telemetry, steering]" in session
    setup_arg = session.index("providers_.motion_read_setup,", compose)
    race_arg = session.index("providers_.race_mode,", compose)
    steering_arg = session.index("steering,", compose)
    load_arg = session.index("load_state->terms,", compose)
    projection_arg = session.index("motion_read_projection_state_", compose)
    assert compose < setup_arg < race_arg < steering_arg < load_arg < projection_arg
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    timing = payload["timing"]
    assert timing["writer_executes_before_pass_0"] is True
    assert timing["writer_executes_before_pass_1"] is True
    assert timing["one_f32_value_shared_by_both_passes"] is True
