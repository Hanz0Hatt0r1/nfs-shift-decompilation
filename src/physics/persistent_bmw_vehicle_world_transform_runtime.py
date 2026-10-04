"""Reference model for transactional persistent BMW vehicle world-transform state."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bmw_body0_vhf_world_matrix_composition_runtime import (
    ProvenBody0BindFrame,
    ProvenVhfBindFrame,
)
from bmw_vehicle_world_matrix_runtime_handoff_runtime import build_handoff
from global_vehicle_body_owner_selection_runtime import (
    GlobalVehicleBodyOwnerIdentityHandoff,
    build_selection,
)

FORMAT = "SHIFT.PersistentBMWVehicleWorldTransform/1"
MAX_U64 = (1 << 64) - 1


@dataclass(frozen=True)
class RuntimeBodyPoseState:
    initialized: bool
    body_count: int
    body_index: int
    snapshot_generation: int
    explicit_update_count: int
    origin: tuple[float, float, float]
    basis: tuple[float, float, float, float, float, float, float, float, float]


@dataclass(frozen=True)
class PersistentVehicleWorldTransformState:
    ready: bool = False
    body_index: int = 0
    source_runtime_body_count: int = 0
    source_pose_snapshot_generation: int = 0
    source_explicit_update_count: int = 0
    commit_generation: int = 0
    source_origin: tuple[float, float, float] = (0.0, 0.0, 0.0)
    source_basis: tuple[float, ...] = (0.0,) * 9
    vehicle_world_matrix: tuple[float, ...] = (0.0,) * 16


def commit_transform(
    state: PersistentVehicleWorldTransformState,
    *,
    runtime: RuntimeBodyPoseState,
    identity: GlobalVehicleBodyOwnerIdentityHandoff,
    vhf_bind: ProvenVhfBindFrame,
    body0_bind: ProvenBody0BindFrame,
) -> PersistentVehicleWorldTransformState:
    # Preserve Phase 703 identity-first admission before runtime-state checks.
    selection = build_selection(identity)
    if not runtime.initialized:
        raise ValueError("persistent outer state is not initialized")
    if runtime.body_count <= 0 or runtime.body_index < 0 or runtime.body_index >= runtime.body_count:
        raise ValueError("runtime BODY pose cardinality is invalid")
    if int(selection["body_index"]) != runtime.body_index:
        raise ValueError("selected BODY identity does not match runtime BODY pose")

    handoff = build_handoff(
        identity=identity,
        body_index=runtime.body_index,
        origin=runtime.origin,
        basis=runtime.basis,
        vhf_bind=vhf_bind,
        body0_bind=body0_bind,
    )
    if state.commit_generation >= MAX_U64:
        raise OverflowError("persistent vehicle world-transform generation overflow")

    return PersistentVehicleWorldTransformState(
        ready=True,
        body_index=runtime.body_index,
        source_runtime_body_count=runtime.body_count,
        source_pose_snapshot_generation=runtime.snapshot_generation,
        source_explicit_update_count=runtime.explicit_update_count,
        commit_generation=state.commit_generation + 1,
        source_origin=runtime.origin,
        source_basis=runtime.basis,
        vehicle_world_matrix=tuple(handoff["vehicle_world_matrix"]),
    )


def read_current_transform(
    state: PersistentVehicleWorldTransformState,
    runtime: RuntimeBodyPoseState,
) -> tuple[float, ...]:
    if not state.ready:
        raise ValueError("persistent vehicle world transform is not ready")
    if not runtime.initialized:
        raise ValueError("persistent outer state is not initialized")
    if (
        state.body_index != 0
        or state.source_runtime_body_count != runtime.body_count
        or state.body_index != runtime.body_index
        or state.source_pose_snapshot_generation != runtime.snapshot_generation
        or state.source_explicit_update_count != runtime.explicit_update_count
    ):
        raise ValueError("persistent vehicle world transform is stale")
    if state.source_origin != runtime.origin or state.source_basis != runtime.basis:
        raise ValueError("persistent vehicle world transform source BODY pose changed")
    return state.vehicle_world_matrix


def contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "transactional_commit": True,
        "source_pose_provenance_retained": True,
        "stale_snapshot_generation_rejected": True,
        "stale_explicit_update_count_rejected": True,
        "reinitialized_pose_with_reused_generation_rejected": True,
        "phase705_handoff_reused": True,
        "current_retail_identity_ready": False,
        "current_retail_BODY0_bind_ready": False,
        "automatic_fixed_step_commit": False,
        "renderer_mutation_enabled": False,
        "camera_follow_enabled": False,
        "original_game_executed": False,
        "new_runtime_capture_required": False,
    }
