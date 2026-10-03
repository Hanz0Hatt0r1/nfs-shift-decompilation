from __future__ import annotations

import math

import pytest

from vehicle_body_pose_selection_runtime import (
    BodyPoseSnapshot,
    contract,
    select_vehicle_body_pose,
)


def _snapshot(index: int) -> BodyPoseSnapshot:
    return BodyPoseSnapshot(
        body_index=index,
        origin=(float(index + 1), float(index + 2), float(index + 3)),
        basis=(1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0),
    )


def _frontier(*, ready: bool, identity: bool, body_index=1):
    return {
        "format": "SHIFT.VehicleBodyIdentityFrontier/1",
        "handoff": {
            "persistent_BODY_pose_available": True,
            "vehicle_BODY_selection_ready": ready,
            "selected_BODY_index": body_index if ready else None,
            "selected_BODY_pointer": None,
            "vehicle_world_transform_ready": False,
            "renderer_vehicle_transform_transport_ready": False,
        },
        "scope": {
            "update_child_to_BODY_identity_proven": identity,
            "vehicle_world_transform_mapping_proven": False,
        },
    }


def test_current_process1_frontier_fails_closed() -> None:
    with pytest.raises(ValueError, match="no proven BODY selection"):
        select_vehicle_body_pose(
            _frontier(ready=False, identity=False),
            [_snapshot(0), _snapshot(1)],
            snapshot_generation=2,
            explicit_update_count=2,
        )


def test_positive_identity_selects_exact_persistent_snapshot_without_transform() -> None:
    selected = select_vehicle_body_pose(
        _frontier(ready=True, identity=True, body_index=1),
        [_snapshot(0), _snapshot(1)],
        snapshot_generation=7,
        explicit_update_count=7,
    )
    assert selected.body_index == 1
    assert selected.snapshot_generation == 7
    assert selected.origin == (2.0, 3.0, 4.0)
    assert selected.basis == (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)


def test_identity_scope_and_selected_index_are_both_required() -> None:
    snapshots = [_snapshot(0), _snapshot(1)]
    with pytest.raises(ValueError, match="does not prove update-child to BODY identity"):
        select_vehicle_body_pose(
            _frontier(ready=True, identity=False),
            snapshots,
            snapshot_generation=1,
            explicit_update_count=1,
        )
    with pytest.raises(ValueError, match="invalid selected BODY index"):
        select_vehicle_body_pose(
            _frontier(ready=True, identity=True, body_index=-1),
            snapshots,
            snapshot_generation=1,
            explicit_update_count=1,
        )
    with pytest.raises(ValueError, match="exceeds persistent snapshot domain"):
        select_vehicle_body_pose(
            _frontier(ready=True, identity=True, body_index=2),
            snapshots,
            snapshot_generation=1,
            explicit_update_count=1,
        )


def test_generation_and_snapshot_identity_must_match_persistent_state() -> None:
    snapshots = [_snapshot(0), _snapshot(1)]
    with pytest.raises(ValueError, match="not synchronized"):
        select_vehicle_body_pose(
            _frontier(ready=True, identity=True),
            snapshots,
            snapshot_generation=1,
            explicit_update_count=2,
        )
    malformed = [_snapshot(0), BodyPoseSnapshot(0, (2.0, 3.0, 4.0), _snapshot(1).basis)]
    with pytest.raises(ValueError, match="does not match selected BODY index"):
        select_vehicle_body_pose(
            _frontier(ready=True, identity=True),
            malformed,
            snapshot_generation=2,
            explicit_update_count=2,
        )


def test_non_finite_pose_is_rejected() -> None:
    bad = BodyPoseSnapshot(
        body_index=1,
        origin=(2.0, math.inf, 4.0),
        basis=_snapshot(1).basis,
    )
    with pytest.raises(ValueError, match="non-finite"):
        select_vehicle_body_pose(
            _frontier(ready=True, identity=True),
            [_snapshot(0), bad],
            snapshot_generation=3,
            explicit_update_count=3,
        )


def test_contract_stops_before_world_transform_renderer_and_schedule() -> None:
    payload = contract()
    assert payload["format"] == "SHIFT.VehicleBodyPoseSelectionRuntime/1"
    assert payload["current_process1_frontier_ready"] is False
    assert payload["vehicle_world_transform_proven"] is False
    assert payload["basis_transpose_or_axis_remap"] is False
    assert payload["renderer_transport_enabled"] is False
    assert payload["camera_follow_enabled"] is False
    assert payload["fixed_step_auto_schedule"] is False
