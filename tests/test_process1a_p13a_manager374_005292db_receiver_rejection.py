import json
from pathlib import Path

EVIDENCE = Path("evidence/hdvehicle_64e8_manager_374_p13a_005292db_receiver_rejection.json")


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_target_call_and_adapter_relation_are_exact():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374P13A005292dbReceiverRejection/1"
    assert data["target_site"]["address"] == "0x005292db"
    assert data["target_entry_surface"]["direct_caller_count"] == 1
    assert data["target_entry_surface"]["direct_caller"] == "0x005320c0 call 0x005292d0"
    assert data["target_entry_surface"]["absolute_function_pointer_occurrence_count_for_0x005292d0"] == 0
    assert data["adapter_to_receiver_chain"]["relation"] == "FUN_005292d0 this = adapter.owner + 0x218"


def test_outer_domain_is_bounded_and_rejects_participants_manager():
    data = load_evidence()
    outer = data["outer_object_domain"]
    assert outer["constructor_direct_callers"] == [
        "0x0052353d call 0x0051b570",
        "0x00523697 call 0x0051b570",
    ]
    assert outer["static_instance"]["outer_address"] == "0x00bdfae4"
    assert outer["static_instance"]["nested_receiver_address"] == "0x00bdfcfc"
    assert outer["dynamic_instances"]["allocation_size"] == "0x1b54"
    assert data["participants_manager_identity"]["root_address"] == "0x00bc9fc0"
    identity = data["identity_adjudication"]
    assert identity["receiver_is_participants_manager"] is False
    assert identity["site_can_write_participants_manager_plus_0x374"] is False
    assert identity["numeric_offset_equality_used_as_identity"] is False


def test_p13a_computed_frontier_closes_but_global_gates_stay_closed():
    a = load_evidence()["adjudication"]
    assert a["p13a_site_0x005292db_complete"] is True
    assert a["p13a_site_0x005f4ffa_complete"] is True
    assert a["p13a_computed_forwarding_sites_complete"] is True
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["last_literal_0x004b86cf_rejected"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
