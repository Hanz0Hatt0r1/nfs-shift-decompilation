import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "hdvehicle_64e8_render_manager_global_slot_owner_closure.json"


def _load():
    return json.loads(EVIDENCE.read_text())


def test_global_slot_owner_reference_inventory_is_pinned():
    report = _load()
    assert report["format"] == "SHIFT.HDVehicle64e8RenderManagerGlobalSlotOwnerClosure/1"
    assert report["ready"] is True
    refs = report["whole_text_reference_classification"]
    assert refs["total_instruction_references_to_0x00bc185c"] == 115
    assert refs["direct_value_loads"] == 112
    assert refs["slot_address_literal_materializations"] == 1
    assert refs["slot_writes"] == 2
    assert refs["other_reference_classes"] == 0
    assert refs["slot_address_literal"]["site"] == "0x004fb9af"
    assert refs["slot_address_literal"]["next_value_load"].startswith("0x004fb9b5")


def test_global_slot_success_and_failure_writer_provenance_is_pinned():
    report = _load()
    window = report["initializer_machine_window"]
    assert window["start"] == "0x00d362b9"
    assert window["end"] == "0x00d362fa"
    assert window["normalized_instruction_sha256"] == "52a65bf29f34f60a2c65dd5a161bc915393a3c3c27604b321775be7e29860a40"
    assert window["allocation"] == [
        "0x00d362b9 push 0x46e0",
        "0x00d362be call 0x008868c0",
    ]
    assert window["success_path"][-1] == "0x00d362ec mov [0x00bc185c],eax"
    assert window["failure_path"] == ["0x00d362f3 mov [0x00bc185c],esi"]


def test_constructor_identity_and_fail_closed_frontier_are_preserved():
    report = _load()
    ctor = report["constructor_identity"]
    assert ctor["entry"] == "0x0045ef50"
    assert ctor["captures_receiver"] == "0x0045ef59 mov esi,ecx"
    assert ctor["primary_vptr_write"] == "0x0045ef78 mov [esi],0x00ab5644"
    assert ctor["constructor_matches_merged_render_manager_identity"] is True

    adj = report["adjudication"]
    assert adj["canonical_global_slot_writer_surface_complete"] is True
    assert adj["canonical_global_slot_external_initialization_found"] is False
    assert adj["canonical_global_slot_unknown_origin_initialization_found"] is False
    assert adj["bounded_direct_target_opaque_surface_complete"] is True
    assert adj["external_or_unknown_origin_copies_of_exact_root_surface_complete"] is False
    assert adj["two_unknown_origin_hdvehicle_4330_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
