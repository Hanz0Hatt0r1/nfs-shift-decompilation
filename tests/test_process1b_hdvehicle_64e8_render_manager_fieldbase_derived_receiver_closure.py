import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_render_manager_fieldbase_derived_receiver_closure.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_three_paths_are_pinned():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8RenderManagerFieldBaseDerivedReceiverClosure/1"
    assert data["ready"] is True
    assert data["upstream"]["bounded_direct_target_count"] == 17
    assert [item["direct_target"] for item in data["closed_paths"]] == [
        "0x00441fd0",
        "0x0045e110",
        "0x00467e20",
    ]


def test_441fd0_forwards_only_loaded_child():
    path = load_evidence()["closed_paths"][0]
    assert path["tail_target"] == "0x00476cf0"
    assert "child" in path["downstream_receiver"]
    assert path["exact_root_memory_store_found"] is False
    assert path["exact_root_return_found"] is False
    assert path["exact_root_reforward_found"] is False
    assert path["return_shape"] == "AL boolean 0/1"


def test_45e110_tail_dispatch_uses_child_receiver():
    path = load_evidence()["closed_paths"][1]
    assert "[root+0xc4c]" in path["tail_dispatch_receiver"]
    assert path["exact_root_memory_store_found"] is False
    assert path["exact_root_return_found"] is False
    assert path["exact_root_reforward_found"] is False
    assert path["body_mnemonic_sha256"] == "9092557ba20a815bf6bb732f7f9b0a79578593b072b73b86de68dc475344abf9"


def test_467e20_helper_reloads_root_only_to_derive_subobjects():
    path = load_evidence()["closed_paths"][2]
    assert path["tail_target"] == "0x00427610"
    assert path["helper_stack_save"].startswith("0x0046586e")
    assert path["helper_exact_root_reload_sites"] == ["0x00465e20", "0x00465f4f"]
    assert path["helper_exact_root_nonstack_store_found"] is False
    assert path["helper_exact_root_return_found"] is False
    assert path["helper_exact_root_reforward_found"] is False
    assert path["helper_body_mnemonic_sha256"] == "2ea39d1ecd5dbf145247f2cbe10cf7a2f1fa10a3d918bb9263872c1c67a3b1cb"


def test_global_frontiers_remain_fail_closed():
    adj = load_evidence()["adjudication"]
    assert adj["closed_path_count"] == 3
    assert adj["these_fieldbase_or_derived_receiver_paths_closed_negative"] is True
    assert adj["exact_outer_root_persisted_by_these_paths"] is False
    assert adj["exact_outer_root_returned_by_these_paths"] is False
    assert adj["exact_outer_root_forwarded_beyond_classified_boundaries"] is False
    assert adj["opaque_callee_created_or_returned_alias_surface_complete"] is False
    assert adj["external_or_unknown_origin_alias_surface_complete"] is False
    assert adj["two_unknown_origin_hdvehicle_4330_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
