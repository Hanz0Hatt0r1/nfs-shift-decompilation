from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTIER = ROOT / "evidence/fun_00766510_residual_ownership_frontier.json"
RESPONSE_CONFIG = ROOT / "evidence/fun_00766510_response_config_ownership.json"
EARLY = ROOT / "evidence/fun_00766510_early_response_branch_ownership.json"
OPTIONAL = ROOT / "evidence/fun_00766510_optional_response_branch_ownership.json"
SHARED_REFERENCE = ROOT / "evidence/fun_00766510_shared_reference_vector.json"
DOC = ROOT / "docs/PROCESS_1_FUN_00766510_RESIDUAL_OWNERSHIP_FRONTIER.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_residual_frontier_joins_positive_merged_process1_contracts() -> None:
    frontier = _load(FRONTIER)
    assert frontier["format"] == "SHIFT.Fun00766510ResidualOwnershipFrontier/1"
    assert frontier["ready"] is True
    assert frontier["authority"]["semantic_platform"] == "PC retail 1.02"
    assert frontier["authority"]["new_machine_or_source_claims_in_this_join"] is False
    assert frontier["authority"]["xbox_recomp_may_replace_pc_proof"] is False

    response = _load(RESPONSE_CONFIG)
    early = _load(EARLY)
    optional = _load(OPTIONAL)
    shared = _load(SHARED_REFERENCE)
    assert response["format"] == "SHIFT.Fun00766510ResponseConfigOwnership/1"
    assert response["ready"] is True
    assert early["format"] == "SHIFT.Fun00766510EarlyResponseBranchOwnership/1"
    assert early["ready"] is True
    assert optional["format"] == "SHIFT.Fun00766510OptionalResponseBranchOwnership/1"
    assert optional["ready"] is True
    assert shared["format"] == "SHIFT.Fun00766510SharedReferenceVector/1"
    assert shared["ready"] is True


def test_frontier_names_only_the_live_p1_1_residuals() -> None:
    frontier = _load(FRONTIER)
    residual = frontier["remaining_process_1_proof"]
    assert [row["id"] for row in residual] == ["P1.1a", "P1.1b", "P1.1c"]
    assert residual[0]["target"] == "FUN_00713630 dynamic writer inputs"
    assert residual[1]["target"] == "later +0x3a28/+0x3a40 direct response block"
    assert residual[2]["target"] == "final cumulative response and residual state/diagnostic writes"

    inventory = frontier["retail_accumulator_inventory"]
    assert inventory["state"] == "HDVehicle+0x40a0/+0x40a8/+0x40b0"
    assert inventory["initial_zeroing_known"] is True
    assert len(inventory["known_contribution_classes"]) == 6
    assert inventory["primary_direct_delta_native"] is True
    assert inventory["whole_accumulator_internalized"] is False


def test_provider_removal_remains_fail_closed() -> None:
    frontier = _load(FRONTIER)
    gate = frontier["completion_gate"]
    assert gate["p1_1_complete"] is False
    assert gate["contact_response_provider_removal_authorized"] is False
    assert gate["external_provider_count"] == 7
    assert gate["target_external_provider_count_after_process_2_consumption"] == 6
    assert len(gate["requirements"]) == 4

    text = DOC.read_text(encoding="utf-8")
    for token in (
        "P1.1a",
        "P1.1b",
        "P1.1c",
        "FUN_00713630",
        "+0x3a28/+0x3a40",
        "+0x40a0/+0x40a8/+0x40b0",
        "contact_response",
        "NEXT_STEP",
    ):
        assert token in text
