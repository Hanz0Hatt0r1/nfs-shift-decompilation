"""Runtime-state admission oracle for the Phase 698 selected BODY pose.

Phase 700 is read-only: it validates runtime admission/persistence and delegates
BODY identity selection to vehicle_body_pose_selection_runtime. It does not
create a vehicle world transform or renderer/camera side effect.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from vehicle_body_pose_selection_runtime import (
    BodyPoseSnapshot,
    SelectedVehicleBodyPose,
    select_vehicle_body_pose,
)

FORMAT = "SHIFT.VehicleBodyPoseRuntimeHandoff/1"


@dataclass(frozen=True)
class RuntimePoseState:
    workspace_ready: bool
    participant_ready: bool
    participant_identity_join_proven: bool
    outer_initialized: bool
    body_count: int
    snapshot_generation: int
    explicit_update_count: int


@dataclass(frozen=True)
class VehicleBodyPoseRuntimeHandoffResult:
    pose: SelectedVehicleBodyPose
    runtime_body_count: int
    explicit_update_count: int


def build_vehicle_body_pose_runtime_handoff(
    state: RuntimePoseState,
    frontier: Mapping[str, Any],
    snapshots: Sequence[BodyPoseSnapshot],
) -> VehicleBodyPoseRuntimeHandoffResult:
    if not state.workspace_ready:
        raise ValueError("runtime pose handoff requires ready physics workspace")
    if not state.participant_ready or not state.participant_identity_join_proven:
        raise ValueError("runtime pose handoff requires admitted participant identity")
    if not state.outer_initialized:
        raise ValueError("runtime pose handoff requires initialized persistent outer state")
    if state.body_count <= 0:
        raise ValueError("runtime pose handoff requires positive BODY count")
    if len(snapshots) != state.body_count:
        raise ValueError("runtime pose handoff snapshot cardinality mismatch")

    pose = select_vehicle_body_pose(
        frontier,
        snapshots,
        snapshot_generation=state.snapshot_generation,
        explicit_update_count=state.explicit_update_count,
    )
    return VehicleBodyPoseRuntimeHandoffResult(
        pose=pose,
        runtime_body_count=state.body_count,
        explicit_update_count=state.explicit_update_count,
    )


def contract() -> dict[str, object]:
    return {
        "format": FORMAT,
        "phase": 700,
        "phase698_selector_reused": True,
        "phase699_provider_frontier_preserved": True,
        "workspace_admission_required": True,
        "participant_identity_admission_required": True,
        "persistent_outer_state_required": True,
        "snapshot_cardinality_required": True,
        "runtime_state_mutated": False,
        "current_process1_chassis_body_selected": False,
        "vehicle_world_transform_proven": False,
        "renderer_transport_enabled": False,
        "camera_follow_enabled": False,
        "fixed_step_auto_schedule": False,
        "deep_outer_update_executable_schedule_enabled": False,
    }


__all__ = [
    "FORMAT",
    "RuntimePoseState",
    "VehicleBodyPoseRuntimeHandoffResult",
    "build_vehicle_body_pose_runtime_handoff",
    "contract",
]
