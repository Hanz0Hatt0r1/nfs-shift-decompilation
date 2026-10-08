import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_render_manager_opaque_direct_target_closure_15of17.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_bounded_target_accounting_is_15_of_17():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8RenderManagerOpaqueDirectTargetClosure15of17/1"
    assert data["ready"] is True
    assert data["upstream"]["bounded_direct_target_count"] == 17
    assert data["upstream"]["already_explicitly_closed_direct_target_count"] == 7
    assert len(data["closed_targets"]) == 8
    adj = data["adjudication"]
    assert adj["closed_target_count_this_contract"] == 8
    assert adj["cumulative_explicitly_closed_direct_target_count"] == 15
    assert adj["remaining_bounded_direct_target_count"] == 2
    assert data["remaining_bounded_direct_targets"] == ["0x00489ad0", "0x00493fb0"]


def test_449630_exact_root_is_edx_and_is_overwritten():
    item = load_evidence()["closed_targets"][0]
    assert item["target"] == "0x00449630"
    assert item["exact_root_receiver_callsites"] == ["0x004be25d", "0x004bf71b", "0x004c06e6"]
    assert item["exact_root_register_at_callsites"] == "EDX"
    assert item["first_target_edx_definition"].startswith("0x00449639")
    assert item["root_destroyed_before_forwarding"] is True
    assert item["exact_root_store_return_or_forward"] is False


def test_entry_clobber_targets_do_not_export_root():
    by_target = {item["target"]: item for item in load_evidence()["closed_targets"]}
    assert by_target["0x00459140"]["entry_root_consumed"] is False
    assert by_target["0x00459140"]["exact_root_store_return_or_forward"] is False
    assert by_target["0x0045abe0"]["first_call_reads_entry_ecx"] is False
    assert by_target["0x0045abe0"]["root_clobber_before_use"].startswith("0x0045abe5")
    assert by_target["0x0045abe0"]["exact_root_store_return_or_forward"] is False
    assert by_target["0x00468ed0"]["entry_root_read_or_save_before_clobber"] is False
    assert by_target["0x00468ed0"]["first_ecx_definition"].startswith("0x00468ee9")


def test_field_base_targets_never_forward_exact_root():
    by_target = {item["target"]: item for item in load_evidence()["closed_targets"]}
    leaf = by_target["0x0045bfc0"]
    assert leaf["exact_root_store_found"] is False
    assert leaf["exact_root_return_found"] is False
    assert leaf["exact_root_reforward_found"] is False
    cc = by_target["0x0045cc50"]
    assert cc["derived_receivers_only"] is True
    assert cc["exact_root_store_found"] is False
    assert cc["exact_root_return_found"] is False
    assert cc["exact_root_reforward_found"] is False


def test_45db50_output_slot_is_zeroed_before_read():
    item = next(item for item in load_evidence()["closed_targets"] if item["target"] == "0x0045db50")
    assert item["helper_chain"] == "0x0045b720 -> 0x004651a0 -> 0x004bb4f0 -> 0x00d77800"
    assert item["first_output_slot_dereference"].startswith("0x00d77868")
    assert item["output_slot_read_before_zero_overwrite"] is False
    assert item["original_exact_root_observable_or_exported"] is False


def test_462400_chain_has_no_unclassified_exact_root_escape():
    item = next(item for item in load_evidence()["closed_targets"] if item["target"] == "0x00462400")
    assert item["singleton_probe_reads_entry_ecx"] is False
    assert item["post_probe_root_clobber"].startswith("0x0045e6f1")
    assert item["45abe0_closes_before_use"] is True
    assert item["45abf0_reads_or_saves_entry_root_before_its_first_getter"] is False
    assert "0x00c26058" in item["final_dispatch_receiver"]
    assert item["exact_root_store_return_or_unclassified_forward"] is False


def test_global_frontier_remains_fail_closed_until_getters_close():
    adj = load_evidence()["adjudication"]
    assert adj["bounded_direct_target_surface_complete"] is False
    assert adj["opaque_callee_created_or_returned_alias_surface_complete"] is False
    assert adj["external_or_unknown_origin_alias_surface_complete"] is False
    assert adj["two_unknown_origin_hdvehicle_4330_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
