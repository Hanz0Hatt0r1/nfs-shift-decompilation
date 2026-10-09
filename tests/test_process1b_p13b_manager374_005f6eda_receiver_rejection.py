import json
from pathlib import Path

EVIDENCE = Path("evidence/hdvehicle_64e8_manager_374_p13b_005f6eda_receiver_rejection.json")


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_exact_site_and_unique_direct_caller_are_pinned():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374P13B005f6edaReceiverRejection/1"
    assert data["owner_shard"] == "P1.3B"
    assert data["target_site"]["address"] == "0x005f6eda"
    assert data["target_site"]["function"] == "FUN_005f6850"
    assert data["direct_call_surface"]["direct_caller_count"] == 1
    assert data["direct_call_surface"]["caller"] == "FUN_005f7df0"
    assert data["direct_call_surface"]["callsite"] == "0x005f7e9b"


def test_receiver_class_is_not_participants_manager():
    data = load_evidence()
    rc = data["receiver_class"]
    assert rc["allocation_size"] == "0x1fe0"
    assert rc["constructor"] == "FUN_005f78e0"
    assert rc["constructor_vptr_store"] == "receiver[0] = 0x00ae2a60"
    assert data["participants_manager_identity"]["root_vptr"] == "0x00ab9190"
    assert data["participants_manager_identity"]["subobject_vptr"] == "0x00ab916c"
    assert data["identity_adjudication"]["receiver_is_participants_manager"] is False
    assert data["identity_adjudication"]["numeric_offset_equality_used_as_identity"] is False


def test_p13b_computed_sites_close_but_aggregate_gates_stay_closed():
    a = load_evidence()["adjudication"]
    assert a["p13b_site_0x005f6eda_complete"] is True
    assert a["p13b_site_0x0070f62d_complete"] is True
    assert a["p13b_computed_forwarding_sites_complete"] is True
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["last_literal_0x004b86cf_rejected"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
