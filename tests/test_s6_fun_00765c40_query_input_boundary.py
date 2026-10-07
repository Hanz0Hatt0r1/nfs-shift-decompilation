from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00765c40_query_input_boundary.json"
QUERY_HEADER = ROOT / "native_runtime/include/shift_fun_00765c40_query_input_boundary.hpp"
RESULT_HEADER = ROOT / "native_runtime/include/shift_fun_00765c40_external_pass_result.hpp"
SESSION_HEADER = ROOT / "native_runtime/include/shift_native_vehicle_provider_session.hpp"
SESSION_SOURCE = ROOT / "native_runtime/src/native_vehicle_provider_session.cpp"


def test_phase726_evidence_reuses_only_proven_query_boundary() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun00765c40QueryInputBoundary/1"
    assert payload["ready"] is True
    assert payload["platform_authority"] == "PC retail primary"
    assert payload["source"]["decompiler_sha256"] == (
        "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
    )
    assert payload["source"]["fun_00765c40_query_call_source_line"] == 759173
    assert payload["source"]["fun_007b0710_source_line"] == 811231

    inputs = payload["input"]
    assert "three finite f64" in inputs["world_position"]
    assert "+0x30" in inputs["cached_handle"]
    assert inputs["miss_fallback"] == "caller state +0x38e8"
    assert inputs["original_world_y_for_hit_scalar"] == "world_position[1]"

    native = payload["native_materialization"]
    assert native["query_y_bias"] == 0.15
    assert native["query_y_tolerance"] == 200.35
    assert native["query_max_aux"] == 9.999999933815813e36
    assert native["cache_flag"] == 1
    assert native["hit_scalar"] == "world_position[1] - returned contact height"
    assert native["miss_scalar"] == "miss_fallback"


def test_phase726_historical_scope_remains_immutable() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    scope = payload["scope"]
    assert scope["world_position_producer_internalized"] is False
    assert scope["world_position_coordinate_provenance_inferred"] is False
    assert scope["renderer_BODY0_VHF_transform_reused_as_query_transform"] is False
    assert scope["collision_provider_internalized"] is False
    assert scope["FUN_007b0710_query_record_native"] is True
    assert scope["query_response_join_native"] is True
    assert scope["external_provider_count_before"] == 7
    assert scope["external_provider_count_after"] == 7
    assert scope["provider_count_reduced"] is False
    assert scope["boundary_narrowed"] is True


def test_active_cpp_contract_feeds_owned_query_state_before_residual_pass() -> None:
    query_header = QUERY_HEADER.read_text(encoding="utf-8")
    result_header = RESULT_HEADER.read_text(encoding="utf-8")
    session_header = SESSION_HEADER.read_text(encoding="utf-8")
    session_source = SESSION_SOURCE.read_text(encoding="utf-8")

    assert "SHIFT.Fun00765c40QueryInputBoundary/1" in query_header
    assert "CollisionQueryVector3d world_position" in query_header
    assert "std::optional<std::uint64_t> cached_handle" in query_header
    assert "double miss_fallback" in query_header
    assert "build_fun_00765c40_collision_query_record" in query_header
    assert "input.world_position[1]" in query_header
    assert "input.miss_fallback" in query_header

    assert "SHIFT.Fun00765c40ExternalPassResult/3" in result_header
    assert "SHIFT.Fun00765c40ExternalPassInput/1" in result_header
    assert "Fun00765c40QueryInputBoundary query_input" in result_header
    assert "returned_cache_handle" in result_header

    assert "kNativeVehiclePhysicsPassCount = 2u" in session_header
    assert "fun_00765c40_query_input_capture_count" in session_header
    assert "fun_00765c40_cache_commit_count" in session_header
    assert "fun_00765c40_query_inputs" in session_header
    assert "fun_00765c40_returned_cache_handles" in session_header
    assert "fun_00765c40_query_cache_handle_" in session_header

    request = session_source.index("external_input.cached_handle =")
    provider_call = session_source.index("providers_.fun_00765c40(pass_index, external_input)")
    validation = session_source.index("validate_fun_00765c40_external_pass_result")
    snapshot = session_source.index("query_inputs[pass_index] = result.query_input")
    cache_commit = session_source.index("fun_00765c40_query_cache_handle_ =")
    load_terms = session_source.index("load_state->terms = result.load_terms")
    assert request < provider_call < validation < snapshot < cache_commit < load_terms


def test_active_session_does_not_consume_renderer_transform_as_query_producer() -> None:
    session_source = SESSION_SOURCE.read_text(encoding="utf-8")
    assert "vehicle_world_transform" not in session_source
    assert "VHF" not in session_source
    assert "BODY0/VHF" not in session_source
    assert "execute_fun_00765c40_selected_bmw_world_position" in session_source
