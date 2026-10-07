from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00765c40_query_cache_lifetime.json"
RESULT_HEADER = ROOT / "native_runtime/include/shift_fun_00765c40_external_pass_result.hpp"
SESSION_HEADER = ROOT / "native_runtime/include/shift_native_vehicle_provider_session.hpp"
SESSION_SOURCE = ROOT / "native_runtime/src/native_vehicle_provider_session.cpp"
PHASE739_CMAKE = ROOT / "native_runtime/cmake/phase739.cmake"
PHASE740_CMAKE = ROOT / "native_runtime/cmake/phase740.cmake"


def test_phase740_evidence_freezes_only_cache_lifetime() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun00765c40QueryCacheLifetime/1"
    assert payload["ready"] is True
    assert payload["platform_authority"] == "PC retail primary"
    assert payload["caller_state"]["offset"] == "HDVehicle+0x38dc"
    assert payload["caller_state"]["setup_seed"] == 0
    runtime = payload["runtime_join"]
    # Historical Phase740 contract remains immutable.
    assert runtime["external_input_format"] == "SHIFT.Fun00765c40ExternalPassInput/1"
    assert runtime["external_result_format"] == "SHIFT.Fun00765c40ExternalPassResult/3"
    assert runtime["provider_receives_native_cached_handle_before_execution"] is True
    assert runtime["session_commits_returned_handle_before_later_pass_anchors"] is True
    assert runtime["pass1_consumes_pass0_returned_handle"] is True
    assert runtime["later_explicit_step_consumes_previous_step_final_handle"] is True
    assert runtime["transactional_rollback"] is True

    scope = payload["scope"]
    assert scope["external_provider_count_before"] == 7
    assert scope["external_provider_count_after"] == 7
    assert scope["provider_count_reduced"] is False
    assert scope["collision_provider_internalized"] is False
    assert scope["returned_handle_semantics_named"] is False
    assert scope["miss_fallback_0x38e8_internalized"] is False


def test_phase740_cache_ownership_survives_phase742_result_extension() -> None:
    result_header = RESULT_HEADER.read_text(encoding="utf-8")
    session_header = SESSION_HEADER.read_text(encoding="utf-8")
    session_source = SESSION_SOURCE.read_text(encoding="utf-8")

    assert "SHIFT.Fun00765c40ExternalPassResult/4" in result_header
    assert "SHIFT.Fun00765c40ExternalPassInput/2" in result_header
    assert "struct Fun00765c40ExternalPassInput" in result_header
    assert "std::optional<std::uint64_t> cached_handle" in result_header
    assert "std::optional<std::uint64_t> returned_cache_handle" in result_header
    assert "std::optional<CollisionQueryOutput> query_output" in result_header
    assert "result.query_input.cached_handle != input.cached_handle" in result_header

    assert "const physics::Fun00765c40ExternalPassInput& input" in session_header
    assert "fun_00765c40_query_cache_handle_" in session_header
    assert "fun_00765c40_cache_commit_count" in session_header
    assert "fun_00765c40_returned_cache_handles" in session_header

    build_input = session_source.index("external_input.cached_handle = fun_00765c40_query_cache_handle_")
    provider_call = session_source.index("providers_.fun_00765c40(pass_index, external_input)")
    validate = session_source.index("validate_fun_00765c40_external_pass_result")
    commit = session_source.index("fun_00765c40_query_cache_handle_ =\n                        result.returned_cache_handle")
    wheel = session_source.index("callbacks.wheel_update =")
    assert build_input < provider_call < validate < commit < wheel


def test_phase740_cache_is_transactional_and_persistent() -> None:
    session_source = SESSION_SOURCE.read_text(encoding="utf-8")
    assert "const auto query_cache_before = fun_00765c40_query_cache_handle_;" in session_source
    assert session_source.count("fun_00765c40_query_cache_handle_ = query_cache_before;") >= 3
    assert "returned_cache_handles[pass_index] =" in session_source
    assert "result.fun_00765c40_returned_cache_handles = returned_cache_handles;" in session_source


def test_phase740_cmake_is_chained_after_phase739() -> None:
    phase739 = PHASE739_CMAKE.read_text(encoding="utf-8")
    phase740 = PHASE740_CMAKE.read_text(encoding="utf-8")
    assert "include(${CMAKE_CURRENT_LIST_DIR}/phase740.cmake)" in phase739
    assert "shift_runtime_fun_00765c40_query_cache_lifetime_check" in phase740
