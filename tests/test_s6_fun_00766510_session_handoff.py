from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00766510_session_handoff.json"
INPUT_HEADER = ROOT / "native_runtime/include/shift_fun_00766510_external_pass_input.hpp"
SESSION_HEADER = ROOT / "native_runtime/include/shift_native_vehicle_provider_session.hpp"
SESSION_SOURCE = ROOT / "native_runtime/src/native_vehicle_provider_session.cpp"
PHASE744_CMAKE = ROOT / "native_runtime/cmake/phase744.cmake"
PHASE745_CMAKE = ROOT / "native_runtime/cmake/phase745.cmake"


def test_phase745_evidence_preserves_provider_frontier() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun00766510SessionHandoff/1"
    assert payload["ready"] is True
    assert payload["platform_authority"] == "PC retail primary"

    deps = payload["dependencies"]
    assert deps["collision_output"] == "SHIFT.Fun00765c40ExternalPassResult/4"
    assert deps["query_scalar_handoff"] == "SHIFT.Fun00766510QueryScalarHandoff/1"
    assert deps["application_point_owner"] == "SHIFT.Fun00766510SelectedBMWApplicationPoint/1"

    runtime = payload["runtime_join"]
    assert runtime["typed_input_built_before_wheel_update"] is True
    assert runtime["typed_input_consumed_only_at_contact_response_anchor"] is True
    assert runtime["generic_two_body_compatibility_input_empty"] is True

    scope = payload["scope"]
    assert scope["external_provider_count_before"] == 7
    assert scope["external_provider_count_after"] == 7
    assert scope["provider_count_reduced"] is False
    assert scope["contact_response_provider_removed"] is False
    assert scope["complete_FUN_00766510_internalized"] is False


def test_phase745_typed_input_requires_both_selected_owned_values() -> None:
    header = INPUT_HEADER.read_text(encoding="utf-8")
    assert "SHIFT.Fun00766510ExternalPassInput/1" in header
    assert "bool selected_bmw_domain" in header
    assert "std::optional<Fun00766510QueryScalarHandoff> query_scalar_handoff" in header
    assert "std::optional<BodyAccumulatorVector3d> primary_application_point" in header
    assert "build_fun_00766510_selected_bmw_external_pass_input" in header
    assert "execute_fun_00765c40_to_00766510_query_scalar_handoff" in header
    assert "selected BMW FUN_00766510 input requires query handoff and +0x38f0 application point" in header
    assert "generic FUN_00766510 compatibility input cannot claim selected BMW ownership" in header


def test_phase745_session_builds_selected_input_before_residual_response() -> None:
    header = SESSION_HEADER.read_text(encoding="utf-8")
    source = SESSION_SOURCE.read_text(encoding="utf-8")

    assert "class NativeVehicleContactResponseProvider" in header
    assert "const physics::Fun00766510ExternalPassInput& input" in header
    assert "std::function<void(std::size_t)> compatibility_" in header
    assert "active top-level provider count remains seven" in header

    # Scope each lookup to the previous source-visible anchor.  The helper name
    # also appears in type/helper declarations above execute_explicit_step, so a
    # global source.index() would test declaration order rather than runtime order.
    observer = source.index("callbacks.current_body_observer =")
    app_point = source.index(
        "world_position_state->primary_application_point =", observer
    )
    fun_provider = source.index(
        "providers_.fun_00765c40(pass_index, external_input)", app_point
    )
    query_output = source.index("*result.query_output", fun_provider)
    build_input = source.index(
        "build_fun_00766510_selected_bmw_external_pass_input", query_output
    )
    wheel_callback = source.index("callbacks.wheel_update =", build_input)
    response_callback = source.index("callbacks.contact_response =", wheel_callback)
    response_provider = source.index("providers_.contact_response(", response_callback)

    assert observer < app_point < fun_provider < query_output < build_input
    assert build_input < wheel_callback < response_callback < response_provider
    assert "FUN_00766510 residual provider invoked before typed Phase745 handoff" in source
    assert "validate_fun_00766510_external_pass_input" in source


def test_phase745_cmake_is_chained_after_phase744() -> None:
    phase744 = PHASE744_CMAKE.read_text(encoding="utf-8")
    phase745 = PHASE745_CMAKE.read_text(encoding="utf-8")
    assert "include(${CMAKE_CURRENT_LIST_DIR}/phase745.cmake)" in phase744
    assert "shift_runtime_fun_00766510_session_handoff_check" in phase745
