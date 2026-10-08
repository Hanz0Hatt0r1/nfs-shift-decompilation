import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_manager_374_vptr_receiver_rejections.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_identity_anchors_and_same_body_sites():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374VptrReceiverRejections/1"
    assert data["ready"] is True
    up = data["upstream"]
    assert up["manager_singleton_root"] == "0x00bc9fc0"
    assert up["manager_root_vptr"] == "0x00ab9190"
    assert up["participants_manager_subobject_vptr_at_manager_plus_0x20"] == "0x00ab916c"
    assert [r["site"] for r in data["same_body_vptr_rejections"]] == [
        "0x0074874b", "0x008169c3", "0x00833972",
        "0x00844343", "0x00844b67", "0x00d7f104",
    ]


def test_unique_vtable_and_owner_child_surfaces():
    table = load_evidence()["unique_vtable_dispatch_rejection"]
    assert table["target_sites"] == ["0x008446cb", "0x008446e3", "0x008446f8"]
    assert table["unique_function_pointer_location"] == "0x00b19144"
    assert table["owning_vtable"] == "0x00b190a8"
    assert table["direct_callsite_count"] == 0

    children = load_evidence()["owner_child_vptr_rejections"]
    assert [row["site"] for row in children] == ["0x00816c9c", "0x00818157"]
    assert all(row["receiver_vptr"] == "0x00b16158" for row in children)
    assert children[0]["child_source"] == "owner+0x56c"
    assert children[1]["target_receiver_capture"] == "0x0081800e mov ebx,ecx"


def test_embedded_owner_and_copy_rejections():
    embedded = load_evidence()["embedded_owner_address_rejections"]
    assert embedded["owner_constructor"] == "FUN_007c3170"
    assert [x["callsite"] for x in embedded["owner_call_domains"]] == [
        "0x0076dfcc", "0x00798e74", "0x00a8ca65"
    ]
    assert [x["site"] for x in embedded["embedded_targets"]] == ["0x007c0fa0", "0x007c1ace"]
    assert all(x["equals_manager_singleton_root"] is False for x in embedded["embedded_targets"])

    copy = load_evidence()["embedded_copy_receiver_rejection"]
    assert copy["site"] == "0x00a44ac5"
    assert copy["outer_vptr"] == "0x00b35e6c"
    assert copy["target_receiver_relation"] == "outer+0x10"
    assert copy["equals_manager_singleton_root"] is False


def test_worklist_reduces_without_promoting_identity_join():
    adj = load_evidence()["adjudication"]
    assert adj["rejected_site_count"] == 14
    assert adj["remaining_literal_store_site_count"] == 6
    assert adj["same_body_vptr_rejected_site_count"] == 6
    assert adj["unique_vtable_dispatch_rejected_site_count"] == 3
    assert adj["owner_child_vptr_rejected_site_count"] == 2
    assert adj["embedded_owner_address_rejected_site_count"] == 2
    assert adj["embedded_copy_receiver_rejected_site_count"] == 1
    assert adj["rejections_use_exact_receiver_owner_vptr_or_address_identity"] is True
    assert adj["numeric_plus_0x374_equality_used_as_identity"] is False
    assert adj["remaining_literal_store_receiver_provenance_complete"] is False
    assert adj["computed_address_manager_374_writer_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
