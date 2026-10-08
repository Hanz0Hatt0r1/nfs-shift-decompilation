from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTIER = ROOT / "evidence/fun_00765c40_residual_ownership_frontier.json"
WORLD = ROOT / "evidence/fun_00765c40_selected_bmw_world_position_join.json"
CACHE = ROOT / "evidence/fun_00765c40_query_cache_lifetime.json"
FALLBACK = ROOT / "evidence/fun_00765c40_selected_bmw_query_fallback.json"
OUTPUT = ROOT / "evidence/fun_00765c40_collision_output_handoff.json"
LOADS = ROOT / "evidence/fun_00765c40_load_term_ownership.json"
DOC = ROOT / "docs/PROCESS_1_FUN_00765C40_RESIDUAL_OWNERSHIP_FRONTIER.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_frontier_joins_only_positive_existing_contracts() -> None:
    frontier = _load(FRONTIER)
    assert frontier["format"] == "SHIFT.Fun00765c40ResidualOwnershipFrontier/1"
    assert frontier["ready"] is True
    assert frontier["authority"]["semantic_platform"] == "PC retail primary"
    assert frontier["authority"]["new_machine_or_source_claims_in_this_join"] is False
    assert frontier["authority"]["xbox_recomp_may_replace_pc_proof"] is False

    expected = (
        (WORLD, "SHIFT.Fun00765c40SelectedBMWWorldPosition/1"),
        (CACHE, "SHIFT.Fun00765c40QueryCacheLifetime/1"),
        (FALLBACK, "SHIFT.Fun00765c40SelectedBMWQueryFallback/1"),
        (OUTPUT, "SHIFT.Fun00765c40CollisionOutputHandoff/1"),
        (LOADS, "SHIFT.Fun00765c40LoadTerms/1"),
    )
    for path, fmt in expected:
        payload = _load(path)
        assert payload["format"] == fmt
        assert payload["ready"] is True


def test_selected_prequery_surface_is_closed_but_provider_is_not() -> None:
    frontier = _load(FRONTIER)
    selected = frontier["selected_bmw_prequery_surface"]
    assert selected["world_position_native"] is True
    assert selected["cache_state_offset"] == "HDVehicle+0x38dc"
    assert selected["cache_lifetime_native"] is True
    assert selected["miss_fallback_offset"] == "HDVehicle+0x38e8"
    assert selected["miss_fallback_native"] is True
    assert selected["query_function"] == "FUN_007b0710"
    assert selected["query_record_typed"] is True
    assert selected["collision_output_typed"] is True
    assert selected["collision_provider_internalized"] is False


def test_four_load_terms_are_closed_and_must_not_be_reselected() -> None:
    frontier = _load(FRONTIER)
    loads = frontier["load_term_surface"]
    source = _load(LOADS)

    assert loads["format"] == source["format"] == "SHIFT.Fun00765c40LoadTerms/1"
    assert loads["wheel_array_base"] == source["wheel_layout"]["array_base"] == "HDVehicle+0x400"
    assert loads["wheel_count"] == source["wheel_layout"]["count"] == 4
    assert loads["wheel_stride"] == source["wheel_layout"]["stride"] == "0xa80"
    assert loads["per_wheel_field"] == source["wheel_layout"]["per_wheel_load_field"] == "+0x738 f64"
    assert loads["hdvehicle_offsets"] == source["wheel_layout"]["hdvehicle_offsets"] == [
        "0xb38",
        "0x15b8",
        "0x2038",
        "0x2ab8",
    ]
    assert loads["ownership_closed"] is True
    assert loads["must_not_be_reselected_as_P1_2_proof"] is True


def test_only_collision_lookup_and_residual_side_effects_remain() -> None:
    frontier = _load(FRONTIER)
    residual = frontier["remaining_process_1_proof"]
    assert [row["id"] for row in residual] == ["P1.2a", "P1.2b"]
    assert "collision/world lookup provider" in residual[0]["target"]
    assert "FUN_007b0710" in residual[0]["target"]
    assert "remaining source-visible FUN_00765c40 side effects" in residual[1]["target"]

    gate = frontier["completion_gate"]
    assert gate["p1_2_complete"] is False
    assert gate["complete_FUN_00765c40_internalized"] is False
    assert gate["fun_00765c40_provider_removal_authorized"] is False
    assert gate["external_provider_count"] == 7
    assert len(gate["requirements"]) == 3


def test_documentation_keeps_the_frontier_fail_closed() -> None:
    text = DOC.read_text(encoding="utf-8")
    for token in (
        "P1.2a",
        "P1.2b",
        "FUN_007b0710",
        "+0x38dc",
        "+0x38e8",
        "+0x738",
        "collision/world",
        "side effects",
        "provider removal authorized: **false**",
        "NEXT_STEP",
    ):
        assert token in text
