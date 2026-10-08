import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_manager_374_vslot0c_indirect_frontier.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_exact_outer_and_vslot_identity():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374VSlot0cIndirectFrontier/1"
    assert data["ready"] is True
    outer = data["outer_object"]
    assert outer["allocation_size"] == "0x46e0"
    assert outer["constructor"] == "FUN_0045ef50"
    assert "0x00bc185c" in outer["global_owner_store"]
    slot = data["vslot"]
    assert slot["vtable"] == "0x00ab5644"
    assert slot["slot_offset"] == "+0x0c"
    assert slot["slot_cell"] == "0x00ab5650"
    assert slot["slot_target"] == "FUN_0045b130"


def test_target_is_only_address_taken_by_single_vtable_cell():
    slot = load_evidence()["vslot"]
    assert slot["whole_pe_target_address_occurrence_count"] == 1
    assert slot["direct_call_count"] == 0
    assert slot["slot_target_mnemonic_sha256"] == "a2aaa664005d48f921de6944292eff22b8df7a3b6dfe93a645bf400c1fbdce4d"


def test_manager_root_is_not_stable_return_contract():
    shape = load_evidence()["return_shape"]
    assert shape["early_return_assigns_eax"] is False
    assert shape["manager_getter_calls"] == ["0x0045b162", "0x0045b181"]
    assert shape["manager_root_is_stable_function_return_contract"] is False


def test_direct_exact_root_dispatch_is_absent_but_interface_frontier_remains_open():
    data = load_evidence()
    scan = data["direct_exact_root_dispatch_scan"]
    assert scan["matching_callsite_count"] == 0
    assert scan["surface_complete_for_direct_exact_global_root_pattern"] is True
    adj = data["adjudication"]
    assert adj["direct_calls_closed"] is True
    assert adj["direct_exact_global_root_dispatch_closed"] is True
    assert adj["stable_manager_root_return_contract"] is False
    assert adj["generic_or_interface_indirect_dispatch_complete"] is False
    assert adj["runtime_created_or_opaque_manager_root_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
