from __future__ import annotations

import json
from pathlib import Path

from src.physics import native_vehicle_external_provider_frontier_current as frontier


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00765c40_collision_output_handoff.json"
RESULT_HEADER = ROOT / "native_runtime/include/shift_fun_00765c40_external_pass_result.hpp"
HANDOFF_HEADER = ROOT / "native_runtime/include/shift_fun_00766510_query_scalar_handoff.hpp"
NATIVE_TEST = ROOT / "native_runtime/tests/fun_00765c40_collision_output_handoff_check.cpp"


def test_phase742_evidence_types_selected_collision_output_without_closing_provider() -> None:
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
    assert payload["source"]["caller_query_source_line"] == 759173

    contracts = payload["contracts"]
    assert contracts["collision_query"] == "SHIFT.NativeCollisionQueryContract/1"
    assert contracts["query_input"] == "SHIFT.Fun00765c40QueryInputBoundary/1"
    assert contracts["external_input"] == "SHIFT.Fun00765c40ExternalPassInput/2"
    assert contracts["external_result"] == "SHIFT.Fun00765c40ExternalPassResult/4"
    assert contracts["query_scalar_handoff"] == "SHIFT.Fun00766510QueryScalarHandoff/1"

    selected = payload["selected_bmw_result_rule"]
    assert selected["collision_output_required"] is True
    assert selected["query_record_must_match_input"] is True
    assert selected["returned_cache_handle_must_equal_query_output_returned_handle"] is True
    assert selected["generic_historical_fixture_output_optional"] is True

    scope = payload["scope"]
    assert scope["external_provider_count_before"] == 7
    assert scope["external_provider_count_after"] == 7
    assert scope["provider_count_reduced"] is False
    assert scope["boundary_narrowed"] is True
    assert scope["collision_provider_internalized"] is False
    assert scope["complete_FUN_00765c40_internalized"] is False
    assert scope["FUN_00766510_contact_response_internalized"] is False
    assert scope["session_query_scalar_handoff_wired"] is False


def test_phase742_active_result_requires_output_only_on_selected_bmw_domain() -> None:
    header = RESULT_HEADER.read_text(encoding="utf-8")
    assert "SHIFT.Fun00765c40ExternalPassResult/4" in header
    assert "SHIFT.Fun00765c40ExternalPassInput/2" in header
    assert "std::optional<CollisionQueryOutput> query_output" in header
    assert "input.world_position.has_value() && !result.query_output.has_value()" in header
    assert "selected BMW provider hid FUN_007b0710 collision output" in header
    assert "validate_fun_00765c40_collision_output_handoff" in header
    assert "output.query_record.query_position != expected.query_position" in header
    assert "result.returned_cache_handle != result.query_output->returned_handle" in header


def test_phase742_query_scalar_helper_is_native_but_not_session_wired() -> None:
    header = HANDOFF_HEADER.read_text(encoding="utf-8")
    assert "SHIFT.Fun00766510QueryScalarHandoff/1" in header
    assert "CollisionQueryOutput query_output" in header
    assert "double query_scalar" in header
    assert "double query_limit" in header
    assert "double clamped_query_scalar" in header
    assert "project_fun_00765c40_query_input_scalar" in header
    assert "clamp_fun_00766510_query_scalar" in header

    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    handoff = payload["native_scalar_handoff"]
    assert handoff["implemented"] is True
    assert handoff["session_wired"] is False
    assert handoff["query_scalar_offset"] == "HDVehicle+0x38e0"
    assert handoff["query_limit_offset"] == "HDVehicle+0x38e8"


def test_phase742_native_regression_covers_hit_miss_cache_and_clamps() -> None:
    source = NATIVE_TEST.read_text(encoding="utf-8")
    assert "reused_hit" in source
    assert "high_hit" in source
    assert "negative_hit" in source
    assert "miss_handoff" in source
    assert "hidden_output_rejected" in source
    assert "wrong_record_rejected" in source
    assert "SHIFT.Fun00765c40CollisionOutputHandoff/1" in source
    assert "contact_response_provider_internalized\\\":false" in source


def test_phase742_current_frontier_is_refreshed_but_remains_seven() -> None:
    report = frontier.build_current_frontier()
    assert report["refresh_after_phase"] == 742
    assert report["external_provider_count"] == 7
    provider = next(row for row in report["providers"] if row["id"] == "fun_00765c40_complete_anchor")
    assert "CollisionQueryOutput" in provider["current_api"]
    assert frontier.FUN_00765C40_EXTERNAL_PASS_RESULT_FORMAT == (
        "SHIFT.Fun00765c40ExternalPassResult/4"
    )
    assert frontier.FUN_00765C40_EXTERNAL_PASS_INPUT_FORMAT == (
        "SHIFT.Fun00765c40ExternalPassInput/2"
    )
    assert frontier.FUN_00765C40_COLLISION_OUTPUT_HANDOFF_FORMAT == (
        "SHIFT.Fun00765c40CollisionOutputHandoff/1"
    )
    assert frontier.FUN_00766510_QUERY_SCALAR_HANDOFF_FORMAT == (
        "SHIFT.Fun00766510QueryScalarHandoff/1"
    )
    audit = report["provider_audit"]
    assert audit["fun_00765c40_selected_collision_output_required"] is True
    assert audit["fun_00765c40_collision_output_typed"] is True
    assert audit["fun_00765c40_collision_provider_internalized"] is False
    assert audit["fun_00766510_query_scalar_handoff_native"] is True
    assert audit["fun_00766510_query_scalar_handoff_session_wired"] is False
