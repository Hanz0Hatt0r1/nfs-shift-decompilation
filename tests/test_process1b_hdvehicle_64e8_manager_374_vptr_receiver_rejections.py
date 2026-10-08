import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_manager_374_vptr_receiver_rejections.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_exact_vptr_rejection_inventory():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374VptrReceiverRejections/1"
    assert data["ready"] is True
    up = data["upstream"]
    assert up["remaining_site_count_before"] == 20
    assert up["manager_singleton_root"] == "0x00bc9fc0"
    assert up["manager_root_vptr"] == "0x00ab9190"
    assert up["participants_manager_subobject_vptr_at_manager_plus_0x20"] == "0x00ab916c"
    assert up["manager_constructor_vptr_proof"] == [
        "0x00488df5 mov [esi],0x00ab9190",
        "0x00488dfb mov [esi+0x20],0x00ab916c",
    ]
    assert up["inherited_negative_site_excluded_here"] == "0x005ded7e"
    rows = data["same_body_vptr_rejections"]
    assert [r["site"] for r in rows] == [
        "0x0074874b",
        "0x008169c3",
        "0x00833972",
        "0x00844343",
        "0x00844b67",
        "0x00d7f104",
    ]
    assert all(r["equals_manager_root_vptr"] is False for r in rows)


def test_unique_vtable_dispatch_rejects_three_more_sites():
    row = load_evidence()["unique_vtable_dispatch_rejection"]
    assert row["function"] == "FUN_008446a0"
    assert row["target_sites"] == ["0x008446cb", "0x008446e3", "0x008446f8"]
    assert row["whole_pe_function_pointer_occurrence_count"] == 1
    assert row["unique_function_pointer_location"] == "0x00b19144"
    assert row["owning_vtable"] == "0x00b190a8"
    assert row["vtable_slot_offset"] == "+0x9c"
    assert row["direct_callsite_count"] == 0
    assert row["owning_vtable_equals_manager_root_vptr"] is False


def test_owner_child_join_rejects_816c9c():
    row = load_evidence()["owner_child_vptr_rejection"]
    assert row["site"] == "0x00816c9c"
    assert row["function"] == "FUN_00816c70"
    assert row["child_constructor_final_vptr"] == "0x00b16158"
    assert row["child_getter"] == "0x0080b8f0 mov eax,[ecx+0x56c]; ret"
    assert row["receiver_vptr"] == "0x00b16158"
    assert row["equals_manager_root_vptr"] is False
    assert row["consumer_chain"][-2:] == [
        "0x00572f49 mov ecx,edi",
        "0x00572f4d call FUN_00816c70",
    ]


def test_embedded_owner_domains_reject_two_sites():
    row = load_evidence()["embedded_owner_address_rejections"]
    assert row["owner_constructor"] == "FUN_007c3170"
    assert row["owner_callsite_count"] == 3
    assert [item["callsite"] for item in row["owner_call_domains"]] == [
        "0x0076dfcc", "0x00798e74", "0x00a8ca65"
    ]
    assert row["fresh_allocation_receivers_are_new_objects_not_fixed_manager_singleton"] is True
    targets = row["embedded_targets"]
    assert [item["site"] for item in targets] == ["0x007c0fa0", "0x007c1ace"]
    assert [item["receiver_relation"] for item in targets] == ["owner+0x8", "owner+0xfe8"]
    assert all(item["equals_manager_singleton_root"] is False for item in targets)


def test_worklist_reduces_without_promoting_identity_join():
    adj = load_evidence()["adjudication"]
    assert adj["rejected_site_count"] == 12
    assert adj["remaining_literal_store_site_count"] == 8
    assert adj["same_body_vptr_rejected_site_count"] == 6
    assert adj["unique_vtable_dispatch_rejected_site_count"] == 3
    assert adj["owner_child_vptr_rejected_site_count"] == 1
    assert adj["embedded_owner_address_rejected_site_count"] == 2
    assert adj["rejections_use_exact_receiver_owner_or_address_identity"] is True
    assert adj["numeric_plus_0x374_equality_used_as_identity"] is False
    assert adj["remaining_literal_store_receiver_provenance_complete"] is False
    assert adj["computed_address_manager_374_writer_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
