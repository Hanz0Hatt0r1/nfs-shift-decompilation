"""Evidence-backed orientation-assist basis reconstruction from FUN_0081cd70.

The function is enabled only when camera data +0x80 exists, profile +0x1c is
positive, and the supplied delta is > 1.0. It builds a cross-product from the
normalized vehicle direction and negative vehicle velocity, normalizes it,
passes it through the executable's matrix/quaternion helper, applies the
observed damping factors, then constructs a second basis against the world
Y-axis and emits a 3x3 transform through FUN_004f8040/FUN_00449930.

Opaque trigonometric/service helpers remain caller-supplied boundaries.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Sequence

FORMAT = "SHIFT.CameraOrientationAssistRuntime/1"


@dataclass(frozen=True)
class OrientationAssistInputs:
    profile_enabled: bool
    profile_rate: float
    delta: float
    vehicle_direction: Sequence[float]
    negative_velocity: Sequence[float]
    angle_sample: float = 0.0
    position_damping: float = 0.0
    rotation_damping: float = 0.0


def _vec3(values: Sequence[float], name: str) -> tuple[float, float, float]:
    if len(values) != 3:
        raise ValueError(f"{name} requires three values")
    return float(values[0]), float(values[1]), float(values[2])


def normalize3(
    values: Sequence[float],
    *,
    epsilon: float = 0.0,
) -> tuple[tuple[float, float, float], float]:
    x, y, z = _vec3(values, "values")
    length = math.sqrt(x * x + y * y + z * z)
    if length <= float(epsilon):
        return (0.0, 0.0, 0.0), length
    inv = 1.0 / length
    return (x * inv, y * inv, z * inv), length


def cross3(
    left: Sequence[float],
    right: Sequence[float],
) -> tuple[float, float, float]:
    ax, ay, az = _vec3(left, "left")
    bx, by, bz = _vec3(right, "right")
    return (
        ay * bz - az * by,
        az * bx - ax * bz,
        ax * by - ay * bx,
    )


def describe_orientation_assist(
    inputs: OrientationAssistInputs,
    *,
    first_normalized_vector: Sequence[float] | None = None,
    first_norm_clamp: float | None = None,
    quaternion_output: Sequence[float] | None = None,
    helper_4a7820: float = 0.0,
    helper_900c40: float = 0.0,
    helper_900b10: float = 0.0,
) -> dict[str, Any]:
    """Trace FUN_0081cd70 with exact vector stages and opaque helper boundaries."""
    direction = _vec3(inputs.vehicle_direction, "vehicle_direction")
    neg_velocity = _vec3(inputs.negative_velocity, "negative_velocity")

    if not inputs.profile_enabled or float(inputs.profile_rate) <= 0.0 or float(inputs.delta) <= 1.0:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "orientation-assist",
            "status": "guarded-off",
            "actions": [],
            "guard": {
                "profile_exists": bool(inputs.profile_enabled),
                "profile_rate_gt_zero": float(inputs.profile_rate) > 0.0,
                "delta_gt_one": float(inputs.delta) > 1.0,
            },
            "evidence": {
                "function": "FUN_0081cd70",
                "profile_rate": "+0x1c",
            },
        }

    normalized_direction, direction_norm = normalize3(direction)
    first_cross = cross3(normalized_direction, neg_velocity)

    if first_normalized_vector is None:
        first_unit, cross_norm = normalize3(first_cross)
    else:
        first_unit, cross_norm = normalize3(first_normalized_vector)

    if first_norm_clamp is None:
        clamped_norm = min(1.0, max(0.0, cross_norm))
    else:
        clamped_norm = float(first_norm_clamp)

    actions: list[dict[str, Any]] = [
        {
            "action": "FUN_0081b500",
            "target": "local basis",
        },
        {
            "action": "FUN_00442310",
            "target": "vehicle direction",
            "input": direction,
            "normalized": normalized_direction,
        },
        {
            "action": "cross vehicle direction × negative velocity",
            "result": first_cross,
        },
        {
            "action": "sqrt/norm",
            "result": cross_norm,
        },
        {
            "action": "FUN_0040f3e0",
            "purpose": "clamp first norm into [0,1]",
            "result": clamped_norm,
        },
    ]

    local48, local44, local40 = neg_velocity

    if clamped_norm > 0.001:
        actions.append({
            "action": "normalize first cross vector",
            "epsilon": 0.001,
            "result": first_unit,
        })
        actions.append({
            "action": "FUN_0047bdb0",
            "arguments": {
                "basis": first_unit,
                "negative_velocity": neg_velocity,
            },
            "result": quaternion_output,
        })

        q = tuple(float(v) for v in quaternion_output) if quaternion_output is not None else (0.0, 0.0, 0.0, 0.0)
        if len(q) != 4:
            raise ValueError("quaternion_output requires four values")
        angle = float(inputs.angle_sample)
        angle_clamped = min(
            1.5707964,
            max(-1.5707964, angle),
        )
        normalized_abs = min(
            1.0,
            max(0.0, abs(angle_clamped) / 0.27925268),
        )
        blend = (
            (1.0 - normalized_abs) * (normalized_abs * normalized_abs)
            + normalized_abs * (1.0 - (normalized_abs - 1.0) * (normalized_abs - 1.0))
        )
        local24 = (
            float(helper_4a7820)
            * blend
            * 0.27925267815589905
            * 0.5
        )
        local18 = float(helper_900c40)
        mix_x = local18 * q[0]
        mix_y = local18 * q[2]
        mix_z = local18 * q[1]
        # Source fields local54/local50/local4c are the first, third and
        # second float components returned by FUN_0047bdb0.
        local48 = float(helper_900b10) * local48 + mix_x
        local44 = float(helper_900b10) * local44 + mix_y
        local40 = float(helper_900b10) * local40 + mix_z
        actions.extend([
            {
                "action": "FUN_0040f3e0",
                "purpose": "clamp angle",
                "range": [-1.5707964, 1.5707964],
                "result": angle_clamped,
            },
            {
                "action": "FUN_0040f3e0",
                "purpose": "clamp normalized angle magnitude",
                "range": [0.0, 1.0],
                "result": normalized_abs,
            },
            {
                "action": "FUN_004a7820",
                "argument": angle_clamped,
                "result": helper_4a7820,
            },
            {
                "action": "FUN_00900c40",
                "result": helper_900c40,
                "purpose": "quaternion contribution scalar",
            },
            {
                "action": "FUN_00900b10",
                "result": helper_900b10,
                "purpose": "velocity damping scalar",
            },
            {
                "action": "damping blend",
                "blend": blend,
                "angle_amplitude": local24,
            },
        ])
    else:
        local24 = 0.0
        local18 = 0.0
        actions.append({
            "action": "skip first quaternion build",
            "condition": "clamped_norm <= 0.001",
        })

    second_cross = (
        local40 * -1.0,
        0.0,
        local48 * -1.0,
    )
    second_normed, second_norm = normalize3(second_cross)

    if second_norm <= 0.01:
        actions.append({
            "action": "FUN_007840a0",
            "arguments": {
                "destination": "local +0x7c/+0x78/+0x74",
                "source": "local basis",
            },
        })
        second_basis = None
    else:
        if helper_7bdb0_output is None:
            second_basis = (*second_normed, helper_900b10)
        else:
            second_basis = tuple(float(v) for v in helper_7bdb0_output)
        actions.extend([
            {
                "action": "normalize second cross vector",
                "epsilon": 0.01,
                "result": second_normed,
            },
            {
                "action": "FUN_0047bdb0",
                "arguments": {
                    "axis": second_normed,
                    "reference": adjusted,
                },
                "result": helper_7bdb0_output,
            },
        ])

    if second_basis is None:
        output_basis = "fallback from FUN_007840a0"
    else:
        output_basis = second_basis

    actions.extend([
        {
            "action": "FUN_004f8040",
            "arguments": {
                "basis": output_basis,
            },
        },
        {
            "action": "FUN_00449930",
            "arguments": {
                "destination": "param_3",
            },
        },
    ])

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "orientation-assist",
        "status": "updated",
        "guard": {
            "profile_exists": True,
            "profile_rate": float(inputs.profile_rate),
            "delta": float(inputs.delta),
        },
        "vectors": {
            "vehicle_direction_normalized": normalized_direction,
            "negative_velocity": neg_velocity,
            "first_cross": first_cross,
            "first_cross_norm": cross_norm,
            "first_cross_unit": first_unit,
            "second_cross": second_cross,
            "second_cross_norm": second_norm,
            "second_cross_unit": second_normed,
        },
        "first_norm_clamp": clamped_norm,
    "damped_velocity": [local48, local44, local40],
        "output_basis": output_basis,
        "actions": actions,
        "evidence": {
            "function": "FUN_0081cd70",
            "profile_rate_field": "+0x1c",
            "vehicle_direction": ["param_2 +0x1c", "param_2 +0x20", "param_2 +0x24"],
            "negative_velocity": ["param_2 +0x640", "param_2 +0x644", "param_2 +0x648"],
            "first_norm_epsilon": 0.001,
            "second_norm_epsilon": 0.01,
            "angle_clamp": [-1.5707964, 1.5707964],
            "angle_scale": 0.27925268,
        },
        "limitations": [
            "FUN_00902620/FUN_00900c40/FUN_00900b10 are exposed as scalar helper inputs",
            "FUN_0047bdb0 and FUN_007840a0 results are kept as explicit boundaries",
            "the emitted basis is represented as source-order data, not assigned an engine-wide handedness convention",
        ],
    }
