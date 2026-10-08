from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / "evidence/fun_007584f0_machine_side_effect_proof.json"
FRONTIER = ROOT / "evidence/fun_00765c40_direct_machine_write_surface.json"
OWNERSHIP = ROOT / "evidence/fun_00765c40_residual_ownership_frontier.json"
DOC = ROOT / "docs/PROCESS_1_FUN_00765C40_RESIDUAL_OWNERSHIP_FRONTIER.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_machine_span_and_caller_are_pinned() -> None:
    proof = _load(PROOF)
    assert proof["format"] == "SHIFT.Fun007584f0MachineSideEffectProof/1"
    assert proof["ready"] is True
    authority = proof["authority"]
    assert authority["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert authority["entry"] == "0x007584f0"
    assert authority["end_exclusive"] == "0x00758803"
    assert authority["machine_span_size"] == 787
    assert authority["machine_span_sha256"] == "252bade571ca266a620628da463c4cd3b3ca81333df0746d438cd95f77e2295f"
    assert authority["caller_site"] == "0x00765f2b"
    assert authority["receiver_at_call"] == "ecx = HDVehicle"


def test_persistent_object_write_surface_is_exact() -> None:
    proof = _load(PROOF)
    writes = proof["persistent_object_writes"]
    assert writes[0]["sites"] == ["0x00758731", "0x0075873b"]
    assert writes[0]["loop_indices"] == [0, 1]
    assert writes[0]["hdvehicle_offsets"] == ["+0x0d40", "+0x17c0"]
    assert writes[0]["width"] == "qword"
    assert writes[1]["site"] == "0x007587f4"
    assert writes[1]["hdvehicle_offset"] == "+0x3420"
    assert writes[1]["width"] == "float"
    assert writes[1]["producer"] == "return value of 0x00783a30 scalar interpolation helper"


def test_all_nested_object_side_effects_are_classified() -> None:
    proof = _load(PROOF)
    rows = {row["callee"]: row for row in proof["nested_calls"]}
    assert set(rows) == {
        "0x007aefb0", "0x007535f0", "0x00753590", "0x00753650",
        "0x00900b10", "0x00900c40", "0x00783a30",
    }
    assert all(row["object_state_mutation"] is False for row in rows.values())
    assert rows["0x00900b10"]["process_fp_environment_may_be_touched_internally"] is True
    assert rows["0x00900c40"]["process_fp_environment_may_be_touched_internally"] is True


def test_p1_2_is_complete_but_provider_count_does_not_move_in_proof_pr() -> None:
    proof = _load(PROOF)
    gate = proof["adjudication"]
    assert gate["persistent_object_write_surface_complete"] is True
    assert gate["nested_object_side_effect_surface_complete"] is True
    assert gate["remaining_unclassified_callees"] == []
    assert gate["p1_2b_complete"] is True
    assert gate["p1_2_complete"] is True
    assert gate["process_2_p2_4_handoff_ready"] is True
    assert gate["fun_00765c40_provider_removal_authorized_for_process_2"] is True
    assert gate["collision_scene_query_must_remain_explicit_typed_external_boundary"] is True
    assert gate["external_provider_count_before_process_2_consumption"] == 7

    frontier = _load(FRONTIER)
    assert frontier["callee_mediated_side_effects_complete"] is True
    assert frontier["representative_unresolved_callees"] == []
    assert frontier["gate"]["p1_2b_complete"] is True
    assert frontier["gate"]["fun_00765c40_provider_removal_authorized"] is True

    ownership = _load(OWNERSHIP)
    assert ownership["remaining_process_1_proof"] == []
    assert ownership["completion_gate"]["p1_2_complete"] is True
    assert ownership["completion_gate"]["p1_2a_complete"] is True
    assert ownership["completion_gate"]["p1_2b_complete"] is True
    assert ownership["completion_gate"]["process_2_p2_4_handoff_ready"] is True
    assert ownership["completion_gate"]["external_provider_count_before_process_2_consumption"] == 7
    assert ownership["next_owner"] == "Process 2 P2.4"


def test_documentation_preserves_lower_external_provider_boundary() -> None:
    text = DOC.read_text(encoding="utf-8")
    for token in (
        "P1.2 complete: **true**",
        "P1.2b: **closed**",
        "+0xd40",
        "+0x17c0",
        "+0x3420",
        "0x00c133ac",
        "+0x1c0",
        "external-provider count before Process 2 consumption: **7**",
        "Process 2 P2.4",
        "NEXT_STEP",
    ):
        assert token in text
