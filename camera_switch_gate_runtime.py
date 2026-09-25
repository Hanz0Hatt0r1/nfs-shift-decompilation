"""Evidence-backed CameraManager switch-request gate.

FUN_0080d3d0 decides whether a requested camera/view transition is already the
current runtime state. When it matches and the manager is not dirty, it returns
without rebuilding the active controller. Otherwise it clears the dirty byte,
snapshots the current state, invokes the switch preparation path, and reports
that a transition is required.

The exact semantic names of the integer mode/request fields remain contextual.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

FORMAT = "SHIFT.CameraSwitchGateRuntime/1"


@dataclass(frozen=True)
class CameraSwitchState:
    mode: int
    sub_index: int = -1
    sub_flag: int = 0
    camera_id: int = -1
    dirty: bool = False


def evaluate_switch_gate(
    state: CameraSwitchState,
    *,
    requested_mode: int,
    requested_sub_index: int,
    requested_sub_flag: int,
    requested_camera_id: int,
) -> dict[str, Any]:
    """Model the equality gate at the start of FUN_0080d3d0."""
    mode = int(requested_mode)
    sub_index = int(requested_sub_index)
    sub_flag = int(requested_sub_flag)
    camera_id = int(requested_camera_id)

    equivalent = (
        mode == state.mode
        and (mode != 1 or sub_index == state.sub_index)
        and sub_flag == state.sub_flag
        and camera_id == state.camera_id
        and not state.dirty
    )

    if equivalent:
        return {
            "format": FORMAT,
            "version": 1,
            "status": "already-current",
            "transition_required": False,
            "state_preserved": True,
            "state_after": {
                "mode": state.mode,
                "sub_index": state.sub_index,
                "sub_flag": state.sub_flag,
                "camera_id": state.camera_id,
                "dirty": state.dirty,
            },
            "evidence": {
                "gate": "FUN_0080d3d0",
                "fast_path_return": "current-mode-without-dirty",
            },
        }

    return {
        "format": FORMAT,
        "version": 1,
        "status": "transition-required",
        "transition_required": True,
        "state_preserved": False,
        "state_after": {
            "mode": state.mode,
            "sub_index": state.sub_index,
            "sub_flag": state.sub_flag,
            "camera_id": state.camera_id,
            "dirty": False,
        },
        "previous_state_snapshot": {
            "mode": state.mode,
            "sub_index": state.sub_index,
            "sub_flag": state.sub_flag,
            "camera_id": state.camera_id,
        },
        "requested": {
            "mode": mode,
            "sub_index": sub_index,
            "sub_flag": sub_flag,
            "camera_id": camera_id,
        },
        "evidence": {
            "gate": "FUN_0080d3d0",
            "dirty_clear": "+0x269d = 0",
            "previous_mode": "+0x26ac",
            "previous_slot": "+0x256c",
            "previous_camera_id": "+0x2578",
            "switch_preparation": "FUN_0080cd40",
        },
    }
