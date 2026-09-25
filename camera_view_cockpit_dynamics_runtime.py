"""Evidence-backed numeric branches of FUN_0081c460.

This module reconstructs the arithmetic that directly updates +0x84/+0x88/+0x8c.
The generic angle-wrap and limit helper FUN_0040f3e0 remain explicit boundaries.
"""

from __future__ import annotations

import math
from typing import Any

from camera_view_dynamics_runtime import normalize_angle_with_pi

FORMAT = "SHIFT.CameraCockpitDynamicsRuntime/1"


def clamp_between(value: float, low: float, high: float) -> float:
    """Reproduce the source clamp shape used twice by the non-cockpit path."""
    x = float(value)
    lo = float(low)
    hi = float(high)
    if lo > hi:
        lo, hi = hi, lo
    return min(max(x, lo), hi)


def non_cockpit_update(
    *,
    selected_cockpit_profile: bool,
    delta: float,
    input_axis_0: float,
    input_axis_1: float,
    current_84: float,
    current_88: float,
    current_8c: float,
    rate_2c0_radians: float,
    rate_2c4_radians: float,
    rate_2b8_radians: float,
    rate_700_radians: float,
    direct_scale: float,
    smoothing_scale: float,
    target_84: float,
    target_88: float,
    use_smoothing: bool,
) -> dict[str, Any]:
    """Reproduce the non-profile+CockpitCam branch of FUN_0081c460."""
    if not selected_cockpit_profile:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "non-cockpit-update",
            "status": "profile-not-selected",
            "values": [+0.0, +0.0, +0.0],
            "state_after": {"+0x84": 0.0, "+0x88": 0.0, "+0x8c": 0.0},
            "evidence": {"function": "FUN_0081c460"},
        }

    dt = float(delta)
    v84 = float(current_84)
    v88 = float(current_88)

    if not use_smoothing:
        step = float(direct_scale) * dt
        v84 += float(input_axis_1) * step
        v88 += float(input_axis_0) * step
        v84 = clamp_between(v84, float(rate_2c0_radians), float(rate_2c4_radians))
        v88 = clamp_between(v88, float(rate_2b8_radians), float(rate_700_radians))
        branch = "direct-rate-and-clamp"
    else:
        factor = min(1.0, max(0.0, float(smoothing_scale) * dt))
        v84 += factor * (float(target_84) - v84)
        v88 += factor * (float(target_88) - v88)
        branch = "target-smoothing"

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "non-cockpit-update",
        "status": "updated",
        "branch": branch,
        "state_after": {"+0x84": v84, "+0x88": v88, "+0x8c": float(current_8c)},
        "evidence": {
            "function": "FUN_0081c460",
            "direct_scale": "DAT_00b8e030",
            "smoothing_scale": "DAT_00b8e034",
            "clamp_84": ["service +0x2c0", "service +0x2c4"],
            "clamp_88": ["service +0x2b8", "service +0x700"],
        },
    }


def cockpit_update(
    *,
    delta: float,
    input_c: float,
    input_8: float,
    steering_value: float,
    action5_bit0: bool,
    param4_low_byte_nonzero: bool,
    current_84: float,
    current_88: float,
    current_8c: float,
    target_84: float,
    target_88: float,
    limit_after_84_helper: float | None = None,
) -> dict[str, Any]:
    """Reproduce the arithmetic branches for profile +0xb8 != 0."""
    dt = float(delta)
    c = float(input_c)
    a = float(input_8)
    v84 = float(current_84)
    v88 = float(current_88)

    abs_c = abs(c)
    abs_a = abs(a)
    first_small = abs_c <= 0.1
    second_small = abs_a <= 0.1

    actions: list[dict[str, Any]] = []

    if not first_small:
        v88 -= dt * 2.0 * c
        wrapped = normalize_angle_with_pi(v88, seed=math.pi)
        actions.append({
            "action": "FUN_0081b610",
            "before": v88,
            "after": wrapped,
            "reason": "abs(input_c) > 0.1",
        })
        v88 = wrapped

    blend_used = False
    if second_small:
        if (
            first_small
            and abs(float(steering_value)) > 3.0
            and not bool(action5_bit0)
            and not bool(param4_low_byte_nonzero)
        ):
            first_factor = min(
                1.0,
                max(0.0, (abs(float(steering_value)) - 3.0) * 0.04),
            )
            blend_factor = min(
                1.0,
                max(0.0, (first_factor * 5.0 + 0.1) * dt),
            )
            v84 = v84 * (1.0 - blend_factor) + float(target_84) * blend_factor
            v88 = v88 * (1.0 - blend_factor) + float(target_88) * blend_factor
            blend_used = True
            actions.append({
                "action": "blend-target",
                "first_factor": first_factor,
                "blend_factor": blend_factor,
                "target": [float(target_84), float(target_88)],
            })
    else:
        v84 += dt * 2.0 * a
        helper_input = v84
        helper_output = (
            float(limit_after_84_helper)
            if limit_after_84_helper is not None
            else None
        )
        actions.append({
            "action": "FUN_0040f3e0",
            "input": helper_input,
            "limits_degrees": ["manager +0x560", "manager +0x564"],
            "output": helper_output,
        })
        if helper_output is not None:
            v84 = helper_output

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "cockpit-update",
        "status": "updated",
        "state_after": {"+0x84": v84, "+0x88": v88, "+0x8c": float(current_8c)},
        "predicates": {
            "abs_input_c_gt_0.1": not first_small,
            "abs_input_8_le_0.1": second_small,
            "steering_abs_gt_3": abs(float(steering_value)) > 3.0,
            "blend_used": blend_used,
        },
        "actions": actions,
        "evidence": {
            "function": "FUN_0081c460",
            "dead_zone": 0.1,
            "steering_threshold": 3.0,
            "steering_scale": 0.04,
            "blend_bias": 0.1,
            "blend_time_scale": 5.0,
            "increment_gain": 2.0,
        },
        "limitations": [
            "FUN_0081b610 is modeled for the explicit +0x88 wrap path using its sign branch",
            "FUN_0040f3e0 remains an opaque angle-limit helper",
        ],
    }
