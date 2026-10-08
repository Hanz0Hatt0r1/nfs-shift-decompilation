from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00766510_same_pass_session_handoff.json"
INPUT_HEADER = ROOT / "native_runtime/include/shift_fun_00766510_external_pass_input.hpp"
SESSION_HEADER = ROOT / "native_runtime/include/shift_native_vehicle_provider_session.hpp"
SESSION_SOURCE = ROOT / "native_runtime/src/native_vehicle_provider_session.cpp"
PHASE744 = ROOT / "native_runtime/cmake/phase744.cmake"
PHASE745 = ROOT / "native_runtime/cmake/phase745.cmake"


def test_phase745_evidence_freezes_same_pass_selected_handoff() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun00766510SamePassSessionHandoff/1"
    assert payload["ready"] is True
    assert payload["anchor_order"] == [
        "FUN_00765c40",
        "FUN_00758b50",
        "FUN_00766510",
        "FUN_00769ef0",
    ]
    join = payload["session_join"]
    assert join["provider_input"] == "SHIFT.Fun00766510ExternalPassInput/1"
    assert join["typed_input_built_before_wheel_update"] is True
    assert join["typed_input_consumed_only_at_contact_response_anchor"] is True
    assert join["contact_response_receives_same_pass_handoff"] is True
    assert join["selected_missing_query_output_fail_closed"] is True
    assert join["selected_missing_application_point_fail_closed"] is True
    assert join["generic_input_cannot_claim_selected_bmw_ownership"] is True


def test_phase745_active_session_threads_query_output_and_application_point() -> None:
    input_header = INPUT_HEADER.read_text(encoding="utf-8")
    session_header = SESSION_HEADER.read_text(encoding="utf-8")
    session_source = SESSION_SOURCE.read_text(encoding="utf-8")

    assert "SHIFT.Fun00766510ExternalPassInput/1" in input_header
    assert "query_scalar_handoff" in input_header
    assert "primary_application_point" in input_header
    assert "generic FUN_00766510 compatibility input cannot claim selected BMW ownership" in input_header
    assert "build_fun_00766510_selected_bmw_external_pass_input" in input_header

    assert "NativeVehicleContactResponseProvider" in session_header
    assert "const physics::Fun00766510ExternalPassInput& input" in session_header

    assert "Fun00766510PassInputState" in session_source
    assert "result.query_output.has_value()" in session_source
    assert "build_fun_00766510_selected_bmw_external_pass_input" in session_source
    assert "fun_00766510_selected_bmw_primary_application_point" in session_source
    assert "validate_fun_00766510_external_pass_input" in session_source
    assert "providers_.contact_response(" in session_source

    build_pos = session_source.index("build_fun_00766510_selected_bmw_external_pass_input")
    wheel_pos = session_source.index("callbacks.wheel_update")
    consume_pos = session_source.index("providers_.contact_response(")
    assert build_pos < wheel_pos < consume_pos


def test_phase745_keeps_provider_count_until_complete_contact_response_removal() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    scope = payload["scope"]
    assert scope["external_provider_count_before"] == 7
    assert scope["external_provider_count_after"] == 7
    assert scope["provider_count_reduced"] is False
    assert scope["contact_response_provider_removed"] is False
    assert scope["complete_FUN_00766510_internalized"] is False


def test_phase745_cmake_chains_after_phase744() -> None:
    phase744 = PHASE744.read_text(encoding="utf-8")
    phase745 = PHASE745.read_text(encoding="utf-8")
    assert "include(${CMAKE_CURRENT_LIST_DIR}/phase745.cmake)" in phase744
    assert "shift_runtime_fun_00766510_same_pass_handoff_check" in phase745
