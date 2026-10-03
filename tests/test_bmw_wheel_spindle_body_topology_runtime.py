from __future__ import annotations

from dataclasses import replace

import pytest

from bmw_wheel_spindle_body_topology_runtime import (
    ProvenRearAxleBodyIndex,
    complete_constraint_body_map,
    contract,
    retail_topology,
)


def test_retail_topology_carries_proven_named_and_chassis_indices() -> None:
    topology = retail_topology()
    assert topology.body_count == 11
    assert topology.wheel_body_indices == (3, 4, 7, 8)
    assert topology.spindle_body_indices == (1, 2, 5, 6)
    assert topology.wheel_spindle_body_indices_ready is True
    assert topology.rear_axle_body_index_ready is False
    assert topology.main_chassis_body_selected is True
    assert topology.main_chassis_body_index == 0
    assert topology.update_child_to_vehicle_solver_base_continuity_proven is False
    assert topology.vehicle_body_selection_ready is False


def test_full_constraint_map_fails_closed_without_rear_axle_proof() -> None:
    with pytest.raises(ValueError, match="rear-axle BODY identity"):
        complete_constraint_body_map(
            retail_topology(),
            ProvenRearAxleBodyIndex(proven=False, body_index=0),
        )


def test_future_proven_rear_axle_completes_map_without_changing_proven_indices() -> None:
    result = complete_constraint_body_map(
        retail_topology(),
        ProvenRearAxleBodyIndex(proven=True, body_index=9),
    )
    assert result == {
        "wheel_body_indices": (3, 4, 7, 8),
        "spindle_body_indices": (1, 2, 5, 6),
        "rear_axle_body_index": 9,
    }


def test_rear_axle_range_and_upstream_topology_drift_fail_closed() -> None:
    with pytest.raises(ValueError, match="outside the exact retail SDF domain"):
        complete_constraint_body_map(
            retail_topology(),
            ProvenRearAxleBodyIndex(proven=True, body_index=11),
        )

    drifted = replace(retail_topology(), wheel_body_indices=(3, 4, 7, 9))
    with pytest.raises(ValueError, match="topology drifted"):
        complete_constraint_body_map(
            drifted,
            ProvenRearAxleBodyIndex(proven=True, body_index=9),
        )


def test_contract_keeps_only_runtime_continuity_and_rear_axle_edges_unresolved() -> None:
    payload = contract()
    assert payload["format"] == "SHIFT.NativeBMWWheelSpindleBodyTopology/1"
    assert payload["wheel_body_indices"] == [3, 4, 7, 8]
    assert payload["spindle_body_indices"] == [1, 2, 5, 6]
    assert payload["wheel_spindle_body_indices_ready"] is True
    assert payload["rear_axle_body_index_ready"] is False
    assert payload["main_chassis_body_selected"] is True
    assert payload["main_chassis_body_index"] == 0
    assert payload["constraint_topology_proves_main_suspension_body"] is True
    assert payload["body_name_alone_proves_chassis_semantics"] is False
    assert payload["update_child_to_vehicle_solver_base_continuity_proven"] is False
    assert payload["vehicle_body_selection_ready"] is False
    assert payload["full_vehicle_constraint_body_map_ready"] is False
    assert payload["phase698_positive_selection_admissible"] is False
    assert payload["distinct_body_indices_assumed"] is False
    assert payload["original_game_executed"] is False
    assert payload["new_runtime_capture_required"] is False
