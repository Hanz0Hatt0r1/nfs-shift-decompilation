"""Source-backed low-level SDF body state primitives."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.SDFBodyStatePrimitivesRuntime/1"

COEFFICIENT_OFFSETS = {
    "input": ["+0x128", "+0x12c", "+0x130"],
    "reciprocal": ["+0x138", "+0x140", "+0x148"],
}

ACCUMULATOR_OFFSETS = {
    "angular": ["+0x48", "+0x50", "+0x58"],
    "linear": ["+0x60", "+0x68", "+0x70"],
}


def _vec3(values: Sequence[float | int], *, name: str) -> tuple[float, float, float]:
    if len(values) != 3:
        raise ValueError(f"{name} must contain exactly 3 components")
    return float(values[0]), float(values[1]), float(values[2])


def initialize_body_coefficients(
    diagonal_values: Sequence[float | int],
) -> dict[str, Any]:
    """Reproduce FUN_007ba860's float/recriprocal coefficient writes."""
    x, y, z = _vec3(diagonal_values, name="diagonal_values")
    if x == 0.0 or y == 0.0 or z == 0.0:
        raise ValueError("diagonal values must be non-zero for reciprocal storage")
    fx, fy, fz = (_f32(x), _f32(y), _f32(z))
    return {
        "format": "SHIFT.SDFBodyCoefficientInit/1",
        "version": 1,
        "status": "computed",
        "ready": True,
        "input_float32": [fx, fy, fz],
        "input_double": [x, y, z],
        "reciprocal": [1.0 / x, 1.0 / y, 1.0 / z],
        "storage": COEFFICIENT_OFFSETS,
        "source_function": "FUN_007ba860",
        "reciprocal_source": "original double input, before float32 storage truncation",
        "next_stage": "FUN_007ba7e0",
    }


def point_accumulator_delta(
    world_point: Sequence[float | int],
    body_origin: Sequence[float | int],
    contribution: Sequence[float | int],
    *,
    sign: int = 1,
) -> dict[str, Any]:
    """Reproduce FUN_007ba9e0's point-offset accumulator update."""
    if int(sign) not in (-1, 1):
        raise ValueError("sign must be +1 or -1")
    px, py, pz = _vec3(world_point, name="world_point")
    ox, oy, oz = _vec3(body_origin, name="body_origin")
    vx, vy, vz = _vec3(contribution, name="contribution")

    rx = px - ox
    ry = py - oy
    rz = pz - oz

    return {
        "format": FORMAT,
        "version": 1,
        "status": "computed",
        "ready": True,
        "sign": int(sign),
        "lever_arm": [rx, ry, rz],
        "linear_delta": [
            int(sign) * vx,
            int(sign) * vy,
            int(sign) * vz,
        ],
        "angular_delta": [
            int(sign) * (ry * vz - rz * vy),
            int(sign) * (rz * vx - rx * vz),
            int(sign) * (rx * vy - ry * vx),
        ],
        "storage_offsets": ACCUMULATOR_OFFSETS,
        "source_function": "FUN_007ba9e0",
        "evidence": {
            "relative_point": [
                "world_point[0] - body +0x00",
                "world_point[1] - body +0x08",
                "world_point[2] - body +0x10",
            ],
            "angular_rule": "relative_point x contribution",
            "linear_rule": "contribution",
        },
    }


def describe_sdf_body_state_primitives() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "source-backed",
        "ready": True,
        "coefficient_init": {
            "function": "FUN_007ba860",
            "input_offsets": COEFFICIENT_OFFSETS["input"],
            "reciprocal_offsets": COEFFICIENT_OFFSETS["reciprocal"],
        },
        "point_accumulator": {
            "function": "FUN_007ba9e0",
            "world_point_offsets": ["+0x00", "+0x08", "+0x10"],
            "linear_offsets": ACCUMULATOR_OFFSETS["linear"],
            "angular_offsets": ACCUMULATOR_OFFSETS["angular"],
            "relative_point_rule": "point - body_origin",
        },
        "limitations": [
            "Coefficient and accumulator physical semantics remain source-opaque.",
            "FUN_007ba7e0 transformation is retained as a separate downstream stage.",
        ],
    }
