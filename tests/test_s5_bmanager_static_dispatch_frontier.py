import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/s5_bmanager_static_dispatch_frontier.json"


def _load():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_old_dispatch_assumptions_are_explicitly_superseded():
    report = _load()
    assert report["format"] == "SHIFT.BManagerStaticDispatchFrontier/2"
    assert report["status"] == "superseded-by-corrected-retail-dispatch-proof"
    assert report["ready"] is True
    corrections = report["corrections"]
    assert corrections["old_FUN_00647da0_plus_0x18_candidate_rejected"] is True
    assert corrections["FUN_00647da0_actual_indirect_slot"] == "0x20"
    assert corrections["correct_default_dispatcher"] == "FUN_00647d80"
    assert corrections["correct_default_dispatch_slot"] == "0x18"
    assert corrections["alternate_dispatch_slot"] == "0x1c"
    assert corrections["old_FUN_0070fe90_return_as_FUN_006485b0_stack_argument_rejected"] is True
    assert corrections["correct_FUN_006485b0_manager_receiver"] == "ECX/this"


def test_corrected_target_surface_tracks_registration_list_gate_and_selector():
    report = _load()
    infra = report["available_consumer_infrastructure"]
    assert infra["format"] == "SHIFT.BManagerPhysicsManagerDispatchFrontier/2"
    assert infra["retail_result_published"] is True
    assert infra["positive_retail_cadence_contract"] == "SHIFT.RetailOuterUpdateCadence/1"
    assert infra["exact_targets"] == [
        "FUN_00647d80",
        "FUN_00647ef0",
        "FUN_0065b8b0",
        "FUN_006626a0",
        "FUN_00662880",
        "FUN_00d36000",
        "FUN_006485b0",
        "FUN_00662600",
        "FUN_0070fe90",
    ]
    adjudication = report["adjudication"]
    assert adjudication["cPhysicsManager_registration_to_controller_list_verified"] is True
    assert adjudication["active_controller_list_to_timing_gate_verified"] is True
    assert adjudication["default_dispatch_operand_matches_cPhysicsManager_slot_plus_0x18"] is True
    assert adjudication["physics_manager_accessor_return_is_controller_api_this"] is True
    assert adjudication["bmanager_controller_to_cPhysicsManager_slot_plus_0x18_proven"] is True
    assert adjudication["retail_cadence_admitted_by_positive_consumer_contract"] is True


def test_corrected_frontier_preserves_fail_closed_limits():
    report = _load()
    assert report["retail_cadence_admitted"] is True
    limits = report["limits"]
    assert limits["alternate_BManager_mode_admitted"] is False
    assert limits["worker_poll_10ms_promoted"] is False
    assert limits["host_1_60_promoted"] is False
    assert limits["runtime_capture_used"] is False
    assert limits["original_game_executed"] is False
