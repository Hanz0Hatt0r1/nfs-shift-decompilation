import json
from pathlib import Path

EVIDENCE = Path("evidence/hdvehicle_64e8_manager_374_b04524_vptr_rejections.json")


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_receiver_vptr_and_sites_are_pinned():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374B04524VptrRejections/1"
    assert data["receiver_class"]["vptr"] == "0x00b04524"
    assert data["receiver_class"]["constructor_vptr_store"] == "0x0070fb13 mov [esi],0x00b04524"
    assert data["receiver_class"]["destructor_vptr_store"] == "0x0070f5a0 mov [esi],0x00b04524"
    assert [r["site"] for r in data["sites"]] == ["0x0070f62d", "0x0070fb45", "0x0070fdeb"]


def test_vptr_mismatch_rejects_manager_identity():
    data = load_evidence()
    assert data["participants_manager_identity"]["root_vptr"] == "0x00ab9190"
    assert data["participants_manager_identity"]["subobject_vptr"] == "0x00ab916c"
    assert all(r["can_target_participants_manager_plus_0x374"] is False for r in data["sites"])


def test_frontier_reduces_to_three_paths():
    a = load_evidence()["adjudication"]
    assert a["rejected_site_count"] == 3
    assert a["same_receiver_vptr_identity_complete"] is True
    assert a["remaining_callee_forwarding_path_count"] == 3
    assert a["remaining_sites"] == ["0x005292db", "0x005f4ffa", "0x005f6eda"]
    assert a["computed_address_manager_374_writer_surface_complete"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["last_literal_0x004b86cf_rejected"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
