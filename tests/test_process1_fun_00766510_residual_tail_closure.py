import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/fun_00766510_residual_tail_closure.json"
DOC = ROOT / "docs/PROCESS_1_FUN_00766510_RESIDUAL_TAIL_CLOSURE.md"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_identity_and_authority():
    p = _payload()
    assert p["format"] == "SHIFT.Fun00766510ResidualTailClosure/1"
    assert p["ready"] is True
    assert p["authority"]["platform"] == "PC retail 1.02"
    assert p["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"


def test_auxiliary_pair_schedule_is_exact():
    pair = _payload()["auxiliary_pair_scheduling"]
    assert pair["first_call"]["callsite"] == "0x00766da5"
    assert pair["first_call"]["record"] == "HDVehicle+0x37d8"
    assert pair["second_call"]["callsite"] == "0x00766dba"
    assert pair["second_call"]["record"] == "HDVehicle+0x3858"
    assert pair["first_call"]["reference_vector"] == pair["second_call"]["reference_vector"] == "[EBP-0xc8]"
    assert pair["ordering"]["exact_pair_order"] == ["0x37d8", "0x3858"]
    assert pair["machine_span"]["raw_byte_sha256"] == "95b9571b1c69af9f17243de4f62ba4c104aa050ac92c23c7283f49f867e54079"


def test_auxiliary_callee_adds_caller_accumulator():
    app = _payload()["auxiliary_pair_scheduling"]["callee_accumulator_application"]
    assert app["cross_callsite"] == "0x007590df"
    assert app["caller_accumulator_offsets"] == ["0x40a0", "0x40a8", "0x40b0"]
    assert app["machine_span"]["raw_byte_sha256"] == "e969ce933012f6b768d549edab69bc38dc53266e34a53745107c4af0dd60ceb9"


def test_final_vector_add_reaches_both_accumulators():
    final = _payload()["final_transformed_vector_add"]
    assert final["transform_callsite"] == "0x00767395"
    assert final["same_three_lanes_added_to_both"] is True
    assert final["body_accumulator_offsets"] == ["BODY0+0x48", "BODY0+0x50", "BODY0+0x58"]
    assert final["caller_accumulator_offsets"] == ["HDVehicle+0x40a0", "HDVehicle+0x40a8", "HDVehicle+0x40b0"]
    assert final["machine_span"]["raw_byte_sha256"] == "ab3efc846adb66a0d6ca8dfc37f64910b59e70023cfeb89b7d5f4c24146f2a6c"


def test_tail_is_guarded_and_has_bounded_direct_state_surface():
    tail = _payload()["conditional_tail"]
    assert tail["guard_branch"] == "0x00767400 je 0x007675dd"
    assert tail["zero_skips_tail"] is True
    assert len(tail["direct_hdvehicle_writes"]) == 7
    assert tail["additional_direct_caller_accumulator_writes_after_final_add"] is False
    assert tail["additional_direct_body_0x48_0x50_0x58_writes_after_final_add"] is False
    assert tail["machine_span"]["raw_byte_sha256"] == "b70f46b31f4890174e5259b9016c937a281960e7f329cf67c3ebf0949e5fa3b8"


def test_fail_closed_gate_moves_only_p1_1c():
    gate = _payload()["adjudication"]
    assert gate["p1_1c_complete"] is True
    assert gate["p1_1a_complete"] is False
    assert gate["p1_1_complete"] is False
    assert gate["contact_response_provider_removal_authorized"] is False
    assert gate["external_provider_count"] == 7
    assert "P1.1a" in DOC.read_text(encoding="utf-8")
