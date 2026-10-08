import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_render_manager_returned_root_direct_callers.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_conditional_return_worklist_is_exactly_seven_functions():
    data = load_evidence()
    scan = data["machine_return_scan"]
    assert data["format"] == "SHIFT.HDVehicle64e8RenderManagerReturnedRootDirectCallerSurface/1"
    assert scan["direct_load_count"] == 112
    assert scan["partial_register_writes_invalidate_full_pointer"] is True
    assert scan["conditional_exact_eax_return_function_count"] == 7
    assert {f["function"] for f in scan["functions"]} == {
        "FUN_0040cfc0",
        "FUN_00499840",
        "FUN_004b7350",
        "FUN_004b73c0",
        "FUN_00512b00",
        "FUN_0051e010",
        "FUN_00558b30",
    }


def test_direct_caller_surface_is_six_and_all_clobber_before_consume():
    calls = load_evidence()["direct_callers"]["calls"]
    assert len(calls) == 6
    assert {c["callsite"] for c in calls} == {
        "0x0040d240",
        "0x0049a2cf",
        "0x005115ab",
        "0x0051e099",
        "0x0051e8e8",
        "0x008a82b0",
    }
    assert all(c["exact_eax_consumed_before_clobber"] is False for c in calls)
    assert all(c["exact_eax_persists_after_window"] is False for c in calls)


def test_two_indirect_only_callbacks_remain_fail_closed():
    frontier = load_evidence()["indirect_only_frontier"]
    assert frontier["function_count"] == 2
    assert frontier["functions"] == ["FUN_004b7350", "FUN_004b73c0"]
    assert frontier["direct_rel32_callsite_count"] == 0
    assert frontier["static_pointer_cells"] == ["0x00abed00", "0x00abed04"]
    assert frontier["recognized_as_vtable_slots_by_vtables_json"] is False
    assert frontier["indirect_consumer_return_use_complete"] is False


def test_global_gates_stay_fail_closed():
    adj = load_evidence()["adjudication"]
    assert adj["direct_returned_root_caller_surface_complete"] is True
    assert adj["direct_returned_root_caller_can_persist_or_dispatch_exact_root"] is False
    assert adj["indirect_table_only_return_consumer_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
