"""Source-order pipeline for FUN_0081d2b0.

This is an orchestration boundary for CCameraView's large per-frame update.
Every stage is tied to an observed call or field access. Complex matrix,
collision-grid, service-vtable, and animation helpers remain explicit opaque
boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

FORMAT = "SHIFT.CameraViewUpdatePipelineRuntime/1"


@dataclass(frozen=True)
class CameraViewUpdateInputs:
    param1_delta: float
    param2_delta: float
    param4_low_byte_nonzero: bool
    param5_low_byte_nonzero: bool
    param6_low_byte_nonzero: bool
    runtime_ready: bool
    profile_present: bool
    service_present: bool
    selected_profile_id: int = 0  # +0xc0
    profile_has_b8_behavior: bool = False  # profile +0xb8
    profile_property_5_present: bool = False  # profile +0x5
    camera_data_dirty: bool = False  # +0xd1
    cockpit_flag: bool = False  # +0xd2
    d3_state: bool = False  # +0xd3
    profile_b4_mode: int = 0  # profile +0xb4
    speed_limit_value: float = 0.0  # +0x92c
    steering_sign_negative: bool = False  # +0x310
    profile_resolved_value: Any = None
    helper_23960_value: float = 0.0


def _fallback_actions() -> list[dict[str, Any]]:
    return [
        {
            "action": "FUN_0081b400",
            "target": "temporary 3x3 matrix",
        },
        {
            "action": "FUN_004f8040",
            "target": "output matrix argument",
        },
        {
            "action": "clear +0x60",
            "size": 0x100,
        },
    ]


def describe_camera_view_update(inputs: CameraViewUpdateInputs) -> dict[str, Any]:
    """Trace the main control flow of FUN_0081d2b0 without opaque-math guesses."""
    actions: list[dict[str, Any]] = [
        {"action": "clear +0x60", "size": 0x100},
    ]

    if not inputs.runtime_ready or not inputs.profile_present:
        actions.extend(_fallback_actions())
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "camera-view-update",
            "status": "fallback",
            "actions": actions,
            "evidence": {
                "function": "FUN_0081d2b0",
                "runtime_guard": "FUN_00703290()",
                "profile": "+0x80",
            },
        }

    effective_delta = (
        float(inputs.param2_delta)
        if inputs.param4_low_byte_nonzero
        else float(inputs.param1_delta)
    )
    actions.append({
        "action": "select effective delta",
        "value": effective_delta,
        "condition": (
            "param4.low8 != 0 -> param2"
            if inputs.param4_low_byte_nonzero
            else "param4.low8 == 0 -> param1"
        ),
    })

    if inputs.service_present and (
        not inputs.param4_low_byte_nonzero or inputs.camera_data_dirty
    ):
        actions.append({
            "action": "FUN_00481e20",
            "target": "+0x2d0",
            "source": "service object for +0xc0",
            "helper": "global service vtable +0x1c",
        })

    first_pass = bool(inputs.camera_data_dirty)
    if first_pass:
        actions.extend([
            {
                "action": "force delta",
                "value": 1000.0,
            },
            {
                "action": "clear +0xd1",
                "value": 0,
            },
            {
                "action": "FUN_0081bdb0",
                "target": "+0x84",
                "argument_delta": 1000.0,
            },
        ])

    if not inputs.service_present:
        actions.extend(_fallback_actions())
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "camera-view-update",
            "status": "service-fallback",
            "effective_delta": effective_delta,
            "actions": actions,
            "evidence": {
                "function": "FUN_0081d2b0",
                "service": "FUN_0080bfb0().+0x574",
            },
        }

    actions.append({
        "action": "load base velocity/state",
        "sources": ["+0x2e0", "+0x2e4", "+0x2e8"],
    })

    if inputs.param6_low_byte_nonzero and not inputs.param4_low_byte_nonzero:
        actions.append({
            "action": "FUN_004368e0 -> FUN_004422e0",
            "inputs": {
                "source": "+0x2ec",
                "delta": effective_delta,
            },
            "target": "base velocity/state",
        })

    actions.append({
        "action": "load secondary position/orientation offsets",
        "sources": ["+0x8ec", "+0x8f0", "+0x8f4"],
    })
    if inputs.profile_has_b8_behavior:
        actions.append({
            "action": "force local_7c = 0",
            "condition": "profile +0xb8 != 0",
        })

    if first_pass:
        actions.append({
            "action": "FUN_00675bd0",
            "target": "+0x180",
        })
    else:
        signed_speed = (
            -abs(float(inputs.speed_limit_value))
            if inputs.steering_sign_negative
            else abs(float(inputs.speed_limit_value))
        )
        actions.append({
            "action": "FUN_00823960",
            "target": "profile + selected +0xc0",
            "result": float(inputs.helper_23960_value),
        })
        actions.append({
            "action": "FUN_0081c460",
            "arguments": {
                "delta": effective_delta,
                "signed_speed_or_axis": signed_speed,
                "profile_scalar": float(inputs.helper_23960_value),
                "param4_low_byte_nonzero": bool(inputs.param4_low_byte_nonzero),
                "param5_low_byte_nonzero": bool(inputs.param5_low_byte_nonzero),
            },
        })

    actions.append({
        "action": "FUN_00823960",
        "target": "profile + selected +0xc0",
        "result": float(inputs.helper_23960_value),
    })
    actions.append({
        "action": "FUN_0081cd70",
        "arguments": {
            "speed": float(inputs.speed_limit_value),
            "source": "+0x2d0",
            "base_offsets": ["+0x84", "+0x80", "+0x7c"],
        },
    })

    if first_pass:
        actions.append({
            "action": "FUN_0081bc70",
            "target": "motion target state",
        })
    elif not inputs.param4_low_byte_nonzero:
        actions.append({
            "action": "FUN_0081b980",
            "delta": effective_delta,
            "target_state": "+0xa8/+0xac/+0xb0",
        })

    actions.append({
        "action": "resolve profile attachment",
        "condition": (
            "+0xd2 == 0 or profile target flag +0x5 == 0"
            if not inputs.cockpit_flag or not inputs.profile_property_5_present
            else "+0xd2 != 0 and profile target flag +0x5 != 0"
        ),
        "normal_path": "FUN_0081b680",
        "cockpit_path": "FUN_0081b6b0",
    })

    if not inputs.cockpit_flag:
        actions.append({
            "action": "update FOV from profile",
            "profile_fields": ["+0x54", "+0x58", "+0x5c"],
            "destination": "+0x34",
            "condition_expression": "profile +0x5c < speed == profile +0x5c == speed",
        })

    if inputs.profile_b4_mode != 0:
        actions.append({
            "action": "apply profile +0xb4 camera-space contribution",
            "mode": int(inputs.profile_b4_mode),
            "helper": "FUN_00442970",
            "scale_helper": "FUN_00433c10",
            "rotation_helper": "FUN_004422e0",
        })

    if inputs.cockpit_flag:
        actions.append({
            "action": "invert cockpit orientation components",
            "writes": {
                "orientation_x": "negate local_84",
                "orientation_y": "local_80 + PI",
                "orientation_z": "negate local_7c",
            },
        })

    actions.append({
        "action": "form target orientation",
        "formula": [
            "profile +0x38 + local_84",
            "profile +0x3c + local_80",
            "profile +0x40 + local_7c",
        ],
        "destination": ["local_34", "local_30", "local_2c"],
    })

    actions.append({
        "action": "orientation update gate",
        "condition": "+0x269c == 0 in owning camera manager",
        "direct_path": (
            "write +0x90/+0x94/+0x98 directly"
            if inputs.d3_state
            else "rate-limited update via profile +0x10/+0x14/+0x18 and FUN_0081b610"
        ),
    })

    if inputs.param4_low_byte_nonzero and inputs.profile_has_b8_behavior and not first_pass:
        actions.append({
            "action": "collision-sample grid",
            "grid": "18x18",
            "sample_helper": "FUN_007024f0(3)",
            "note": "raw source stage; no gameplay label assigned",
        })

    actions.extend([
        {
            "action": "normalize/look-at helper",
            "helper": "FUN_004d05a0",
            "source": "+0x2d0",
        },
        {
            "action": "write output matrix",
            "helper": "FUN_004f8040",
        },
        {
            "action": "FUN_0081caf0",
            "argument": float(inputs.speed_limit_value),
        },
    ])

    if not inputs.param4_low_byte_nonzero:
        actions.extend([
            {"action": "FUN_0081c100", "delta": effective_delta},
            {"action": "FUN_0081c180", "delta": effective_delta},
        ])

    actions.append({
        "action": "copy +0x2ec/+0x2f0/+0x2f4 -> +0x28/+0x2c/+0x30",
    })
    actions.append({
        "action": "finalize orientation/output matrix",
        "helper": "FUN_0081b400 + FUN_004f8040",
    })
    actions.append({
        "action": "clear +0x60",
        "size": 0x100,
    })

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "camera-view-update",
        "status": "updated",
        "effective_delta": effective_delta,
        "first_pass": first_pass,
        "actions": actions,
        "evidence": {
            "function": "FUN_0081d2b0",
            "frame_stack": "+0x60",
            "profile": "+0x80",
            "camera_manager": "+0x44",
            "motion_target": "+0x2d0",
            "velocity_state": "+0x2e0..+0x2f4",
            "camera_position_state": "+0x84/+0x80/+0x7c",
            "output_position": "+0x10/+0x14/+0x18",
            "output_orientation": "+0x1c/+0x20/+0x24",
        },
        "limitations": [
            "collision grid and matrix construction helpers remain opaque",
            "FUN_00823960 result is an explicit input boundary",
            "profile/service vtable helpers are not assigned new semantics",
        ],
    }
