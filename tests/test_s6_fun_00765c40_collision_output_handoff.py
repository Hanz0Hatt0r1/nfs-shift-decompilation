from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00765c40_collision_output_handoff.json"
RESULT_HEADER = ROOT / "native_runtime/include/shift_fun_00765c40_external_pass_result.hpp"
HANDOFF_HEADER = ROOT / "native_runtime/include/shift_fun_00766510_query_scalar_handoff.hpp"
NATIVE_TEST = ROOT / "native_runtime/tests/fun_00765c40_collision_output_handoff_check.cpp"
PHASE743 = ROOT / "native_runtime/cmake/phase743.cmake"
PHASE744 = ROOT / "native_runtime/cmake/phase744.cmake"


def test_phase744_evidence_types_selected_collision_output_without_closing_provider() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Fun00765c40CollisionOutputHandoff/1"
    assert payload["ready"] is True
    assert payload["platform_authority"] == "PC retail primary"
    assert payload["source"]["retail_executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    assert payload["source"]["decompiler_sha256"] == (
        "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
    )
    assert payload["contracts"]["external_result"] == "SHIFT.Fun00765c40ExternalPassResult/4"
    assert payload["contracts"]["primary_response_application"] == (
        "SHIFT.Fun00766510PrimaryResponseApplication/1"
    )
    assert payload["contracts"]["selected_application_point"] == (
        "SHIFT.Fun00766510SelectedBMWApplicationPoint/1"
    )
    selected = payload["selected_bmw_result_rule"]
    assert selected["collision_output_required"] is True
    assert selected["query_record_must_match_input"] is True
    assert selected["returned_cache_handle_must_equal_query_output_returned_handle"] is True
    assert selected["generic_historical_fixture_output_optional"] is True
    scope = payload["scope"]
    assert scope["external_provider_count_before"] == 7
    assert scope["external_provider_count_after"] == 7
    assert scope["provider_count_reduced"] is False
    assert scope["collision_provider_internalized"] is False
    assert scope["FUN_00766510_contact_response_internalized"] is False
    assert payload["next_blocker"]["phase"] == 745


def test_phase744_active_result_requires_output_only_on_selected_bmw_domain() -> None:
    header = RESULT_HEADER.read_text(encoding="utf-8")
    assert "SHIFT.Fun00765c40ExternalPassResult/4" in header
    assert "SHIFT.Fun00765c40ExternalPassInput/2" in header
    assert "std::optional<CollisionQueryOutput> query_output" in header
    assert "input.world_position.has_value() && !result.query_output.has_value()" in header
    assert "validate_fun_00765c40_collision_output_handoff" in header
    assert "result.returned_cache_handle != result.query_output->returned_handle" in header


def test_phase744_query_scalar_helper_is_native_but_not_session_wired() -> None:
    header = HANDOFF_HEADER.read_text(encoding="utf-8")
    assert "SHIFT.Fun00766510QueryScalarHandoff/1" in header
    assert "CollisionQueryOutput query_output" in header
    assert "project_fun_00765c40_query_input_scalar" in header
    assert "clamp_fun_00766510_query_scalar" in header
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["native_scalar_handoff"]["implemented"] is True
    assert payload["native_scalar_handoff"]["session_wired"] is False


def test_phase744_native_regression_covers_hit_miss_cache_and_clamps() -> None:
    source = NATIVE_TEST.read_text(encoding="utf-8")
    for witness in (
        "reused_hit",
        "high_hit",
        "negative_hit",
        "miss_handoff",
        "hidden_output_rejected",
        "wrong_record_rejected",
    ):
        assert witness in source
    assert "SHIFT.Fun00765c40CollisionOutputHandoff/1" in source


def test_phase744_cmake_chains_after_canonical_phase743() -> None:
    phase743 = PHASE743.read_text(encoding="utf-8")
    phase744 = PHASE744.read_text(encoding="utf-8")
    assert "shift_runtime_fun_00766510_selected_bmw_application_point_check" in phase743
    assert "include(${CMAKE_CURRENT_LIST_DIR}/phase744.cmake)" in phase743
    assert "shift_runtime_fun_00765c40_collision_output_handoff_check" in phase744
