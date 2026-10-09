import json
from pathlib import Path

EVIDENCE = Path("evidence/hdvehicle_64e8_manager_374_p13a_005f4ffa_receiver_rejection.json")


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_exact_site_and_bounded_entry_surface_are_pinned():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374P13A005f4ffaReceiverRejection/1"
    assert data["owner_shard"] == "P1.3A"
    assert data["target_site"]["address"] == "0x005f4ffa"
    assert data["target_site"]["receiver_capture"] == "0x005f4f6d mov esi,ecx"
    surface = data["whole_image_entry_surface"]
    assert surface["direct_callers_to_wrapper"] == [
        "0x005f79d7 call 0x005f4f50",
        "0x005f7b85 call 0x005f4f50",
    ]
    assert surface["direct_tail_jumps_to_wrapper"] == ["0x005f8aff jmp 0x005f4f50"]
    assert surface["absolute_function_pointer_occurrence_count_for_0x005f4f50"] == 0
    assert surface["absolute_function_pointer_occurrence_count_for_0x005f4f55"] == 0


def test_exact_receiver_class_rejects_participants_manager_identity():
    data = load_evidence()
    rc = data["receiver_class"]
    assert rc["allocation_size"] == "0x1fe0"
    assert rc["vptr"] == "0x00ae2a60"
    assert rc["constructor_vptr_store"] == "0x005f78fd mov [esi],0x00ae2a60"
    assert rc["destructor_vptr_store"] == "0x005f79cb mov [esi],0x00ae2a60"
    assert data["participants_manager_identity"]["root_vptr"] == "0x00ab9190"
    assert data["participants_manager_identity"]["subobject_vptr"] == "0x00ab916c"
    identity = data["identity_adjudication"]
    assert identity["receiver_is_participants_manager"] is False
    assert identity["site_can_write_participants_manager_plus_0x374"] is False
    assert identity["numeric_offset_equality_used_as_identity"] is False


def test_p13a_frontier_reduces_but_global_gates_stay_closed():
    a = load_evidence()["adjudication"]
    assert a["p13a_site_0x005f4ffa_complete"] is True
    assert a["p13a_site_0x005292db_complete"] is False
    assert a["p13a_computed_forwarding_sites_complete"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["last_literal_0x004b86cf_rejected"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
