"""Pure camera-state helpers recovered from FUN_008167b0 and FUN_00813fd0."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.CameraResetAffineRuntime/1"


def initialize_affine_basis(
    basis_values: Sequence[float],
) -> dict[str, Any]:
    """Reproduce FUN_008167b0's post-basis affine writes."""
    if len(basis_values) != 16:
        raise ValueError("basis_values requires exactly 16 values")
    values = [float(v) for v in basis_values]
    # FUN_008167b0 calls FUN_00815ff0 first; these are its six explicit
    # post-call zeroes followed by the homogeneous w component.
    for index in (3, 7, 11, 12, 13, 14):
        values[index] = 0.0
    values[15] = 1.0
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "affine-basis-init",
        "matrix": values,
        "actions": [
            {"action": "FUN_00815ff0", "destination": "param_1"},
            {
                "action": "explicit affine writes",
                "zero_indices": [3, 7, 11, 12, 13, 14],
                "one_index": 15,
            },
        ],
        "evidence": {
            "function": "FUN_008167b0",
            "homogeneous_last": 1.0,
        },
    }


def reset_camera_target_state(
    *,
    resolved_target_data: Mapping[int, Any] | None,
) -> dict[str, Any]:
    """Reproduce FUN_00813fd0's reset and optional target-data propagation."""
    writes: dict[str, Any] = {
        "+0x58": 0,
        "+0x5c": 0,
        "+0x60": 0,
        "+0x1c": 0,
        "+0x20": 0,
        "+0x24": 0,
        "+0x28": 0,
        "+0x2c": 0,
        "+0x30": 0,
        "+0x68": 1,
    }
    actions: list[dict[str, Any]] = [
        {
            "action": "clear local state",
            "offsets": [
                "+0x58",
                "+0x5c",
                "+0x60",
                "+0x1c",
                "+0x20",
                "+0x24",
                "+0x28",
                "+0x2c",
                "+0x30",
            ],
        },
        {"action": "FUN_00812ed0"},
    ]

    if resolved_target_data is not None:
        writes.update({
            "+0x10": resolved_target_data.get(0x20, 0),
            "+0x14": resolved_target_data.get(0x24, 0),
            "+0x18": resolved_target_data.get(0x28, 0),
            "+0x34": resolved_target_data.get(0x64, 0),
            "+0x3c": resolved_target_data.get(0x6c, 0),
            "+0x40": resolved_target_data.get(0x70, 0),
        })
        actions.append({
            "action": "copy resolved target defaults",
            "source_offsets": ["+0x20", "+0x24", "+0x28", "+0x64", "+0x6c", "+0x70"],
            "destination_offsets": ["+0x10", "+0x14", "+0x18", "+0x34", "+0x3c", "+0x40"],
        })

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "camera-target-state-reset",
        "writes": writes,
        "actions": actions,
        "evidence": {
            "function": "FUN_00813fd0",
            "target_resolver": "FUN_00812ed0",
            "valid_flag": "+0x68",
        },
    }


def camera_jump_dispatch(
    *,
    vtable_target_present: bool,
    mode: int,
    payload: Any,
) -> dict[str, Any]:
    """Trace FUN_00813fb0's opaque vtable +0x58 dispatch."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "camera-jump-dispatch",
        "status": "dispatched" if vtable_target_present else "no-target",
        "action": (
            {"action": "vtable +0x58", "mode": int(mode), "payload": payload}
            if vtable_target_present
            else {"action": "no dispatch"}
        ),
        "evidence": {"function": "FUN_00813fb0", "method": "+0x58"},
    }
