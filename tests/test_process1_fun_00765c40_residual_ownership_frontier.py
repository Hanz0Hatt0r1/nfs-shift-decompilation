from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTIER = ROOT / "evidence/fun_00765c40_residual_ownership_frontier.json"
PROOF = ROOT / "evidence/fun_0074f560_collision_provider_machine_proof.json"
DOC = ROOT / "docs/PROCESS_1_FUN_00765C40_RESIDUAL_OWNERSHIP_FRONTIER.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_provider_boundary_is_closed_without_inventing_class_identity() -> None:
    frontier = _load(FRONTIER)
    proof = _load(PROOF)
    selected = frontier["selected_bmw_prequery_surface"]

    assert proof["format"] == "SHIFT.Fun0074f560CollisionProviderMachineProof/1"
    assert proof["ready"] is True
    assert selected["collision_provider_pointer_global"] == "0x00c133ac"
    assert selected["collision_provider_virtual_slot"] == "0x1c0"
    assert selected["collision_provider_boundary_typed"] is True
    assert selected["collision_provider_internalized"] is False
    assert proof["provider_dispatch"]["physx_class_name_proven"] is False


def test_only_p1_2b_remains() -> None:
    frontier = _load(FRONTIER)
    residual = frontier["remaining_process_1_proof"]
    assert [row["id"] for row in residual] == ["P1.2b"]
    assert "remaining source-visible FUN_00765c40 side effects" in residual[0]["target"]

    gate = frontier["completion_gate"]
    assert gate["p1_2a_complete"] is True
    assert gate["p1_2b_complete"] is False
    assert gate["p1_2_complete"] is False
    assert gate["fun_00765c40_provider_removal_authorized"] is False
    assert gate["external_provider_count"] == 7


def test_documentation_keeps_provider_external_and_p1_2b_fail_closed() -> None:
    text = DOC.read_text(encoding="utf-8")
    for token in (
        "P1.2a: **closed**",
        "P1.2b: **open**",
        "0x00c133ac",
        "+0x1c0",
        "explicit typed provider",
        "guessed track query",
        "provider removal authorized: **false**",
    ):
        assert token in text
