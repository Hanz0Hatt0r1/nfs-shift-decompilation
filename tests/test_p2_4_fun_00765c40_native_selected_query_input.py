import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p2_4_fun_00765c40_native_selected_query_input.json"
HEADER = ROOT / "native_runtime/include/shift_fun_00765c40_external_pass_result.hpp"
DOC = ROOT / "docs/P2_4_FUN_00765C40_NATIVE_SELECTED_QUERY_INPUT.md"


def test_selected_query_input_is_native_owned_and_fail_closed() -> None:
    payload = json.loads(EVIDENCE.read_text())
    assert payload["format"] == "SHIFT.Fun00765c40NativeSelectedQueryInput/1"
    assert payload["ready"] is True
    contract = payload["native_contract"]
    assert contract["materializer"] == "Fun00765c40ExternalPassInput.selected_bmw_query_input"
    assert contract["query_input_world_position_provider_owned"] is False
    assert contract["query_input_cached_handle_provider_owned"] is False
    assert contract["query_input_miss_fallback_provider_owned"] is False
    assert contract["provider_result_must_match_native_query_input"] is True
    assert contract["generic_non_selected_fixture_compatibility_preserved"] is True
    scope = payload["scope"]
    assert scope["selected_query_input_native_owned"] is True
    assert scope["complete_FUN_00765c40_internalized"] is False
    assert scope["top_level_FUN_00765c40_provider_removed"] is False
    assert scope["external_provider_count_after"] == 7


def test_header_materializes_and_compares_complete_selected_query_input() -> None:
    text = HEADER.read_text()
    assert "selected_bmw_query_input() const" in text
    assert "query.world_position = *world_position" in text
    assert "query.cached_handle = cached_handle" in text
    assert "selected_bmw_m3_e36_fun_00765c40_query_fallback()" in text
    assert "const auto native_selected_query = input.selected_bmw_query_input();" in text
    assert "result.query_input.world_position != native_selected_query->world_position" in text
    assert "result.query_input.cached_handle != native_selected_query->cached_handle" in text
    assert "result.query_input.miss_fallback != native_selected_query->miss_fallback" in text


def test_docs_keep_provider_removal_fail_closed() -> None:
    doc = DOC.read_text()
    assert "lower collision query implementation" in doc
    assert "top-level provider remains present" in doc
    assert "external provider count remains 7" in doc
