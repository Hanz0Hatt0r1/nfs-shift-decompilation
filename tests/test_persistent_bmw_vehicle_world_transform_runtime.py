from __future__ import annotations

from dataclasses import replace

import pytest

from bmw_body0_vhf_world_matrix_composition_runtime import (
    ProvenBody0BindFrame,
    ProvenVhfBindFrame,
)
from persistent_bmw_vehicle_world_transform_runtime import (
    MAX_U64,
    PersistentVehicleWorldTransformState,
    RuntimeBodyPoseState,
    commit_retail_transform,
    contract,
    read_current_transform,
)


def _runtime() -> RuntimeBodyPoseState:
    return RuntimeBodyPoseState(
        initialized=True,
        body_count=2,
        body_index=0,
        snapshot_generation=0,
        explicit_update_count=0,
        origin=(10.0, 20.0, 30.0),
        basis=(
            1.0, 0.0, 0.0,
            0.0, 1.0, 0.0,
            0.0, 0.0, 1.0,
        ),
    )


def _vhf() -> ProvenVhfBindFrame:
    return ProvenVhfBindFrame(
        True,
        (
            0.0, 2.0, 0.0, 0.0,
            -1.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.5, 0.0,
            5.0, 6.0, 7.0, 1.0,
        ),
    )


def _bind(*, ready: bool = True) -> ProvenBody0BindFrame:
    return ProvenBody0BindFrame(
        ready,
        ready,
        0,
        False,
        (
            1.0, 0.0, 0.0, 0.0,
            0.0, 2.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            1.0, 2.0, 3.0, 1.0,
        ),
    )


def test_phase707_retail_identity_commits_and_reads_current_transform() -> None:
    runtime = _runtime()
    state = commit_retail_transform(
        PersistentVehicleWorldTransformState(),
        runtime=runtime,
        vhf_bind=_vhf(),
        body0_bind=_bind(),
    )
    assert state.ready is True
    assert state.body_index == 0
    assert state.source_runtime_body_count == 2
    assert state.source_pose_snapshot_generation == 0
    assert state.source_explicit_update_count == 0
    assert state.commit_generation == 1
    assert read_current_transform(state, runtime) == state.vehicle_world_matrix


def test_phase707_retail_identity_reaches_body0_bind_blocker() -> None:
    state = PersistentVehicleWorldTransformState()
    with pytest.raises(ValueError, match="proven-static"):
        commit_retail_transform(
            state,
            runtime=_runtime(),
            vhf_bind=_vhf(),
            body0_bind=_bind(ready=False),
        )
    assert state == PersistentVehicleWorldTransformState()


def test_phase706_failed_recommit_is_transactional() -> None:
    runtime = _runtime()
    committed = commit_retail_transform(
        PersistentVehicleWorldTransformState(),
        runtime=runtime,
        vhf_bind=_vhf(),
        body0_bind=_bind(),
    )
    with pytest.raises(ValueError, match="proven-static"):
        commit_retail_transform(
            committed,
            runtime=runtime,
            vhf_bind=_vhf(),
            body0_bind=_bind(ready=False),
        )
    assert read_current_transform(committed, runtime) == committed.vehicle_world_matrix


def test_phase706_rejects_stale_generation_and_update_count() -> None:
    runtime = _runtime()
    state = commit_retail_transform(
        PersistentVehicleWorldTransformState(),
        runtime=runtime,
        vhf_bind=_vhf(),
        body0_bind=_bind(),
    )
    with pytest.raises(ValueError, match="stale"):
        read_current_transform(state, replace(runtime, snapshot_generation=1))
    with pytest.raises(ValueError, match="stale"):
        read_current_transform(state, replace(runtime, explicit_update_count=1))


def test_phase706_rejects_reinitialize_with_reused_zero_generation() -> None:
    runtime = _runtime()
    state = commit_retail_transform(
        PersistentVehicleWorldTransformState(),
        runtime=runtime,
        vhf_bind=_vhf(),
        body0_bind=_bind(),
    )
    reinitialized = replace(runtime, origin=(11.0, 20.0, 30.0))
    with pytest.raises(ValueError, match="source BODY pose changed"):
        read_current_transform(state, reinitialized)


def test_phase706_successful_recommit_advances_only_transform_generation() -> None:
    runtime = _runtime()
    first = commit_retail_transform(
        PersistentVehicleWorldTransformState(),
        runtime=runtime,
        vhf_bind=_vhf(),
        body0_bind=_bind(),
    )
    second = commit_retail_transform(
        first,
        runtime=runtime,
        vhf_bind=_vhf(),
        body0_bind=_bind(),
    )
    assert second.commit_generation == 2
    assert second.vehicle_world_matrix == first.vehicle_world_matrix
    assert second.source_pose_snapshot_generation == first.source_pose_snapshot_generation


def test_phase706_commit_generation_overflow_fails_closed() -> None:
    state = replace(PersistentVehicleWorldTransformState(), commit_generation=MAX_U64)
    with pytest.raises(OverflowError, match="generation overflow"):
        commit_retail_transform(
            state,
            runtime=_runtime(),
            vhf_bind=_vhf(),
            body0_bind=_bind(),
        )


def test_phase707_contract_removes_identity_input_but_keeps_other_gates() -> None:
    payload = contract()
    assert payload["format"] == "SHIFT.PersistentBMWVehicleWorldTransform/1"
    assert payload["transactional_commit"] is True
    assert payload["source_pose_provenance_retained"] is True
    assert payload["stale_snapshot_generation_rejected"] is True
    assert payload["stale_explicit_update_count_rejected"] is True
    assert payload["reinitialized_pose_with_reused_generation_rejected"] is True
    assert payload["phase705_handoff_reused"] is True
    assert payload["current_retail_identity_ready"] is True
    assert payload["retail_identity_injected_by_caller"] is False
    assert payload["current_retail_BODY0_bind_ready"] is False
    assert payload["automatic_fixed_step_commit"] is False
    assert payload["renderer_mutation_enabled"] is False
    assert payload["camera_follow_enabled"] is False
    assert payload["original_game_executed"] is False
    assert payload["new_runtime_capture_required"] is False
