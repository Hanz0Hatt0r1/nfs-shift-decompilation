import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_render_manager_getter_residue_direct_surface_closure.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_independent_machine_inventory_is_complete_for_getters():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8RenderManagerGetterResidueDirectSurfaceClosure/1"
    assert data["ready"] is True
    replay = data["independent_machine_receiver_replay"]
    assert replay["whole_text_exact_direct_load_seed_count"] == 112
    assert replay["state_cap_hit_count"] == 0
    assert replay["target_0x00489ad0_receiver_like_callsite_count"] == 2
    assert replay["target_0x00493fb0_receiver_like_callsite_count"] == 1
    assert replay["getter_receiver_callsite_inventory_complete_for_this_replay"] is True


def test_489ad0_residual_ecx_is_never_consumed():
    target = load_evidence()["targets"][0]
    assert target["target"] == "0x00489ad0"
    assert target["returned_singleton"] == "0x00bc9fc0"
    assert target["returned_singleton_is_exact_outer_root"] is False
    assert target["hot_path_may_physically_preserve_entry_ecx"] is True
    assert [item["callsite"] for item in target["callsites"]] == ["0x004989c6", "0x00498ac4"]
    assert [item["ecx_clobber"] for item in target["callsites"]] == [
        "0x004989e7 mov ecx,esi",
        "0x00498ae5 mov ecx,esi",
    ]
    for item in target["callsites"]:
        assert item["exact_root_registers_at_call"] == ["ECX"]
        assert item["post_call_exact_root_ecx_read"] is False
        assert item["exact_root_persisted_forwarded_or_returned"] is False
    assert target["target_closed_negative"] is True


def test_493fb0_both_residual_paths_are_closed():
    target = load_evidence()["targets"][1]
    assert target["target"] == "0x00493fb0"
    assert target["returned_singleton"] == "0x00bcae00"
    assert target["returned_singleton_is_exact_outer_root"] is False
    assert len(target["callsites"]) == 1
    call = target["callsites"][0]
    assert call["callsite"] == "0x004d1a1f"
    assert call["exact_root_registers_at_call"] == ["ECX"]
    assert call["post_call_exact_root_ecx_read_before_branch"] is False
    zero = call["zero_branch"]
    assert zero["residual_ecx_reaches"] == "0x004d1a3f call 0x0045db50"
    assert zero["consumer_contract"] == "SHIFT.HDVehicle64e8RenderManagerOpaqueDirectTargetClosure15of17/1"
    assert zero["exact_root_escape"] is False
    nonzero = call["nonzero_branch"]
    assert nonzero["intermediate_getter_reads_entry_ecx"] is False
    assert nonzero["residual_ecx_clobber"] == "0x004d1a32 mov ecx,eax"
    assert nonzero["exact_root_escape"] is False
    assert call["exact_root_persisted_forwarded_or_returned"] is False
    assert target["target_closed_negative"] is True


def test_bounded_direct_surface_closes_17_of_17_but_global_frontier_stays_open():
    adj = load_evidence()["adjudication"]
    assert adj["closed_target_count_this_contract"] == 2
    assert adj["cumulative_explicitly_closed_direct_target_count"] == 17
    assert adj["bounded_direct_target_count"] == 17
    assert adj["bounded_receiver_transfer_direct_target_opaque_surface_complete"] is True
    assert adj["remaining_bounded_direct_target_count"] == 0
    assert adj["global_opaque_callee_created_or_returned_alias_surface_complete"] is False
    assert adj["external_or_unknown_origin_alias_surface_complete"] is False
    assert adj["two_unknown_origin_hdvehicle_4330_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
