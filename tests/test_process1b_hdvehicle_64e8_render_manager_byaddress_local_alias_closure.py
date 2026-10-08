import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_render_manager_byaddress_local_alias_closure.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_two_byaddress_local_paths_are_pinned():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8RenderManagerByAddressLocalAliasClosure/1"
    assert data["ready"] is True
    assert data["upstream"]["bounded_direct_target_count"] == 17
    paths = data["closed_paths"]
    assert len(paths) == 2
    assert [item["direct_target"] for item in paths] == ["0x00462250", "0x004695e0"]


def test_helpers_overwrite_original_local_before_reading_it():
    for item in load_evidence()["closed_paths"]:
        assert item["pointed_slot_read_before_overwrite"] is False
        assert item["exact_outer_root_observable_by_helper"] is False
        assert item["exact_outer_root_exported_or_persisted"] is False
        assert "mov dword ptr [esi],0" in item["first_access_to_pointed_slot"]


def test_exact_machine_routes_are_stable():
    paths = load_evidence()["closed_paths"]
    assert paths[0]["helper_thunk"] == "0x00481860 -> 0x00d5ddb0"
    assert paths[0]["helper_local_pointer_capture"].startswith("0x00d5ddc7")
    assert paths[0]["caller_prefix_mnemonic_sha256"] == "0355cb7080ddc7d9d56f7e75f239bdf9f17dc031263336e4964861d730437ba0"
    assert paths[0]["helper_prefix_mnemonic_sha256"] == "6878a2418da0db05cbc9a33375b41a0ab997ee4f842df9b9b7af8dc7d9e71c0a"
    assert paths[1]["tail_target"] == "0x004b1ea0"
    assert paths[1]["helper_thunk"] == "0x0045ecf0 -> 0x00d52670"
    assert paths[1]["helper_local_pointer_capture"].startswith("0x00d5269c")
    assert paths[1]["caller_body_mnemonic_sha256"] == "f2e9fbd03f5eb4c295384138b4133f1702de508b103acbc1271a645e85ec575d"
    assert paths[1]["helper_prefix_mnemonic_sha256"] == "0c70230dd466d9e7d44ecc90c7f392b9110bbfea0760b2a8b2595a4a2cc59487"


def test_remaining_frontiers_stay_fail_closed():
    adj = load_evidence()["adjudication"]
    assert adj["closed_path_count"] == 2
    assert adj["these_byaddress_local_paths_closed_negative"] is True
    assert adj["helper_reads_original_exact_root_from_local"] is False
    assert adj["helper_exports_original_exact_root"] is False
    assert adj["opaque_callee_created_or_returned_alias_surface_complete"] is False
    assert adj["external_or_unknown_origin_alias_surface_complete"] is False
    assert adj["two_unknown_origin_hdvehicle_4330_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
