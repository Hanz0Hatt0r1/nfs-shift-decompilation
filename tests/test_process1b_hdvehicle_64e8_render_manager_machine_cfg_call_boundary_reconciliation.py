import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_render_manager_machine_cfg_call_boundary_reconciliation.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_call_boundary_partition():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8RenderManagerMachineCfgCallBoundaryReconciliation/1"
    assert data["ready"] is True
    inv = data["inventory"]
    assert inv["call_boundary_observation_count"] == 303
    assert inv["unique_callsite_count"] == 302
    assert inv["callee_saved_only_unique_callsite_count"] == 207
    assert inv["caller_saved_exact_alias_unique_callsite_count"] == 95
    assert inv["caller_saved_direct_callsite_count"] == 92
    assert inv["caller_saved_indirect_callsite_count"] == 3
    assert inv["eax_only_unique_callsite_count"] == 41
    assert inv["ecx_or_edx_receiver_like_unique_callsite_count"] == 54
    assert inv["direct_ecx_or_edx_receiver_like_unique_callsite_count"] == 51


def test_indirect_calls_match_merged_vslot_surface():
    data = load_evidence()
    calls = data["indirect_calls"]
    assert [item["callsite"] for item in calls] == ["0x0056bcf2", "0x0056bd09", "0x0056bd59"]
    assert [item["merged_vslot_offset"] for item in calls] == ["+0x1c", "+0x20", "+0x1c"]
    adj = data["adjudication"]
    assert adj["machine_wide_new_indirect_exact_root_dispatch_found"] is False
    assert adj["all_machine_wide_indirect_exact_root_calls_match_merged_vslot_closure"] is True
    assert adj["target_vslot_plus_0x0c_reappears"] is False


def test_direct_and_opaque_frontiers_remain_fail_closed():
    adj = load_evidence()["adjudication"]
    assert adj["direct_call_receiver_surface_reproved_here"] is False
    assert adj["opaque_callee_created_or_returned_alias_surface_complete"] is False
    assert adj["external_or_unknown_origin_alias_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
