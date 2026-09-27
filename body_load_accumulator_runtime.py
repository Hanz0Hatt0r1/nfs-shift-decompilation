"""Exact point-vector accumulation boundary for FUN_007baa70.

The function adds the supplied 3-vector into the linear accumulator at
+0x60/+0x68/+0x70 and adds point × vector into the angular/moment-like
accumulator at +0x48/+0x50/+0x58. No body-origin subtraction occurs inside
FUN_007baa70 itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence

FORMAT = "SHIFT.BodyLoadAccumulatorRuntime/1"
FUNCTION = "FUN_007baa70"
SOURCE_FILE = "SHIFT.exe.c"
SOURCE_LINE = 818986

MOMENT_X_OFFSET = 0x48
MOMENT_Y_OFFSET = 0x50
MOMENT_Z_OFFSET = 0x58
LINEAR_X_OFFSET = 0x60
LINEAR_Y_OFFSET = 0x68
LINEAR_Z_OFFSET = 0x70


@dataclass(frozen=True)
class Vec3:
    x: float
    y: float
    z: float

    def __post_init__(self) -> None:
        if not all(isfinite(float(v)) for v in (self.x, self.y, self.z)):
            raise ValueError("Vec3 values must be finite")

    def as_tuple(self) -> tuple[float, float, float]:
        return (float(self.x), float(self.y), float(self.z))


@dataclass(frozen=True)
class BodyLoadAccumulator:
    point_cross_vector: Vec3
    vector_sum: Vec3


def point_cross_vector(point: Vec3, vector: Vec3) -> Vec3:
    """Return the exact three-component cross product used by FUN_007baa70."""
    return Vec3(
        vector.z * point.y - vector.y * point.z,
        vector.x * point.z - vector.z * point.x,
        vector.y * point.x - vector.x * point.y,
    )


def apply_load(
    accumulator: BodyLoadAccumulator,
    point: Sequence[float],
    vector: Sequence[float],
) -> BodyLoadAccumulator:
    """Apply one FUN_007baa70 call to a neutral accumulator snapshot."""
    if len(point) != 3 or len(vector) != 3:
        raise ValueError("point and vector must each contain exactly three values")
    p = Vec3(*(float(v) for v in point))
    f = Vec3(*(float(v) for v in vector))
    cross = point_cross_vector(p, f)
    return BodyLoadAccumulator(
        point_cross_vector=Vec3(
            accumulator.point_cross_vector.x + cross.x,
            accumulator.point_cross_vector.y + cross.y,
            accumulator.point_cross_vector.z + cross.z,
        ),
        vector_sum=Vec3(
            accumulator.vector_sum.x + f.x,
            accumulator.vector_sum.y + f.y,
            accumulator.vector_sum.z + f.z,
        ),
    )


def zero_accumulator() -> BodyLoadAccumulator:
    return BodyLoadAccumulator(Vec3(0.0, 0.0, 0.0), Vec3(0.0, 0.0, 0.0))


def build_contract() -> dict:
    return {
        "format": FORMAT,
        "version": 1,
        "function": FUNCTION,
        "source_file": SOURCE_FILE,
        "source_line": SOURCE_LINE,
        "storage": {
            "point_cross_vector": [
                f"+0x{MOMENT_X_OFFSET:x}",
                f"+0x{MOMENT_Y_OFFSET:x}",
                f"+0x{MOMENT_Z_OFFSET:x}",
            ],
            "vector_sum": [
                f"+0x{LINEAR_X_OFFSET:x}",
                f"+0x{LINEAR_Y_OFFSET:x}",
                f"+0x{LINEAR_Z_OFFSET:x}",
            ],
        },
        "arithmetic": {
            "vector_update": "accumulator += param_2",
            "point_cross_vector": "param_1 x param_2",
            "cross_x": "param_1.y * param_2.z - param_1.z * param_2.y",
            "cross_y": "param_1.z * param_2.x - param_1.x * param_2.z",
            "cross_z": "param_1.x * param_2.y - param_1.y * param_2.x",
            "origin_adjustment": "none inside FUN_007baa70",
        },
        "caller_boundary": {
            "point": "application point supplied by caller",
            "vector": "response vector supplied by caller",
        },
        "related_variant": {
            "function": "FUN_007ba9e0",
            "difference": "subtracts body position from param_1 before cross product while updating the same accumulators",
        },
        "status": "instruction-stream exact accumulation boundary; physical naming of accumulators remains intentionally conservative",
    }


__all__ = [
    "FORMAT",
    "FUNCTION",
    "SOURCE_FILE",
    "SOURCE_LINE",
    "MOMENT_X_OFFSET",
    "MOMENT_Y_OFFSET",
    "MOMENT_Z_OFFSET",
    "LINEAR_X_OFFSET",
    "LINEAR_Y_OFFSET",
    "LINEAR_Z_OFFSET",
    "Vec3",
    "BodyLoadAccumulator",
    "point_cross_vector",
    "apply_load",
    "zero_accumulator",
    "build_contract",
]
