from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_007682c0_derived_projection_state.json"
PROJECTION_HEADER = ROOT / "native_runtime/include/shift_fun_007682c0_projection_state.hpp"
SESSION_HEADER = ROOT / "native_runtime/include/shift_native_vehicle_provider_session.hpp"
SESSION_SOURCE = ROOT / "native_runtime/src/native_vehicle_provider_session.cpp"


def test_pc_projection_state_evidence_freezes_outer_update_order() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun007682c0DerivedProjectionState/1"
    assert payload["ready"] is True
    assert payload["platform_authority"] == "PC retail primary"
    assert payload["source"]["sha256"] == (
        "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
    )
    assert payload["source"]["xbox_360_recomp_required_for_claim"] is False
    fields = payload["fields"]
    assert fields["x"] == "HDVehicle+0x4084 f32"
    assert fields["z"] == "HDVehicle+0x408c f32"
    assert fields["initial_value"] == 0.0
    assert fields["external_provider_required_after_consumption"] is False
    order = payload["outer_update_order"]
    assert order["both_passes_use_previous_outer_state"] is True
    assert order["refresh_occurs_after_both_passes"] is True


def test_native_session_keeps_projection_internal_after_final_raw_provider_closure() -> None:
    projection_header = PROJECTION_HEADER.read_text(encoding="utf-8")
    session_header = SESSION_HEADER.read_text(encoding="utf-8")
    session_source = SESSION_SOURCE.read_text(encoding="utf-8")
    external_struct = projection_header.split(
        "struct Fun007682c0ExternalMachineInput", 1
    )[1].split("struct Fun007682c0DerivedProjectionState", 1)[0]
    assert "projection_field_x" not in external_struct
    assert "projection_field_z" not in external_struct
    assert "Fun007682c0DerivedProjectionState" in projection_header
    assert "compose_fun_007682c0_machine_input" in projection_header
    assert "derive_fun_007682c0_projection_state" in projection_header
    assert "NativeVehicleMotionReadInputProvider" not in session_header
    assert "RaceModePlayerDifficulty race_mode" in session_header
    assert "motion_read_projection_state_" in session_header
    assert "motion_read_projection_state() const" in session_header
    assert "compose_fun_007682c0_machine_input" in session_source
    assert "providers_.race_mode" in session_source
    assert "providers_.motion_read_input" not in session_source
    assert "derive_fun_007682c0_projection_state" in session_source
    assert "motion_read_projection_state_ = next_projection" in session_source
    assert "motion_read_projection_state_ = projection_before" in session_source


def test_projection_state_handoff_artifact_remains_historical() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    handoff = payload["handoff"]
    scope = payload["scope"]
    assert handoff["HDVehicle_0x4084_internalized"] is True
    assert handoff["HDVehicle_0x408c_internalized"] is True
    assert handoff["active_external_provider_count"] == 8
    assert handoff["provider_count_decremented"] is False
    assert handoff["raw_input_boundary_narrowed"] is True
    assert payload["remaining_raw_input_blockers"]
    assert scope["runtime_capture_required"] is False
    assert scope["original_game_execution_required"] is False
    assert scope["xbox_360_recomp_substituted_for_pc_authority"] is False
