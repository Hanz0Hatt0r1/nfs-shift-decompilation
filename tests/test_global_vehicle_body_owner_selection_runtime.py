from __future__ import annotations
from dataclasses import replace
import pytest
from global_vehicle_body_owner_selection_runtime import (
    GlobalVehicleBodyOwnerIdentityHandoff,
    blocked_current_retail_handoff,
    build_selection,
    contract,
    synthetic_positive_handoff,
)

def test_current_retail_composed_identity_remains_fail_closed() -> None:
    with pytest.raises(ValueError, match="not retail-ready"):
        build_selection(blocked_current_retail_handoff())

def test_synthetic_positive_composed_identity_selects_exact_body_zero() -> None:
    assert build_selection(synthetic_positive_handoff()) == {"selection_proven": True, "body_index": 0}

def test_obsolete_update_child_gate_is_rejected() -> None:
    bad = replace(synthetic_positive_handoff(), phase703_update_child_equality_gate_required=True)
    with pytest.raises(ValueError, match="obsolete update-child equality gate"):
        build_selection(bad)

def test_readiness_flags_must_move_transactionally() -> None:
    bad = replace(synthetic_positive_handoff(), phase700_runtime_handoff_admissible=False)
    with pytest.raises(ValueError, match="readiness flags disagree"):
        build_selection(bad)

def test_blocked_identity_cannot_preclaim_body_zero() -> None:
    with pytest.raises(ValueError, match="preclaims a BODY index"):
        build_selection(GlobalVehicleBodyOwnerIdentityHandoff(selected_body_index=0))

def test_positive_identity_cannot_select_non_chassis_body() -> None:
    with pytest.raises(ValueError, match="must select BODY 0"):
        build_selection(replace(synthetic_positive_handoff(), selected_body_index=9))

def test_contract_tracks_process1_and_phase646_boundaries() -> None:
    payload = contract()
    assert payload["format"] == "SHIFT.NativeGlobalVehicleBodyOwnerSelection/1"
    assert payload["process1_contract"] == "SHIFT.GlobalVehicleBodyOwnerIdentity/1"
    assert payload["current_retail_global_vehicle_BODY_owner_identity_ready"] is False
    assert payload["current_retail_selected_BODY_index"] is None
    assert payload["retail_BMW_chassis_BODY_index"] == 0
    assert payload["obsolete_update_child_equality_gate_required"] is False
    assert payload["synthetic_positive_identity_is_retail_proof"] is False
    assert payload["phase698_selector_reused"] is True
    assert payload["phase700_runtime_handoff_reused"] is True
    assert payload["phase645_VHF_bind_transform_is_dynamic_physics_pose"] is False
    assert payload["phase646_dynamic_transform_transport_available"] is True
    assert payload["dynamic_BODY0_pose_to_VHF_composition_proven"] is False
    assert payload["fixed_step_auto_schedule"] is False
    assert payload["original_game_executed"] is False
    assert payload["new_runtime_capture_required"] is False
