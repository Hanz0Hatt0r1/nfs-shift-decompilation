from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTIER = ROOT / "evidence/fun_007b0710_collision_provider_frontier.json"
PHASE370 = ROOT / "evidence/collision_query_runtime_phase370.json"
RUNTIME = ROOT / "src/physics/collision_query_runtime.py"
WORLD = ROOT / "evidence/fun_00765c40_selected_bmw_world_position_join.json"
CACHE = ROOT / "evidence/fun_00765c40_query_cache_lifetime.json"
FALLBACK = ROOT / "evidence/fun_00765c40_selected_bmw_query_fallback.json"
HANDOFF = ROOT / "evidence/fun_00765c40_collision_output_handoff.json"
DOC = ROOT / "docs/PROCESS_1_FUN_007B0710_COLLISION_PROVIDER_FRONTIER.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_frontier_reuses_the_existing_pc_query_boundary() -> None:
    frontier = _load(FRONTIER)
    phase370 = _load(PHASE370)

    assert frontier["format"] == "SHIFT.Fun007b0710CollisionProviderFrontier/1"
    assert frontier["ready"] is True
    assert frontier["authority"]["semantic_platform"] == "PC retail primary"
    assert frontier["authority"]["new_machine_or_source_claims_in_this_join"] is False
    assert frontier["authority"]["xbox_recomp_may_replace_pc_proof"] is False

    surface = frontier["known_call_surface"]
    assert surface["caller"] == "FUN_00765c40"
    assert surface["caller_source_line"] == phase370["source"]["wheel_caller_line"] == 759173
    assert surface["query_function"] == "FUN_007b0710"
    assert surface["query_function_source_line"] == phase370["source"]["query_function_line"] == 811231
    assert surface["known_lower_fallback_query"] == phase370["source"]["fallback_query_function"] == "FUN_0074f560"


def test_closed_abi_matches_phase370_layout() -> None:
    frontier = _load(FRONTIER)
    phase370 = _load(PHASE370)
    abi = frontier["closed_abi"]

    assert abi["query_record_double_slots"] == phase370["query_record"]["double_slots"] == 7
    assert abi["query_position_offset"] == phase370["query_record"]["position_offset"] == "0x00"
    assert abi["y_tolerance_offset"] == phase370["query_record"]["y_tolerance_offset"] == "0x18"
    assert abi["max_aux_offset"] == phase370["query_record"]["max_aux_offset"] == "0x20"
    assert abi["output_height_offset"] == phase370["query_record"]["output_height_offset"] == "0x28"
    assert abi["cache_handle_offset"] == phase370["query_record"]["cache_handle_offset"] == "0x30"
    assert abi["cache_record_size"] == phase370["cache_record"]["allocation_stride"] == "0x58"
    assert abi["provider_execution_implemented"] is False


def test_selected_session_inputs_and_handoff_are_already_positive() -> None:
    frontier = _load(FRONTIER)
    selected = frontier["closed_selected_session_inputs"]

    expected = (
        (WORLD, selected["world_position"]),
        (CACHE, selected["persistent_cache_lifetime"]),
        (FALLBACK, selected["miss_fallback"]),
        (HANDOFF, selected["collision_output_handoff"]),
    )
    for path, fmt in expected:
        payload = _load(path)
        assert payload["format"] == fmt
        assert payload["ready"] is True


def test_runtime_module_pins_the_same_named_lower_surface() -> None:
    text = RUNTIME.read_text(encoding="utf-8")
    for token in (
        'FUNCTION = "FUN_007b0710"',
        'CALLER = "FUN_00765c40"',
        'FALLBACK_QUERY = "FUN_0074f560"',
        "SOURCE_LINE = 811231",
        "CALLER_SOURCE_LINE = 759173",
        "CACHE_RECORD_SIZE = 0x58",
    ):
        assert token in text


def test_provider_implementation_remains_fail_closed() -> None:
    frontier = _load(FRONTIER)
    adjudication = frontier["adjudication"]
    assert adjudication["FUN_007b0710_caller_visible_contract_closed"] is True
    assert adjudication["FUN_0074f560_known_as_lower_fallback_query_surface"] is True
    assert adjudication["exact_scene_query_implementation_below_cache_boundary_known"] is False
    assert adjudication["collision_provider_object_owned"] is False
    assert adjudication["physx_class_or_scene_object_name_proven"] is False
    assert adjudication["safe_to_replace_provider_with_guessed_track_query"] is False

    consumer = frontier["consumer"]
    assert consumer["may_use_typed_collision_output_now"] is True
    assert consumer["may_internalize_collision_provider_now"] is False
    assert consumer["may_remove_complete_FUN_00765c40_now"] is False

    text = DOC.read_text(encoding="utf-8")
    for token in (
        "FUN_0074f560",
        "scene-query",
        "provider object/pointer domain",
        "guessed track-raycast",
        "P1.2a complete: **false**",
        "NEXT_STEP",
    ):
        assert token in text
