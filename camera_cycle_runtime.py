"""Exact camera ID cycling helper from FUN_008116a0.

The helper reacts to two device states returned by FUN_00649f40. The first
state advances the active camera id; when it reaches the configured count it
wraps to zero. The second state (only checked when the first is inactive)
decrements; when it becomes negative it wraps to count-1.

On a change it sets +0xb4 and calls FUN_0080e1b0 with the current active group
(+0x26a4) for both group arguments and the new camera id.
"""

from __future__ import annotations

from typing import Any

FORMAT = "SHIFT.CameraCycleRuntime/1"


def cycle_camera_id(
    *,
    current_id: int,
    camera_count: int,
    next_input_active: bool,
    previous_input_active: bool,
) -> dict[str, Any]:
    """Reproduce FUN_008116a0's exact two-probe branch."""
    current = int(current_id)
    count = int(camera_count)
    if count <= 0:
        raise ValueError("camera_count must be positive")

    selected = current
    direction: str | None = None

    if bool(next_input_active):
        selected = current + 1
        direction = "increment"
        if count <= selected:
            selected = 0
    else:
        if bool(previous_input_active):
            selected = current - 1
            direction = "decrement"
            if selected < 0:
                selected = count - 1

    changed = selected != current
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "cycle-camera-id",
        "current_id": current,
        "camera_count": count,
        "selected_id": selected,
        "changed": changed,
        "direction": direction,
        "actions": (
            [
                {
                    "action": "write +0xb4",
                    "value": 1,
                },
                {
                    "action": "FUN_0080e1b0",
                    "arguments": {
                        "group": "active +0x26a4",
                        "group_repeat": "active +0x26a4",
                        "camera_id": selected,
                    },
                },
            ]
            if changed
            else []
        ),
        "evidence": {
            "function": "FUN_008116a0",
            "active_camera_id": "manager +0x26a0",
            "camera_count": "this +0x38",
            "dirty_flag": "this +0xb4",
            "next_probe": "FUN_0064a010 -> FUN_00649f40",
            "previous_probe": "FUN_0064a010 -> FUN_00649f40",
        },
    }


def describe_cycle_update(
    *,
    manager_active_camera_id: int,
    camera_count: int,
    active_group: int,
    next_input_active: bool,
    previous_input_active: bool,
) -> dict[str, Any]:
    """Add the manager active-group values consumed by the source call."""
    result = cycle_camera_id(
        current_id=manager_active_camera_id,
        camera_count=camera_count,
        next_input_active=next_input_active,
        previous_input_active=previous_input_active,
    )
    if result["changed"]:
        result["actions"][1]["arguments"]["group"] = int(active_group)
        result["actions"][1]["arguments"]["group_repeat"] = int(active_group)
    return result
