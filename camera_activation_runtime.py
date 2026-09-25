"""Evidence-backed camera activation state transition from SHIFT.exe.

FUN_0080e1b0 is the central camera activation path used after camera selection.
This module models the observable transition decisions while leaving callback
side effects external.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

FORMAT = "SHIFT.CameraActivationRuntime/1"


@dataclass(frozen=True)
class CameraActivationState:
    active_group: int = -1
    active_camera_id: int = -1


def activate_camera(
    state: CameraActivationState,
    *,
    param_1: int,
    param_2: int,
    param_3: int,
    camera_found: bool,
    is_tracking_camera: bool,
) -> dict[str, Any]:
    """Reproduce FUN_0080e1b0 control-flow decisions."""
    effective_group = int(param_1) if int(param_2) == -1 else int(param_2)
    old_group = int(state.active_group)
    old_camera = int(state.active_camera_id)

    deactivated_old_group = (
        old_group if old_group != effective_group and old_group != -1 else None
    )

    if int(param_3) < 0:
        return {
            "format": FORMAT,
            "version": 1,
            "status": "ignored-negative-camera-id",
            "changed": False,
            "effective_group": effective_group,
            "selected_camera_id": old_camera,
            "activation_mode": None,
            "deactivated_old_group": deactivated_old_group,
            "evidence": {"selector": "FUN_0080e1b0"},
        }

    if old_camera == int(param_3):
        return {
            "format": FORMAT,
            "version": 1,
            "status": "no-op-already-active",
            "changed": False,
            "effective_group": effective_group,
            "selected_camera_id": old_camera,
            "activation_mode": None,
            "deactivated_old_group": deactivated_old_group,
            "evidence": {"selector": "FUN_0080e1b0"},
        }

    if not camera_found:
        return {
            "format": FORMAT,
            "version": 1,
            "status": "ignored-unresolved-camera",
            "changed": False,
            "effective_group": effective_group,
            "selected_camera_id": old_camera,
            "activation_mode": None,
            "deactivated_old_group": deactivated_old_group,
            "evidence": {
                "selector": "FUN_0080e1b0",
                "lookup": "FUN_0080b8e0",
            },
        }

    activation_mode = 2 if is_tracking_camera else 3
    return {
        "format": FORMAT,
        "version": 1,
        "status": "activated",
        "changed": True,
        "effective_group": effective_group,
        "selected_camera_id": int(param_3),
        "activation_mode": activation_mode,
        "deactivated_old_group": deactivated_old_group,
        "state_after": {
            "active_group": effective_group,
            "active_camera_id": int(param_3),
        },
        "evidence": {
            "selector": "FUN_0080e1b0",
            "object_lookup": "FUN_0080b8e0",
            "tracking_activation": "FUN_0080e0d0",
            "static_activation": "FUN_0080e140",
            "active_camera_set": "+0x26a0",
            "active_group_set": "FUN_0080d500 -> +0x26a4",
        },
        "limitations": [
            "callback and input-state side effects are not synthesized",
            "RTTI helper FUN_004b71f0 is represented only by the tracking boolean",
            "exact semantic names of group/mode integers remain contextual",
        ],
    }
