import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_manager_374_vslot0c_dispatch_closure.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_upstreams_are_pinned():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374VSlot0cDispatchClosure/1"
    assert data["ready"] is True
    assert data["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert data["vslot"]["primary_vtable"] == "0x00ab5644"
    assert data["vslot"]["target_slot_offset"] == "+0x0c"
    assert data["vslot"]["target"] == "FUN_0045b130"


def test_exact_manager_first_hop_surface_uses_only_1c_and_20():
    surface = load_evidence()["exhaustive_exact_manager_first_hop"]
    assert surface["source_read_count"] == 95
    assert surface["source_function_count"] == 80
    assert surface["proven_indirect_receiver_transfer_count"] == 3
    calls = surface["calls"]
    assert [c["callsite"] for c in calls] == ["0x0056bcf2", "0x0056bd09", "0x0056bd59"]
    assert [c["slot_offset"] for c in calls] == ["+0x1c", "+0x20", "+0x1c"]
    assert surface["target_slot_plus_0x0c_dispatch_count"] == 0


def test_retail_machine_slots_not_synthetic_fixture_slots():
    calls = load_evidence()["exhaustive_exact_manager_first_hop"]["calls"]
    assert calls[0]["slot_load"] == "0x0056bced mov edx,[eax+0x1c]"
    assert calls[1]["slot_load"] == "0x0056bd02 mov edx,[eax+0x20]"
    assert calls[2]["slot_load"] == "0x0056bd56 mov edx,[eax+0x1c]"


def test_frontier_closes_only_exact_global_first_hop():
    adj = load_evidence()["adjudication"]
    assert adj["exact_manager_first_hop_indirect_surface_complete"] is True
    assert adj["target_vslot_plus_0x0c_reached_by_exact_manager"] is False
    assert adj["fun_0045b130_alternate_manager_root_source_closed"] is True
    assert adj["runtime_created_or_copied_outer_alias_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
