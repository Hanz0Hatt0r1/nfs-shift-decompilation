from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_phase724_late_input_struct_is_removed() -> None:
    text = (ROOT / "native_runtime/include/shift_fun_007682c0_projection_state.hpp").read_text(encoding="utf-8")
    assert "struct Fun007682c0ExternalMachineInput" not in text
    assert "selected_bmw_native_session_player_difficulty()" in text


def test_phase724_session_owns_setup_gate_without_raw_provider() -> None:
    header = (ROOT / "native_runtime/include/shift_native_vehicle_provider_session.hpp").read_text(encoding="utf-8")
    source = (ROOT / "native_runtime/src/native_vehicle_provider_session.cpp").read_text(encoding="utf-8")
    assert "Fun007560c0MotionReadGateSetup motion_read_setup" in header
    assert "NativeVehicleMotionReadInputProvider" not in header
    assert "providers_.motion_read_setup" in source
    assert "providers_.motion_read_input" not in source
