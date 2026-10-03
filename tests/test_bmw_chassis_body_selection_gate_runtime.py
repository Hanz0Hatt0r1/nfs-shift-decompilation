from __future__ import annotations

from dataclasses import replace

import pytest

from bmw_chassis_body_selection_gate_runtime import (
    BmwChassisTopology,
    UpdateChildVehicleSolverBaseContinuity,
    build_selection,
    contract,
)


def test_current_continuity_frontier_fails_closed() -> None:
    with pytest.raises(ValueError, match="update-child to vehicle solver-base continuity"):
        build_selection(
            BmwChassisTopology(),
            UpdateChildVehicleSolverBaseContinuity(proven=False),
        )


def test_synthetic_future_positive_continuity_emits_exact_body_zero_selection() -> None:
    assert build_selection(
        BmwChassisTopology(),
        UpdateChildVehicleSolverBaseContinuity(proven=True),
    ) == {"selection_proven": True, "body_index": 0}


def test_topology_drift_fails_before_continuity_is_consumed() -> None:
    drifted = replace(BmwChassisTopology(), main_chassis_body_index=9)
    with pytest.raises(ValueError, match="proven retail BODY topology"):
        build_selection(
            drifted,
            UpdateChildVehicleSolverBaseContinuity(proven=True),
        )


def test_contract_keeps_current_runtime_identity_and_transform_closed() -> None:
    payload = contract()
    assert payload["format"] == "SHIFT.NativeBMWChassisBodySelectionGate/1"
    assert payload["main_chassis_body_selected"] is True
    assert payload["main_chassis_body_index"] == 0
    assert payload["current_update_child_to_vehicle_solver_base_continuity_proven"] is False
    assert payload["current_vehicle_body_selection_ready"] is False
    assert payload["phase698_selection_emitted_without_continuity"] is False
    assert payload["synthetic_positive_continuity_is_retail_proof"] is False
    assert payload["rear_axle_body_index_required_for_chassis_selection"] is False
    assert payload["world_transform_mapping_proven"] is False
    assert payload["fixed_step_auto_schedule"] is False
    assert payload["original_game_executed"] is False
    assert payload["new_runtime_capture_required"] is False
