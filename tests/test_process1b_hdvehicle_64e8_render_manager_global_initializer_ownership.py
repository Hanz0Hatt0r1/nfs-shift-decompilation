import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_render_manager_global_initializer_ownership.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_global_store_surface_is_complete_and_local():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8RenderManagerGlobalInitializerOwnership/1"
    assert data["ready"] is True
    inv = data["machine_inventory"]
    assert inv["whole_image_store_to_target_global_count"] == 2
    assert inv["store_sites"] == [
        "0x00d362ec mov [0x00bc185c],eax",
        "0x00d362f3 mov [0x00bc185c],esi",
    ]
    win = data["initializer_window"]
    assert win["zero_sentinel_setup"] == "0x00d36224 xor esi,esi"
    assert win["allocation_size_push"] == "0x00d362b9 push 0x46e0"
    assert win["allocator_call"] == "0x00d362be call 0x008868c0"
    assert win["constructor_call"] == "0x00d362d9 call 0x0045ef50"
    assert win["success_store"] == "0x00d362ec mov [0x00bc185c],eax"
    assert win["failure_store"] == "0x00d362f3 mov [0x00bc185c],esi"


def test_slot_address_literal_is_not_promoted_to_outer_root_value():
    data = load_evidence()
    inv = data["machine_inventory"]
    assert inv["address_literal_materialization_site"] == "0x004fb9af mov edi,0x00bc185c"
    assert inv["address_literal_is_pointer_to_global_slot_not_outer_root_value"] is True


def test_fail_closed_frontier_remains_open_beyond_canonical_slot():
    adj = load_evidence()["adjudication"]
    assert adj["canonical_global_root_is_locally_allocated_and_constructed"] is True
    assert adj["canonical_global_root_external_initialization_found"] is False
    assert adj["target_global_store_surface_complete"] is True
    assert adj["external_or_unknown_origin_alias_copies_surface_complete"] is False
    assert adj["two_unknown_origin_hdvehicle_4330_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
