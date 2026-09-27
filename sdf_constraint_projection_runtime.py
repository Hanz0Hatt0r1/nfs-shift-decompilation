"""Exact JOINT/HINGE scalar projection primitives recovered from SHIFT.exe.c."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.SDFConstraintProjectionRuntime/2"

JOINT_SOURCE_LINE = 819089
HINGE_SOURCE_LINE = 819157
CROSS_SOURCE_LINE = 811731
GLOBAL_SCALE_SOURCE_LINE = 763749


def _vec3(values: Sequence[float | int], *, name: str) -> tuple[float, float, float]:
    if len(values) != 3:
        raise ValueError(f"{name} must contain exactly three values")
    return float(values[0]), float(values[1]), float(values[2])


def derive_constraint_scales(system_value: float | int) -> dict[str, float]:
    """Reproduce the global scale initialization used by SDF projection."""
    base = float(system_value) * 0.8
    return {
        "linear_scale": base + base,
        "quadratic_scale": base * base,
        "source": "FUN_0070fe90 -> FUN_0070fe90",
    }


def evaluate_joint_cross_terms(
    sample_position: Sequence[float | int],
    body_axis: Sequence[float | int],
) -> dict[str, float]:
    """Evaluate the three JOINT cross terms d2/d3/d5."""
    sx, sy, sz = _vec3(sample_position, name="sample_position")
    ax, ay, az = _vec3(body_axis, name="body_axis")
    return {
        "d2": sz * ay - sy * az,
        "d3": az * sx - sz * ax,
        "d5": sy * ax - ay * sx,
    }


def evaluate_joint_projection(
    *,
    body_position: Sequence[float | int],
    body_axis: Sequence[float | int],
    body_correction: Sequence[float | int],
    sample_position: Sequence[float | int],
    residual_vector: Sequence[float | int],
    linear_velocity: Sequence[float | int],
    linear_scale: float,
    quadratic_scale: float,
    side_flag: int = 0,
) -> dict[str, Any]:
    """Reproduce the complete scalar projection computed by FUN_007bac60."""

    bx, by, bz = _vec3(body_position, name="body_position")
    ax, ay, az = _vec3(body_axis, name="body_axis")
    cx, cy, cz = _vec3(body_correction, name="body_correction")
    sx, sy, sz = _vec3(sample_position, name="sample_position")
    rx, ry, rz = _vec3(residual_vector, name="residual_vector")
    lx, ly, lz = _vec3(linear_velocity, name="linear_velocity")

    d2 = sz * ay - sy * az
    d3 = bz * sx - sz * bx
    d5 = sy * bx - by * sx

    d4 = (
        (sx + bx) * quadratic_scale
        + (cx + d2) * linear_scale
        + (sz * ry - sy * rz)
        + (by * d5 - bz * d3)
        + lx
    )
    d6 = (
        (sy + by) * quadratic_scale
        + (cy + d3) * linear_scale
        + (sx * rz - sz * rx)
        + (bz * d2 - bx * d5)
        + ly
    )
    d7 = (
        (sz + bz) * quadratic_scale
        + (cz + d5) * linear_scale
        + (sy * rx - sx * ry)
        + (bx * d3 - by * d2)
        + lz
    )

    sign = 1.0 if int(side_flag) == 0 else -1.0
    return {
        "format": FORMAT,
        "version": 2,
        "status": "computed",
        "ready": True,
        "function": "FUN_007bac60",
        "source_line": JOINT_SOURCE_LINE,
        "side_flag": int(side_flag),
        "sign": sign,
        "intermediate": {"d2": d2, "d3": d3, "d5": d5},
        "lanes": [sign * d4, sign * d6, sign * d7],
        "raw_lanes": [d4, d6, d7],
        "destination": "this +0x150 + scalar_base*8",
        "sample_stride": 0x40,
        "scalar_base_offset": "+0x30",
    }


def apply_joint_projection(
    solver_vector: Sequence[float | int],
    scalar_base: int,
    lanes: Sequence[float | int],
    *,
    side_flag: int = 0,
) -> list[float]:
    """Apply JOINT's signed three-lane update to the per-body solver vector."""
    if len(lanes) != 3:
        raise ValueError("JOINT projection must contain exactly three lanes")
    base = int(scalar_base)
    if base < 0 or base + 2 >= len(solver_vector):
        raise ValueError("JOINT scalar base is outside solver vector")
    sign = 1.0 if int(side_flag) == 0 else -1.0
    out = [float(value) for value in solver_vector]
    for lane, value in enumerate(lanes):
        out[base + lane] += sign * float(value)
    return out


def evaluate_hinge_projection(
    *,
    body_axis: Sequence[float | int],
    residual_vector: Sequence[float | int],
    sample_angular: Sequence[float | int],
    sample_linear: Sequence[float | int],
    sample_position: Sequence[float | int],
    sample_frame_offset: Sequence[float | int],
    body_frame: Any | None,
    linear_scale: float,
    quadratic_scale: float,
    side_flag: int = 0,
) -> dict[str, Any]:
    """Reproduce FUN_007bae40's two scalar projection lanes."""

    ax, ay, az = _vec3(body_axis, name="body_axis")
    rx, ry, rz = _vec3(residual_vector, name="residual_vector")
    a0, a1, a2 = _vec3(sample_angular, name="sample_angular")
    b0, b1, b2 = _vec3(sample_linear, name="sample_linear")
    sx, sy, sz = _vec3(sample_position, name="sample_position")
    ox, oy, oz = _vec3(sample_frame_offset, name="sample_frame_offset")

    tx = ax * linear_scale + rx
    ty = ay * linear_scale + ry
    tz = az * linear_scale + rz

    coupling_scalar = (
        (a0 * b1 - a1 * b0) * az
        + ay * (a2 * b0 - a0 * b2)
        + ax * (a1 * b2 - a2 * b1)
    )
    axis_a = ax * a0 + ay * a1 + az * a2
    axis_b = ax * b0 + ay * b1 + az * b2

    branch_details: dict[str, Any]
    if int(side_flag) == 0:
        qx, qy, qz = tx, ty, tz
        branch_details = {
            "branch": "flag_zero",
            "transformed_sample_position": None,
            "cross_vector": None,
        }
    else:
        if body_frame is None:
            raise ValueError("body_frame is required when side_flag is nonzero")
        from sdf_body_frame_runtime import transform_vector_transpose

        t0, t1, t2 = transform_vector_transpose(body_frame, (sx, sy, sz))
        # FUN_007b1320(&sample_frame_offset, transformed_sample_position, out)
        # returns sample_frame_offset x transformed_sample_position.
        cx = t2 * oy - t1 * oz
        cy = t0 * oz - t2 * ox
        cz = ox * t1 - t0 * oy
        qx = tx + quadratic_scale * cx
        qy = ty + quadratic_scale * cy
        qz = tz + quadratic_scale * cz
        branch_details = {
            "branch": "flag_nonzero",
            "transformed_sample_position": [t0, t1, t2],
            "cross_vector": [cx, cy, cz],
        }

    lane0 = a0 * qx + a1 * qy + a2 * qz - axis_b * coupling_scalar
    lane1 = qz * b2 + qy * b1 + b0 * qx + axis_a * coupling_scalar

    sign = 1.0 if int(side_flag) == 0 else -1.0
    return {
        "format": FORMAT,
        "version": 2,
        "status": "computed",
        "ready": True,
        "function": "FUN_007bae40",
        "source_line": HINGE_SOURCE_LINE,
        "side_flag": int(side_flag),
        "sign": sign,
        "coupling_scalar": coupling_scalar,
        "axis_a": axis_a,
        "axis_b": axis_b,
        "raw_lanes": [lane0, lane1],
        "lanes": [sign * lane0, sign * lane1],
        "destination": "this +0x150 + scalar_base*8",
        "sample_stride": 0xA0,
        "scalar_base_offset": "+0x94",
        "branch_details": branch_details,
    }


def apply_hinge_projection(
    solver_vector: Sequence[float | int],
    scalar_base: int,
    lanes: Sequence[float | int],
) -> list[float]:
    """Apply HINGE's already-signed two-lane update to the solver vector."""
    if len(lanes) != 2:
        raise ValueError("HINGE projection must contain exactly two lanes")
    base = int(scalar_base)
    if base < 0 or base + 1 >= len(solver_vector):
        raise ValueError("HINGE scalar base is outside solver vector")
    out = [float(value) for value in solver_vector]
    out[base] += float(lanes[0])
    out[base + 1] += float(lanes[1])
    return out


def describe_joint_projection_provenance() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 2,
        "status": "source-backed",
        "ready": True,
        "function": "FUN_007bac60",
        "source_line": JOINT_SOURCE_LINE,
        "sample_stride": 0x40,
        "side_flag_offset": "+0x34",
        "scalar_base_offset": "+0x30",
        "destination": "this +0x150 + scalar_base*8",
        "proven_terms": {
            "d2": "sample[+0x28]*body[+0x20] - sample[+0x20]*body[+0x28]",
            "d3": "body[+0x28]*sample[+0x18] - sample[+0x28]*body[+0x18]",
            "d5": "sample[+0x20]*body[+0x18] - body[+0x20]*sample[+0x18]",
            "d4": "(sample.x+body.x)*Q + (body+0x78+d2)*L + (sample.z*residual.y-sample.y*residual.z) + (body.y*d5-body.z*d3) + linear.x",
            "d6": "(sample.y+body.y)*Q + (body+0x80+d3)*L + (sample.x*residual.z-sample.z*residual.x) + (body.z*d2-body.x*d5) + linear.y",
            "d7": "(sample.z+body.z)*Q + (body+0x88+d5)*L + (sample.y*residual.x-sample.x*residual.y) + (body.x*d3-body.y*d2) + linear.z",
        },
        "sign_rule": "sample +0x34 == 0 => add; otherwise subtract",
        "global_scales": {
            "Q": "_DAT_00b8d8b8",
            "L": "_DAT_00b8d8c0",
            "initialization": "Q=(0.8*system_value)^2; L=1.6*system_value",
            "source_line": GLOBAL_SCALE_SOURCE_LINE,
        },
    }


def describe_hinge_projection_provenance() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 2,
        "status": "source-backed",
        "ready": True,
        "function": "FUN_007bae40",
        "source_line": HINGE_SOURCE_LINE,
        "sample_stride": 0xA0,
        "scalar_base_offset": "+0x94",
        "side_flag_offset": "+0x98",
        "destination": "this +0x150 + scalar_base*8",
        "equations": {
            "tx": "body.axis.x*L + residual.x",
            "ty": "body.axis.y*L + residual.y",
            "tz": "body.axis.z*L + residual.z",
            "c": "body.axis dot (sample_angular x sample_linear)",
            "u": "body.axis dot sample_angular",
            "v": "body.axis dot sample_linear",
            "flag_zero_lane0": "sample_angular dot (tx,ty,tz) - v*c",
            "flag_zero_lane1": "sample_linear dot (tx,ty,tz) + u*c",
            "flag_nonzero_q": "t + Q*(transformed_sample_position x sample_frame_offset)",
            "flag_nonzero_lane0": "sample_angular dot q - v*c",
            "flag_nonzero_lane1": "sample_linear dot q + u*c",
        },
        "sign_rule": "sample +0x98 == 0 => add; otherwise subtract",
        "cross_helper": {
            "function": "FUN_007b1320",
            "source_line": CROSS_SOURCE_LINE,
            "argument_order": "sample_frame_offset x transformed_sample_position",
        },
    }


__all__ = [
    "FORMAT",
    "derive_constraint_scales",
    "evaluate_joint_cross_terms",
    "evaluate_joint_projection",
    "apply_joint_projection",
    "evaluate_hinge_projection",
    "apply_hinge_projection",
    "describe_joint_projection_provenance",
    "describe_hinge_projection_provenance",
]
