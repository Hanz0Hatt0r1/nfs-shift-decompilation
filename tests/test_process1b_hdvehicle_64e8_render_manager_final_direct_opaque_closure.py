import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_render_manager_final_direct_opaque_closure.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_exact_final_target_set():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8RenderManagerFinalDirectOpaqueClosure/1"
    assert data["ready"] is True
    assert [item["target"] for item in data["targets"]] == [
        "0x0045bfc0",
        "0x0045cc50",
        "0x0045db50",
        "0x00462400",
    ]


def test_leaf_and_derived_pointer_paths_do_not_export_exact_root():
    targets = {item["target"]: item for item in load_evidence()["targets"]}
    leaf = targets["0x0045bfc0"]
    assert leaf["nested_helper"]["reads_entry_ecx"] is False
    assert len(leaf["exact_root_uses_after_capture"]) == 2
    assert leaf["exact_root_stored"] is False
    assert leaf["exact_root_returned"] is False
    assert leaf["exact_root_reforwarded"] is False

    derived = targets["0x0045cc50"]
    assert derived["exact_root_register_use_count"] == 3
    assert derived["derived_stack_local_read_count_after_store"] == 0
    assert derived["exact_root_stored"] is False
    assert derived["exact_root_returned"] is False
    assert derived["exact_root_reforwarded_as_argument"] is False


def test_pointer_to_local_is_zeroed_before_first_read():
    target = {item["target"]: item for item in load_evidence()["targets"]}["0x0045db50"]
    assert "[ebp-0x4]" in target["stack_local_seed"]
    assert target["pointer_to_local_read_before_overwrite"] is False
    assert "0x00d77868" in target["overwrite_before_read"]
    assert target["post_helper_reload_can_be_original_exact_root"] is False
    assert target["exact_root_returned"] is False


def test_fun_00462400_nested_receiver_paths_are_bounded():
    target = {item["target"]: item for item in load_evidence()["targets"]}["0x00462400"]
    assert target["exact_root_callsite_count"] == 13
    assert len(target["exact_root_callsites"]) == 13
    assert len(target["direct_root_field_uses"]) == 3
    nested = {item["target"]: item for item in target["nested_paths"]}
    assert nested["FUN_00633980"]["reads_entry_ecx"] is False
    assert nested["FUN_0045abe0"]["status"].startswith("closed by")
    assert nested["thunk_FUN_004300ae"]["status"].startswith("closed by")
    assert nested["FUN_0045abf0"]["entry_ecx_read_before_replacement"] is False
    assert nested["FUN_0045abf0"]["first_nested_target_reads_ecx"] is False
    assert target["exact_root_stored"] is False
    assert target["exact_root_returned"] is False


def test_frozen_direct_worklist_is_exhausted_but_global_frontier_stays_open():
    data = load_evidence()
    work = data["worklist"]
    assert work["frozen_original_direct_target_count"] == 17
    assert work["closed_before_this_contract"] == 13
    assert work["closed_this_contract"] == 4
    assert work["remaining_bounded_direct_targets"] == []
    assert work["bounded_direct_target_surface_complete"] is True

    adj = data["adjudication"]
    assert adj["exact_outer_root_first_hop_direct_callee_surface_complete"] is True
    assert adj["bounded_direct_target_opaque_surface_complete"] is True
    assert adj["external_or_unknown_origin_alias_surface_complete"] is False
    assert adj["two_unknown_origin_hdvehicle_4330_surface_complete"] is False
    assert adj["global_opaque_or_external_alias_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
