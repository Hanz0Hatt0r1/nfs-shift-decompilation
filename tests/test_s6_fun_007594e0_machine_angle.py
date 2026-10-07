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
    assert payload["retail"]["executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    spans = {row["function"]: row for row in payload["machine_spans"]}
    assert spans["FUN_007594e0"]["raw_byte_sha256"] == (
        "a3b85095f536be8f707ad1f5431e28912cd5b492748b5776234fd8d5ba6c9088"
    )
    assert spans["FUN_0076f970 writer site"]["raw_byte_sha256"] == (
        "f0952defd5357bdbcdb0985f287e3031012e6477da2b0b6adb18952108613816"
    )
    assert spans["FUN_00770e80 early caller site"]["raw_byte_sha256"] == (
        "8b74279675a0814b1989e5c4735ceab5561dc98be88b81ff5b09f973834c0fb5"
    )
    assert spans["CRT atan2 finite normal path"]["raw_byte_sha256"] == (
        "5e2ce07cb2bdf3f80ce831dff7b2ad965af8022dd59c434c0fb7bd68be411c4f"
    )


def test_formula_keeps_retail_basis_gate_x87_and_signed_zero_semantics() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    formula = payload["machine_formula"]
    assert formula["local_x"] == "basis[3]*vy + basis[0]*vx + basis[6]*vz"
    assert formula["local_z"] == "basis[2]*vx + basis[5]*vy + basis[8]*vz"
    assert formula["gate"] == "strict planar_squared > 0.1 f64"
    assert formula["open_gate_result"] == "f32(CRT_x87_atan2(-local_x, -local_z))"
    assert formula["retail_x87_control_word"] == "0x027f"
    assert formula["x87_instruction"] == "FPATAN"
    assert formula["signed_zero_quadrants_preserved"] is True
    assert formula["host_std_atan2_substitution_allowed"] is False

    source = SOURCE.read_text(encoding="utf-8")
    assert "fpatan" in source
    assert "0x027fu" in source
    assert "planar_squared > kRetailPlanarSquaredGate" in source
    assert "std::atan2" not in source
    assert "basis[3]" in source and "basis[6]" in source
    assert "basis[2]" in source and "basis[8]" in source


def test_active_external_machine_input_cannot_supply_steering_anymore() -> None:
    projection = PROJECTION.read_text(encoding="utf-8")
    struct_text = projection.split("struct Fun007682c0ExternalMachineInput", 1)[1].split("};", 1)[0]
    assert "float steering" not in struct_text
    assert "float steering" in projection.split("compose_fun_007682c0_machine_input", 1)[1]
    assert "legacy.steering" not in struct_text

    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["native_consumption"]["external_steering_field_required"] is False
    blockers = " ".join(payload["remaining_raw_input_blockers"])
    assert "+0x4068" not in blockers


def test_session_derives_one_steering_value_before_both_passes() -> None:
    session = SESSION.read_text(encoding="utf-8")
    machine_call = session.index("execute_fun_007594e0_machine_angle")
    pass_provider = session.index("Fun0076d100MotionReadMachineInputProvider pass_provider")
    external_provider_call = session.index("providers_.motion_read_input(pass_index)")
    assert machine_call < pass_provider < external_provider_call
    assert "const float steering = machine_angle.steering" in session
    assert "[this, &telemetry, steering]" in session
    assert (
        "external,\n                        steering,\n                        response_field_4054_,\n"
        "                        motion_read_projection_state_"
    ) in session

    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    timing = payload["timing"]
    assert timing["writer_executes_before_pass_0"] is True
    assert timing["writer_executes_before_pass_1"] is True
    assert timing["one_f32_value_shared_by_both_passes"] is True
    assert payload["scope"]["runtime_capture_required"] is False
    assert payload["scope"]["xbox_360_recomp_substituted_for_pc_authority"] is False
