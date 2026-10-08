import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "hdvehicle_64e8_manager_2a0_fun00469ab0_frontier.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_candidate():
    p = _payload()
    assert p["format"] == "SHIFT.HDVehicle64e8Manager2a0Fun00469ab0Frontier/1"
    assert p["ready"] is True
    assert p["candidate"]["function"] == "FUN_00469ab0"
    assert p["candidate"]["candidate_subobject"] == "receiver+0x2a0"
    assert p["candidate"]["mutation_callsite"] == "0x00469b1d"


def test_machine_join_is_real_but_root_identity_is_fail_closed():
    p = _payload()
    assert p["machine_join"]["receiver_capture"] == "0x00469abc MOV ESI,ECX"
    assert p["machine_join"]["subobject_address"] == "0x00469b17 LEA ECX,[ESI+0x2a0]"
    assert p["machine_join"]["call"] == "0x00469b1d CALL 0x0057f620"
    assert p["machine_join"]["callee_mutates_receiver_state"] is True
    assert p["adjudication"]["fun00469ab0_mutates_receiver_plus_0x2a0"] is True
    assert p["adjudication"]["fun00469ab0_receiver_is_singleton_manager"] is False
    assert p["adjudication"]["manager_plus_0x2a0_join_complete"] is False


def test_easy_registration_surfaces_are_exhausted_without_overclaiming():
    p = _payload()
    x = p["whole_export_exclusions"]
    assert x["direct_inbound_calls_to_fun00469ab0"] == 0
    assert x["present_in_2533_vtable_candidates"] is False
    assert x["literal_little_endian_0x00469ab0_occurrences_in_retail_image"] == 0
    assert x["address_taken_registration_proven"] is False


def test_adjacent_function_does_not_supply_identity():
    p = _payload()
    a = p["adjacent_function_disambiguation"]
    assert a["function"] == "FUN_00469c00"
    assert a["vtable"] == "0x00ab6154"
    assert a["vtable_slot"] == 0
    assert "0x10 bytes" in a["constructor_like_allocation"]


def test_semantic_gates_remain_closed():
    p = _payload()
    a = p["adjudication"]
    assert a["manager_plus_0x374_join_complete"] is False
    assert a["exact_hdvehicle_64e8_non_sentinel_writer_proven"] is False
    assert a["retail_input_control_provenance_proven"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
