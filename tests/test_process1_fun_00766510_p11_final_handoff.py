import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "fun_00766510_p11_final_handoff.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_p11a_and_p11c_are_both_positive_inputs():
    p = _payload()
    assert p["format"] == "SHIFT.Fun00766510P11FinalHandoff/1"
    a = p["p1_1a_runtime_input_closure"]
    c = p["p1_1c_tail_closure"]
    assert a["config_globals_complete"] is True
    assert a["sample_history_selected_participant_join_complete"] is True
    assert a["participant_plus_0x4b0_ownership_complete"] is True
    assert a["dynamic_lane_must_remain_runtime_state"] is True
    assert a["p1_1a_complete"] is True
    assert c["p1_1c_complete"] is True


def test_process2_handoff_preserves_dynamic_and_order_invariants():
    h = _payload()["retail_order_handoff"]
    assert h["consumer"] == "Process 2 P2.3"
    joined = "\n".join(h["required_invariants"])
    assert "runtime-mutable through FUN_007927c0" in joined
    assert "sample-history scheduling" in joined
    assert "accumulator contribution order" in joined
    assert "auxiliary-pair scheduling" in joined
    assert "Xbox/recomp" in joined


def test_provider_transition_authorizes_proof_not_immediate_count_change():
    t = _payload()["provider_transition"]
    assert t["boundary"] == "FUN_00766510/contact_response"
    assert t["proof_removal_authorized"] is True
    assert t["current_external_provider_count"] == 7
    assert t["count_changes_in_this_handoff"] is False
    assert t["target_external_provider_count_after_process2_consumption"] == 6
    assert "no longer required" in t["count_change_condition"]


def test_p11_closes_and_routes_to_process2_without_touching_other_lanes():
    p = _payload()
    a = p["adjudication"]
    assert a["p1_1a_complete"] is True
    assert a["p1_1c_complete"] is True
    assert a["p1_1_complete"] is True
    assert a["contact_response_provider_removal_authorized"] is True
    assert a["current_external_provider_count"] == 7
    assert a["process1_remaining_p1_1_blockers"] == 0
    assert a["next_owner"] == "Process 2 P2.3"
    limits = "\n".join(p["limits"])
    assert "Process 1B" in limits
    assert "Process 1D" in limits
