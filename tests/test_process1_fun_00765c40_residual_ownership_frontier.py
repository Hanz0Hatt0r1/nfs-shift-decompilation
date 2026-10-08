from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTIER = ROOT / "evidence/fun_00765c40_residual_ownership_frontier.json"
PROOF = ROOT / "evidence/fun_0074f560_collision_provider_machine_proof.json"
FINAL = ROOT / "evidence/fun_007584f0_machine_side_effect_proof.json"
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


def test_p1_2_is_complete_and_handoff_moves_to_process_2() -> None:
    frontier = _load(FRONTIER)
    final = _load(FINAL)
    assert final["format"] == "SHIFT.Fun007584f0MachineSideEffectProof/1"
    assert final["ready"] is True
    assert frontier["remaining_process_1_proof"] == []

    side = frontier["side_effect_surface"]
    assert side["direct_machine_writes_closed"] is True
    assert side["callee_mediated_object_side_effects_closed"] is True
    assert side["unclassified_callees"] == []
    assert side["last_closed_callee"] == "FUN_007584f0"
    assert side["last_callee_persistent_hdvehicle_writes"] == ["+0xd40", "+0x17c0", "+0x3420"]

    gate = frontier["completion_gate"]
    assert gate["p1_2a_complete"] is True
    assert gate["p1_2b_complete"] is True
    assert gate["p1_2_complete"] is True
    assert gate["fun_00765c40_provider_removal_authorized"] is True
    assert gate["process_2_p2_4_handoff_ready"] is True
    assert gate["external_provider_count_before_process_2_consumption"] == 7
    assert frontier["next_owner"] == "Process 2 P2.4"


def test_documentation_closes_p1_2_but_keeps_lower_provider_external() -> None:
    text = DOC.read_text(encoding="utf-8")
    for token in (
        "P1.2a: **closed**",
        "P1.2b: **closed**",
        "P1.2 complete: **true**",
        "0x00c133ac",
        "+0x1c0",
        "+0xd40",
        "+0x17c0",
        "+0x3420",
        "provider removal authorized for Process 2: **true**",
        "external-provider count before Process 2 consumption: **7**",
        "NEXT_STEP",
    ):
        assert token in text
