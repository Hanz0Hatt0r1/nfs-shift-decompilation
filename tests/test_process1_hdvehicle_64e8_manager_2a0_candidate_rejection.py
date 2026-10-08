import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "hdvehicle_64e8_manager_2a0_candidate_rejection.json"
COORD = ROOT / "coordination" / "decomp_blockers.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_authority():
    p = _payload()
    assert p["format"] == "SHIFT.HDVehicle64e8Manager2a0CandidateRejection/1"
    assert p["ready"] is True
    assert p["authority"]["platform"] == "PC retail 1.02"
    assert p["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"


def test_candidate_receiver_is_not_manager_receiver():
    p = _payload()
    r = p["receiver_provenance"]
    assert r["candidate_receiver_address"] == "0x00bbdbe0"
    assert r["manager_receiver_address"] == "0x00bc9fc0"
    assert r["same_receiver"] is False
    assert r["same_collection"] is False


def test_machine_chain_keeps_exact_value_transfer():
    p = _payload()
    getter = p["machine_chain"]["getter_thunk"]
    body = p["machine_chain"]["candidate_body"]
    assert "0x0043b97b mov EAX,0x00bbdbe0" in getter
    assert "0x00469abc mov ESI,ECX" in body
    assert "0x00469b17 lea ECX,[ESI+0x2a0]" in body
    assert "0x00469b1d call FUN_0057f620" in body


def test_fail_closed_gates_are_preserved():
    a = _payload()["adjudication"]
    assert a["candidate_rejected_as_manager_2a0_mutator"] is True
    assert a["matching_plus_0x2a0_offset_is_object_identity"] is False
    assert a["manager_2a0_insertion_identity_complete"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["exact_hdvehicle_64e8_non_sentinel_writer_proven"] is False
    assert a["retail_input_control_provenance_proven"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7


def test_coordination_preserves_rejected_edge_while_frontier_advances():
    graph = json.loads(COORD.read_text(encoding="utf-8"))
    p13 = next(row for row in graph["workstreams"] if row["id"] == "P1.3")
    node = next(row for row in p13["children"] if row["id"] == "P1.3.manager2a0")
    assert node["status"] != "mutation-edge-found"
    assert "0x00469b1d" in node["rejected_candidate"]
    assert "0x00bbdbe0+0x2a0" in node["rejected_candidate"]
