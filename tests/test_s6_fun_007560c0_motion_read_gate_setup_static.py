from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_phase723_late_input_has_only_angle_mode() -> None:
    text = (ROOT / "native_runtime/include/shift_fun_007682c0_projection_state.hpp").read_text(encoding="utf-8")
    struct = text.split("struct Fun007682c0ExternalMachineInput", 1)[1].split("};", 1)[0]
    assert "caller_gate_open" not in struct
    assert "angle_mode" in struct


def test_phase723_session_owns_setup_gate() -> None:
    header = (ROOT / "native_runtime/include/shift_native_vehicle_provider_session.hpp").read_text(encoding="utf-8")
    source = (ROOT / "native_runtime/src/native_vehicle_provider_session.cpp").read_text(encoding="utf-8")
    assert "Fun007560c0MotionReadGateSetup motion_read_setup" in header
    assert "providers_.motion_read_setup" in source
