"""Fail-closed Process 1 identity -> persistent BODY pose selection join.

This module deliberately stops before vehicle/world-transform or renderer transport.
It accepts only a positive SHIFT.VehicleBodyIdentityFrontier/1 handoff and selects
one already-persistent BODY pose snapshot by the proven BODY index.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.VehicleBodyPoseSelectionRuntime/1"
FRONTIER_FORMAT = "SHIFT.VehicleBodyIdentityFrontier/1"


@dataclass(frozen=True)
class BodyPoseSnapshot:
    body_index: int
    origin: tuple[float, float, float]
    basis: tuple[float, float, float, float, float, float, float, float, float]


@dataclass(frozen=True)
class SelectedVehicleBodyPose:
    body_index: int
    snapshot_generation: int
    origin: tuple[float, float, float]
    basis: tuple[float, float, float, float, float, float, float, float, float]


def _require_finite(values: Sequence[float], label: str) -> None:
    if not all(isfinite(float(value)) for value in values):
        raise ValueError(f"{label} contains non-finite value")


def select_vehicle_body_pose(
    frontier: Mapping[str, Any],
    snapshots: Sequence[BodyPoseSnapshot],
    *,
    snapshot_generation: int,
    explicit_update_count: int,
) -> SelectedVehicleBodyPose:
    if frontier.get("format") != FRONTIER_FORMAT:
        raise ValueError(f"expected {FRONTIER_FORMAT}")
    handoff = frontier.get("handoff")
    scope = frontier.get("scope")
    if not isinstance(handoff, Mapping) or not isinstance(scope, Mapping):
        raise ValueError("vehicle/BODY identity frontier is missing handoff or scope")
    if handoff.get("persistent_BODY_pose_available") is not True:
        raise ValueError("vehicle/BODY identity frontier does not admit persistent BODY pose")
    if handoff.get("vehicle_BODY_selection_ready") is not True:
        raise ValueError("vehicle/BODY identity frontier has no proven BODY selection")
    if scope.get("update_child_to_BODY_identity_proven") is not True:
        raise ValueError("vehicle/BODY identity frontier does not prove update-child to BODY identity")

    body_index = handoff.get("selected_BODY_index")
    if isinstance(body_index, bool) or not isinstance(body_index, int) or body_index < 0:
        raise ValueError("vehicle/BODY identity frontier has invalid selected BODY index")
    if snapshot_generation < 0 or explicit_update_count < 0:
        raise ValueError("persistent BODY pose generations must be non-negative")
    if snapshot_generation != explicit_update_count:
        raise ValueError("persistent BODY pose generation is not synchronized with explicit update state")
    if not snapshots:
        raise ValueError("persistent BODY pose snapshot set is empty")
    if body_index >= len(snapshots):
        raise ValueError("selected BODY index exceeds persistent snapshot domain")

    snapshot = snapshots[body_index]
    if snapshot.body_index != body_index:
        raise ValueError("selected snapshot BODY identity does not match selected BODY index")
    _require_finite(snapshot.origin, "selected BODY origin")
    _require_finite(snapshot.basis, "selected BODY basis")

    return SelectedVehicleBodyPose(
        body_index=body_index,
        snapshot_generation=snapshot_generation,
        origin=tuple(float(value) for value in snapshot.origin),
        basis=tuple(float(value) for value in snapshot.basis),
    )


def contract() -> dict[str, object]:
    return {
        "format": FORMAT,
        "process1_frontier_required": FRONTIER_FORMAT,
        "persistent_body_pose_required": True,
        "vehicle_body_selection_must_be_proven": True,
        "selected_body_index_must_be_explicit": True,
        "snapshot_generation_must_match_explicit_update_count": True,
        "current_process1_frontier_ready": False,
        "vehicle_world_transform_proven": False,
        "basis_transpose_or_axis_remap": False,
        "renderer_transport_enabled": False,
        "camera_follow_enabled": False,
        "fixed_step_auto_schedule": False,
    }


__all__ = [
    "FORMAT",
    "FRONTIER_FORMAT",
    "BodyPoseSnapshot",
    "SelectedVehicleBodyPose",
    "select_vehicle_body_pose",
    "contract",
]
