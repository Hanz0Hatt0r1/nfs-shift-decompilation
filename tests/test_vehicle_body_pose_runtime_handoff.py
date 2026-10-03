from __future__ import annotations

import pytest

from vehicle_body_pose_selection_runtime import BodyPoseSnapshot
from vehicle_body_pose_runtime_handoff import (
    RuntimePoseState,
    build_vehicle_body_pose_runtime_handoff,
    contract,
)


def _snapshots():
    basis = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
    return [
        BodyPoseSnapshot(0, (1.0, 2.0, 3.0), basis),
        BodyPoseSnapshot(1, (-1.0, -2.0, -3.0), basis),
    ]


def _frontier(*, ready=True, identity=True, body_index=1):
    return {
        "format": "SHIFT.VehicleBodyIdentityFrontier/1",
        "handoff": {
            "persistent_BODY_pose_available": True,
            "vehicle_BODY_selection_ready": ready,
            "selected_BODY_index": body_index if ready else None,
        },
        "scope": {
            "update_child_to_BODY_identity_proven": identity,
        },
    }


def _state(**overrides):
    values = {
        "workspace_ready": True,
        "participant_ready": True,
        "participant_identity_join_proven": True,
        "outer_initialized": True,
        "body_count": 2,
        "snapshot_generation": 4,
        "explicit_update_count": 4,
    }
    values.update(overrides)
    return RuntimePoseState(**values)


def test_runtime_handoff_selects_phase698_pose_without_mutating_or_transforming() -> None:
    result = build_vehicle_body_pose_runtime_handoff(
        _state(),
        _frontier(),
        _snapshots(),
    )
    assert result.runtime_body_count == 2
    assert result.explicit_update_count == 4
    assert result.pose.body_index == 1
    assert result.pose.snapshot_generation == 4
    assert result.pose.origin == (-1.0, -2.0, -3.0)
    assert result.pose.basis == _snapshots()[1].basis


def test_workspace_participant_and_outer_state_fail_before_selection() -> None:
    frontier = _frontier()
    snapshots = _snapshots()
    with pytest.raises(ValueError, match="workspace"):
        build_vehicle_body_pose_runtime_handoff(
            _state(workspace_ready=False), frontier, snapshots
        )
    with pytest.raises(ValueError, match="participant identity"):
        build_vehicle_body_pose_runtime_handoff(
            _state(participant_ready=False), frontier, snapshots
        )
    with pytest.raises(ValueError, match="participant identity"):
        build_vehicle_body_pose_runtime_handoff(
            _state(participant_identity_join_proven=False), frontier, snapshots
        )
    with pytest.raises(ValueError, match="persistent outer state"):
        build_vehicle_body_pose_runtime_handoff(
            _state(outer_initialized=False), frontier, snapshots
        )


def test_runtime_cardinality_is_fail_closed() -> None:
    with pytest.raises(ValueError, match="positive BODY count"):
        build_vehicle_body_pose_runtime_handoff(
            _state(body_count=0), _frontier(), []
        )
    with pytest.raises(ValueError, match="cardinality mismatch"):
        build_vehicle_body_pose_runtime_handoff(
            _state(body_count=3), _frontier(), _snapshots()
        )


def test_current_process1_identity_frontier_remains_blocked() -> None:
    with pytest.raises(ValueError, match="no proven BODY selection"):
        build_vehicle_body_pose_runtime_handoff(
            _state(), _frontier(ready=False, identity=False), _snapshots()
        )


def test_phase698_generation_guard_is_preserved() -> None:
    with pytest.raises(ValueError, match="not synchronized"):
        build_vehicle_body_pose_runtime_handoff(
            _state(snapshot_generation=3, explicit_update_count=4),
            _frontier(),
            _snapshots(),
        )


def test_contract_does_not_promote_execution_schedule_or_render_transform() -> None:
    payload = contract()
    assert payload["format"] == "SHIFT.VehicleBodyPoseRuntimeHandoff/1"
    assert payload["phase"] == 700
    assert payload["phase698_selector_reused"] is True
    assert payload["phase699_provider_frontier_preserved"] is True
    assert payload["runtime_state_mutated"] is False
    assert payload["current_process1_chassis_body_selected"] is False
    assert payload["vehicle_world_transform_proven"] is False
    assert payload["renderer_transport_enabled"] is False
    assert payload["camera_follow_enabled"] is False
    assert payload["fixed_step_auto_schedule"] is False
    assert payload["deep_outer_update_executable_schedule_enabled"] is False
