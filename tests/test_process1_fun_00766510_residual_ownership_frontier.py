from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTIER = ROOT / "evidence/fun_00766510_residual_ownership_frontier.json"
RESPONSE_CONFIG = ROOT / "evidence/fun_00766510_response_config_ownership.json"
EARLY = ROOT / "evidence/fun_00766510_early_response_branch_ownership.json"
OPTIONAL = ROOT / "evidence/fun_00766510_optional_response_branch_ownership.json"
LATER = ROOT / "evidence/fun_00766510_later_response_branch_ownership.json"
DIRECT_SURFACE = ROOT / "evidence/fun_00766510_direct_caller_accumulator_surface.json"
SHARED_REFERENCE = ROOT / "evidence/fun_00766510_shared_reference_vector.json"
REFERENCE_SOURCE = ROOT / "evidence/fun_00713630_reference_source.json"
DOC = ROOT / "docs/PROCESS_1_FUN_00766510_RESIDUAL_OWNERSHIP_FRONTIER.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_residual_frontier_joins_positive_process1_and_phase748_contracts() -> None:
    frontier = _load(FRONTIER)
    assert frontier["format"] == "SHIFT.Fun00766510ResidualOwnershipFrontier/1"
    assert frontier["ready"] is True
    assert frontier["authority"]["semantic_platform"] == "PC retail 1.02"
    assert frontier["authority"]["new_machine_or_source_claims_in_this_join"] is False
    assert frontier["authority"]["xbox_recomp_may_replace_pc_proof"] is False

    for path, fmt in (
        (RESPONSE_CONFIG, "SHIFT.Fun00766510ResponseConfigOwnership/1"),
        (EARLY, "SHIFT.Fun00766510EarlyResponseBranchOwnership/1"),
        (OPTIONAL, "SHIFT.Fun00766510OptionalResponseBranchOwnership/1"),
        (LATER, "SHIFT.Fun00766510LaterResponseBranchOwnership/1"),
        (DIRECT_SURFACE, "SHIFT.Fun00766510DirectCallerAccumulatorSurface/1"),
        (SHARED_REFERENCE, "SHIFT.Fun00766510SharedReferenceVector/1"),
        (REFERENCE_SOURCE, "SHIFT.Fun00713630ReferenceSource/1"),
    ):
        payload = _load(path)
        assert payload["format"] == fmt
        assert payload["ready"] is True

    direct = _load(DIRECT_SURFACE)
    assert direct["accumulator"]["direct_surface_complete"] is True


def test_frontier_names_only_the_live_p1_1_residuals() -> None:
    frontier = _load(FRONTIER)
    residual = frontier["remaining_process_1_proof"]
    assert [row["id"] for row in residual] == ["P1.1a", "P1.1c"]
    assert residual[0]["target"] == "FUN_00713630 dynamic writer inputs"
    assert "Phase 748" in residual[0]["reason"]
    assert residual[1]["target"] == "final cumulative response and residual state/diagnostic writes"
    assert "All four direct FUN_00753650" in residual[1]["reason"]

    inventory = frontier["retail_accumulator_inventory"]
    assert inventory["state"] == "HDVehicle+0x40a0/+0x40a8/+0x40b0"
    assert inventory["initial_zeroing_known"] is True
    assert len(inventory["known_contribution_classes"]) == 6
    assert inventory["direct_FUN_00753650_site_count"] == 4
    assert inventory["direct_FUN_00753650_sites_accounted"] == 4
    assert inventory["direct_FUN_00753650_surface_closed"] is True
    assert inventory["primary_direct_delta_native"] is True
    assert inventory["whole_accumulator_internalized"] is False


def test_provider_removal_remains_fail_closed() -> None:
    frontier = _load(FRONTIER)
    gate = frontier["completion_gate"]
    assert gate["p1_1_complete"] is False
    assert gate["contact_response_provider_removal_authorized"] is False
    assert gate["external_provider_count"] == 7
    assert gate["target_external_provider_count_after_process_2_consumption"] == 6
    assert len(gate["requirements"]) == 3

    text = DOC.read_text(encoding="utf-8")
    for token in (
        "P1.1a",
        "P1.1b",
        "P1.1c",
        "Phase 748",
        "four direct",
        "FUN_00758fc0",
        "final transformed cumulative-response vector",
        "+0x40a0/+0x40a8/+0x40b0",
        "contact_response",
        "NEXT_STEP",
    ):
        assert token in text
