from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00765c40_external_pass_result.json"
RESULT_HEADER = ROOT / "native_runtime/include/shift_fun_00765c40_external_pass_result.hpp"
QUERY_INPUT_HEADER = ROOT / "native_runtime/include/shift_fun_00765c40_query_input_boundary.hpp"
SESSION_HEADER = ROOT / "native_runtime/include/shift_native_vehicle_provider_session.hpp"
SESSION_SOURCE = ROOT / "native_runtime/src/native_vehicle_provider_session.cpp"


def test_phase725_evidence_narrows_only_the_session_boundary() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun00765c40ExternalPassResult/1"
    assert payload["ready"] is True
    assert payload["upstream_load_term_contract"] == "SHIFT.Fun00765c40LoadTerms/1"
    api = payload["session_api"]
    assert api["provider_type"] == "NativeVehicleFun00765c40Provider"
    assert api["bundle_field"] == "fun_00765c40"
    assert api["result_type"] == "Fun00765c40ExternalPassResult"
    assert api["result_field"] == "load_terms"
    assert api["legacy_lower_callback"].endswith(".contact_factor")
    assert api["legacy_lower_callback_renamed"] is False
    assert api["session_contact_factor_alias_removed"] is True


def test_phase725_historical_scope_remains_immutable() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    native = payload["already_native_subcomponents"]
    remaining = payload["remaining_external"]
    scope = payload["scope"]
    assert native["FUN_00758ad0_contact_factor"] is True
    assert native["FUN_007b0710_collision_query_record"] is True
    assert native["wheel_query_response_join"] is True
    assert remaining["complete_FUN_00765c40_pass"] is True
    assert remaining["collision_provider_behavior"] is True
    assert scope["external_provider_count_after"] == 7
    assert scope["complete_FUN_00765c40_internalized"] is False


def test_active_cpp_api_extends_historical_result_with_phase744_collision_output() -> None:
    result_header = RESULT_HEADER.read_text(encoding="utf-8")
    query_input_header = QUERY_INPUT_HEADER.read_text(encoding="utf-8")
    session_header = SESSION_HEADER.read_text(encoding="utf-8")
    session_source = SESSION_SOURCE.read_text(encoding="utf-8")

    assert "SHIFT.Fun00765c40ExternalPassResult/4" in result_header
    assert "SHIFT.Fun00765c40ExternalPassInput/2" in result_header
    assert "std::optional<CollisionQueryOutput> query_output" in result_header
    assert "validate_fun_00765c40_collision_output_handoff" in result_header
    assert "selected BMW provider hid FUN_007b0710 collision output" in result_header
    assert "returned cache handle disagrees with FUN_007b0710 output" in result_header

    assert "SHIFT.Fun00765c40QueryInputBoundary/1" in query_input_header
    assert "build_fun_00765c40_query_record" in query_input_header
    assert "project_fun_00765c40_query_input_scalar" in query_input_header

    assert "using NativeVehicleFun00765c40Provider" in session_header
    assert "const physics::Fun00765c40ExternalPassInput& input" in session_header
    request = session_source.index("external_input.cached_handle =")
    provider_call = session_source.index("providers_.fun_00765c40(pass_index, external_input)")
    validation = session_source.index("validate_fun_00765c40_external_pass_result")
    query_store = session_source.index("query_inputs[pass_index] = result.query_input")
    cache_commit = session_source.index("fun_00765c40_query_cache_handle_ =")
    load_store = session_source.index("load_state->terms = result.load_terms")
    assert request < provider_call < validation < query_store < cache_commit < load_store
