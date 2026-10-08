import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_render_manager_slot_address_consumer_closure.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_unique_slot_address_is_immediately_dereferenced_and_derived():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8RenderManagerSlotAddressConsumerClosure/1"
    assert data["ready"] is True
    occ = data["unique_slot_address_occurrence"]
    assert occ["slot_address_literal"].startswith("0x004fb9af")
    assert occ["immediate_dereference"].startswith("0x004fb9b5")
    assert occ["derived_receiver"].startswith("0x004fb9b7")
    assert occ["slot_address_stored_forwarded_or_returned_before_dereference"] is False
    assert occ["exact_outer_root_stored_forwarded_or_returned_before_derivation"] is False


def test_derived_path_reuses_bounded_item_primitives():
    data = load_evidence()
    path = data["derived_path"]
    assert "0x0048fc70" in path["first_consumer"]
    assert path["fun_0048fc70"]["allocator_stores_same_derived_pointer"] is True
    assert path["fun_0048fc70"]["subtracts_0x780_or_recovers_outer_root"] is False
    assert path["fun_00493410"]["recovers_item_pointer_via_FUN_00632fe0"] is True
    assert path["fun_00493410"]["subtracts_0x780_or_recovers_outer_root"] is False
    shared = data["shared_item_primitives"]
    assert shared["FUN_00633290"]["stored_pointer_is"] == "outer+0x780"
    assert shared["FUN_00632fe0"]["recovers_exact_outer_root"] is False
    assert shared["FUN_006333f0"]["this_minus_0x780_reconstruction"] is False


def test_unknown_origin_frontier_remains_fail_closed():
    adj = load_evidence()["adjudication"]
    assert adj["unique_slot_address_literal_consumer_surface_complete"] is True
    assert adj["slot_address_literal_escapes_before_dereference"] is False
    assert adj["resulting_outer_plus_0x780_path_reconstructs_exact_outer_root"] is False
    assert adj["slot_address_occurrence_adds_new_unknown_origin_exact_root_source"] is False
    assert adj["external_or_unknown_memory_exact_root_surface_complete"] is False
    assert adj["two_unknown_origin_hdvehicle_4330_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
