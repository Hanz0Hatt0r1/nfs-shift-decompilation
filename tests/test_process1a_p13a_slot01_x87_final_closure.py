import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "evidence" / "p1a_p13a_slot01_x87_final_closure.json"
FRONTIER = ROOT / "evidence" / "p1a_p13a_slot01_x87_zero_init_frontier.json"
REUSE = ROOT / "evidence" / "p1a_p13a_slot01_x87_reuse_tranche_closure.json"
STACK = ROOT / "evidence" / "p1a_p13a_slot01_x87_stack_output_tranche_closure.json"
P1D_FINAL = ROOT / "evidence" / "p1d_slot3_x87_remaining_closure.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_composition_consumes_exact_18_candidate_frontier():
    final = load(FINAL)
    frontier = load(FRONTIER)
    assert final["format"] == "SHIFT.P1A.P13ASlot01X87FinalClosure/1"
    assert frontier["format"] == "SHIFT.P1A.P13ASlot01X87ZeroInitFrontierEvidence/1"
    assert frontier["scan"]["candidate_function_count"] == 18
    assert final["composition"] == {
        "original_candidate_count": 18,
        "p1a_reuse_tranche_rejected": 9,
        "p1a_stack_output_tranche_rejected": 5,
        "shared_pointer_chain_rejected": 4,
        "total_rejected": 18,
        "remaining_count": 0,
    }


def test_cross_lane_pointer_chain_evidence_is_exact_and_not_reowned():
    final = load(FINAL)
    reuse = load(REUSE)
    stack = load(STACK)
    p1d = load(P1D_FINAL)
    assert reuse["format"] == "SHIFT.P1A.P13ASlot01X87ReuseTrancheClosure/1"
    assert stack["format"] == "SHIFT.P1A.P13ASlot01X87StackOutputTrancheClosure/1"
    assert p1d["format"] == "SHIFT.P1D.P13DSlot3X87RemainingClosure/1"
    assert final["authority"]["cross_lane_machine_evidence_consumed_not_reowned"] is True
    names = [row["function"] for row in final["shared_pointer_chain_adjudication"]]
    assert names == ["FUN_0075c0d0", "FUN_0075ada0", "FUN_007b8630", "FUN_007b7840"]
    p1d_names = {row["function"] for row in p1d["resolved"]}
    assert set(names) == p1d_names
    assert all(row["rejected"] is True for row in final["shared_pointer_chain_adjudication"])


def test_only_x87_surface_closes_and_global_gates_stay_fail_closed():
    adj = load(FINAL)["adjudication"]
    assert adj["shallow_x87_zero_init_depth4_surface_complete"] is True
    assert adj["shallow_x87_candidate_count"] == 18
    assert adj["shallow_x87_rejected_count"] == 18
    assert adj["shallow_x87_selected_hdvehicle_slot01_writer_found"] is False
    assert adj["x87_zero_init_semantics_complete"] is True
    assert adj["sse_vector_copy_init_complete"] is False
    assert adj["deeper_direct_aliases_ruled_out"] is False
    assert adj["indirect_callback_aliases_ruled_out"] is False
    assert adj["p13a_slot0_complete"] is False
    assert adj["p13a_slot1_complete"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
