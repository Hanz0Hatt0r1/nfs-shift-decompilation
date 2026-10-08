import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_render_manager_plus780_item_alias_closure.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_exact_two_root_derived_entry_paths():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8RenderManagerPlus780ItemAliasClosure/1"
    assert data["ready"] is True
    paths = data["root_derived_entry_paths"]
    assert {(p["function"], p["materialization"], p["callsite"]) for p in paths} == {
        ("FUN_00498b80", "0x00498b93 lea ecx,[edi+0x780]", "0x00498b9b call FUN_0070e1c0"),
        ("FUN_00499240", "0x004995bf lea ecx,[ebx+0x780]", "0x004995c5 call FUN_0070e1c0"),
    }


def test_subobject_identity_and_virtual_noop_are_pinned():
    sub = load_evidence()["subobject_identity"]
    assert sub["constructor_call"] == "0x0045f0f8 call FUN_00633080 with ECX=outer+0x780"
    assert sub["vptr_store"] == "0x0063308a [subobject]=0x00aebdbc"
    assert sub["vtable"] == "0x00aebdbc"
    assert sub["slot_plus_0x08_target"] == "0x008f3df0"
    assert sub["slot_plus_0x08_target_body"] == "ret"


def test_item_persists_only_the_same_derived_pointer():
    item = load_evidence()["item_encapsulation"]
    assert item["body"] == "FUN_00d66440"
    assert item["allocator_helper"] == "FUN_00633290"
    assert item["derived_pointer_relative_to_returned_item"] == "item-0x0c"
    assert item["recovery_helper"] == "FUN_00632fe0"
    assert item["reconstructs_exact_outer_root"] is False


def test_derived_receiver_consumers_do_not_subtract_0x780():
    data = load_evidence()
    consumer = data["derived_receiver_consumer"]
    assert consumer["this_minus_0x780_reconstruction"] is False
    assert consumer["exact_outer_root_store_or_return"] is False
    assert consumer["virtual_slot_plus_0x08_target_is_noop"] is True
    helper = data["same_receiver_helper_surface"]
    assert helper["this_minus_0x780_reconstruction"] is False
    assert helper["exact_outer_root_store_or_return"] is False
    assert helper["descendant_receiver_offsets"] == ["+0x88", "+0x90"]
    assert helper["descendant_this_minus_0x780_reconstruction"] is False


def test_frontier_remains_fail_closed():
    adj = load_evidence()["adjudication"]
    assert adj["outer_plus_0x780_root_derived_entry_surface_complete"] is True
    assert adj["runtime_item_encapsulation_surface_complete"] is True
    assert adj["outer_plus_0x780_reconstructs_exact_outer_root"] is False
    assert adj["outer_plus_0x780_alias_surface_closed_negative_for_exact_root_reconstruction"] is True
    assert adj["derived_subobject_alias_surface_complete"] is True
    assert adj["callee_created_or_external_exact_root_alias_surface_complete"] is False
    assert adj["two_unknown_origin_hdvehicle_4330_alias_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
