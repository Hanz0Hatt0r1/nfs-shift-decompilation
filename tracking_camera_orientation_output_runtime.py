"""Evidence-backed TrackingCamera orientation output from FUN_008207c0.

The routine has four source-controlled branches:
1. target mode with a valid spline id and bStaticDirection clear: build a basis
   from target-camera direction and pass ten basis/scalar values to FUN_0063eb50.
2. target mode fallback: query the global camera service vtable +0x1c, optionally
   combine it with the stored orientation through FUN_004d0440, then emit through
   FUN_00401130.
3. non-target mode with bStaticDirection set: copy the stored quaternion +0x10..+0x1c.
4. non-target mode with bStaticDirection clear: derive two opaque angle values,
   build two opaque quaternions, multiply them with FUN_004d0440, and emit four
   floats.

No engine-wide quaternion convention is inferred here.
"""

from __future__ import annotations

import math
from typing import Any, Sequence

FORMAT = "SHIFT.TrackingOrientationOutputRuntime/1"


def _vec3(values: Sequence[float], name: str) -> tuple[float, float, float]:
    if len(values) != 3:
        raise ValueError(f"{name} requires exactly three values")
    return float(values[0]), float(values[1]), float(values[2])


def _quat(values: Sequence[float], name: str) -> tuple[float, float, float, float]:
    if len(values) != 4:
        raise ValueError(f"{name} requires exactly four values")
    return float(values[0]), float(values[1]), float(values[2]), float(values[3])


def normalize3(values: Sequence[float]) -> tuple[tuple[float, float, float], float]:
    x, y, z = _vec3(values, "values")
    length = math.sqrt(x * x + y * y + z * z)
    if length == 0.0:
        return (0.0, 0.0, 0.0), 0.0
    inv = 1.0 / length
    return (x * inv, y * inv, z * inv), length


def describe_tracking_orientation(
    *,
    target_mode: int,
    target_spline_id: int,
    static_direction: bool,
    camera_position: Sequence[float],
    target_position: Sequence[float],
    stored_quaternion: Sequence[float],
    service_available: bool,
    service_orientation: Sequence[float] | None = None,
    service_combined_orientation: Sequence[float] | None = None,
    spline_output_basis: Sequence[float] | None = None,
    spline_helper_args: Sequence[float] | None = None,
    angle_902620: float = 0.0,
    angle_90285a: float = 0.0,
    horizontal_is_zero: bool | None = None,
    quat_4d8c10_a: Sequence[float] | None = None,
    quat_4d8c10_b: Sequence[float] | None = None,
    multiplied_quaternion: Sequence[float] | None = None,
) -> dict[str, Any]:
    """Trace FUN_008207c0 source order with opaque helper results."""
    camera = _vec3(camera_position, "camera_position")
    target = _vec3(target_position, "target_position")
    stored = _quat(stored_quaternion, "stored_quaternion")

    is_target_mode = int(target_mode) == 1
    actions: list[dict[str, Any]] = [
        {"action": "FUN_0081f2e0", "result": "camera data pointer" if True else None}
    ]

    if is_target_mode and int(target_spline_id) != -1 and not static_direction:
        direction = (
            target[0] - camera[0],
            target[1] - camera[1],
            target[2] - camera[2],
        )
        direction_unit, direction_norm = normalize3(direction)

        first_axis = direction_unit
        # Source uses FUN_004e5ef0 twice and normalizes both intermediate vectors.
        first_cross_output = (
            tuple(float(v) for v in spline_output_basis[:3])
            if spline_output_basis is not None and len(spline_output_basis) >= 3
            else (0.0, 0.0, 0.0)
        )
        second_axis, second_norm = normalize3(first_cross_output)
        third_raw = (
            first_axis[1] * second_axis[2] - first_axis[2] * second_axis[1],
            second_axis[0] * first_axis[2] - first_axis[0] * second_axis[2],
            first_axis[0] * second_axis[1] - first_axis[1] * second_axis[0],
        )
        third_axis, third_norm = normalize3(third_raw)

        helper_args = (
            tuple(float(v) for v in spline_helper_args)
            if spline_helper_args is not None
            else (*second_axis, *third_axis, *first_axis, 0.0)
        )
        if len(helper_args) != 10:
            raise ValueError("spline_helper_args requires exactly ten values")

        output = (
            tuple(float(v) for v in spline_output_basis)
            if spline_output_basis is not None and len(spline_output_basis) == 9
            else None
        )
        actions.extend([
            {
                "action": "direction = target - camera",
                "value": direction,
            },
            {
                "action": "FUN_00442310",
                "target": "direction",
                "result": direction_unit,
            },
            {
                "action": "FUN_004e5ef0",
                "stage": 1,
            },
            {
                "action": "FUN_00442310",
                "stage": 2,
                "result_norm": second_norm,
            },
            {
                "action": "FUN_004e5ef0",
                "stage": 3,
            },
            {
                "action": "FUN_00442310",
                "stage": 4,
                "result_norm": third_norm,
            },
            {
                "action": "FUN_0063eb50",
                "arguments": list(helper_args),
                "result": list(output) if output is not None else None,
            },
            {
                "action": "FUN_004f8040",
                "result": list(output) if output is not None else None,
            },
        ])
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "tracking-orientation",
            "branch": "target-spline-direction",
            "output": list(output) if output is not None else None,
            "direction": {
                "raw": direction,
                "unit": direction_unit,
                "norm": direction_norm,
            },
            "basis": {
                "first": first_axis,
                "second": second_axis,
                "third": third_axis,
            },
            "actions": actions,
            "evidence": {
                "function": "FUN_008207c0",
                "mode_field": "+0x1a",
                "spline_id_field": "+0x1f",
                "static_direction_flag": "+0x101",
                "camera_position": "+0x10/+0x14/+0x18",
                "basis_builder": "FUN_0063eb50",
            },
            "limitations": [
                "FUN_0063eb50 output is opaque",
                "the 3x3 basis is retained in source-order only",
            ],
        }

    if is_target_mode:
        if not service_available:
            return {
                "format": FORMAT,
                "version": 1,
                "operation": "tracking-orientation",
                "branch": "target-mode-no-service",
                "output": None,
                "actions": actions,
            }

        service = (
            _quat(service_combined_orientation, "service_combined_orientation")
            if service_combined_orientation is not None
            else None
        )
        service_raw = (
            _quat(service_orientation, "service_orientation")
            if service_orientation is not None
            else None
        )
        if service_raw is not None and service is not None:
            combine_action = {
                "action": "FUN_004d0440",
                "arguments": ["service_orientation", "stored_quaternion"],
                "result": service,
            }
        else:
            combine_action = {
                "action": "use stored +0x04..+0x13 orientation directly"
            }

        emitted = list(service if service is not None else (service_raw or stored))
        actions.extend([
            {
                "action": "service vtable +0x1c",
                "argument": int(target_spline_id),
                "result": list(service_raw) if service_raw is not None else None,
            },
            combine_action,
            {
                "action": "FUN_00401130",
                "result": emitted,
            },
        ])
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "tracking-orientation",
            "branch": "target-service-fallback",
            "output": emitted,
            "actions": actions,
            "evidence": {
                "function": "FUN_008207c0",
                "service_object": "FUN_0080bfb0()+0x574",
                "service_vtable_method": "+0x1c",
                "stored_orientation": "+0x04..+0x13",
                "combine_helper": "FUN_004d0440",
                "emit_helper": "FUN_00401130",
            },
        }

    if static_direction:
        emitted = list(stored)
        actions.extend([
            {
                "action": "copy stored quaternion",
                "source": "+0x04..+0x13",
                "result": emitted,
            }
        ])
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "tracking-orientation",
            "branch": "static-direction",
            "output": emitted,
            "actions": actions,
            "evidence": {
                "function": "FUN_008207c0",
                "static_direction_flag": "+0x101",
            },
        }

    direction = (
        target[0] - camera[0],
        target[1] - camera[1],
        target[2] - camera[2],
    )
    direction_unit, direction_norm = normalize3(direction)
    if horizontal_is_zero is None:
        horizontal_is_zero = direction_unit[0] == 0.0 and direction_unit[2] == 0.0

    quat_a = _quat(quat_4d8c10_a or [1.0, 0.0, 0.0, 0.0], "quat_4d8c10_a")
    quat_b = _quat(quat_4d8c10_b or [1.0, 0.0, 0.0, 0.0], "quat_4d8c10_b")
    multiplied = _quat(
        multiplied_quaternion or [1.0, 0.0, 0.0, 0.0],
        "multiplied_quaternion",
    )
    actions.extend([
        {
            "action": "direction = target - camera",
            "value": direction,
        },
        {
            "action": "FUN_00449930",
            "source": "+0x04..+0x13",
        },
        {
            "action": "FUN_00442310",
            "result": direction_unit,
        },
        {
            "action": "FUN_00902620",
            "result": float(angle_902620),
        },
        {
            "action": (
                "local_28 = 0"
                if horizontal_is_zero
                else "FUN_0090285a"
            ),
            "result": 0.0 if horizontal_is_zero else float(angle_90285a),
        },
        {
            "action": "FUN_004d8c10",
            "result": list(quat_a),
        },
        {
            "action": "FUN_004d8c10",
            "result": list(quat_b),
        },
        {
            "action": "FUN_004d0440",
            "result": list(multiplied),
        },
    ])
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "tracking-orientation",
        "branch": "derived-quaternion",
        "output": list(multiplied),
        "direction": {
            "raw": direction,
            "unit": direction_unit,
            "norm": direction_norm,
            "horizontal_is_zero": bool(horizontal_is_zero),
        },
        "angles": {
            "FUN_00902620": float(angle_902620),
            "FUN_0090285a": 0.0 if horizontal_is_zero else float(angle_90285a),
        },
        "quaternion_helpers": {
            "FUN_004d8c10_a": list(quat_a),
            "FUN_004d8c10_b": list(quat_b),
            "FUN_004d0440": list(multiplied),
        },
        "actions": actions,
        "evidence": {
            "function": "FUN_008207c0",
            "static_direction_flag": "+0x101",
            "stored_quaternion": "+0x04..+0x13",
            "yaw_helper": "FUN_00902620",
            "pitch_helper": "FUN_0090285a",
        },
        "limitations": [
            "FUN_00902620/FUN_0090285a/FUN_004d8c10/FUN_004d0440 remain opaque",
            "no quaternion multiplication convention is inferred",
        ],
    }
