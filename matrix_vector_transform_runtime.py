"""Exact 3x3 float matrix × double-vector boundary for FUN_007af0a0."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence

FORMAT = "SHIFT.MatrixVectorTransformRuntime/1"
FUNCTION = "FUN_007af0a0"
SOURCE_FILE = "SHIFT.exe.c"
SOURCE_LINE = 810279

M00_OFFSET = 0x00
M01_OFFSET = 0x04
M02_OFFSET = 0x08
M10_OFFSET = 0x0C
M11_OFFSET = 0x10
M12_OFFSET = 0x14
M20_OFFSET = 0x18
M21_OFFSET = 0x1C
M22_OFFSET = 0x20


@dataclass(frozen=True)
class Matrix3x3:
    m00: float
    m01: float
    m02: float
    m10: float
    m11: float
    m12: float
    m20: float
    m21: float
    m22: float

    def __post_init__(self) -> None:
        if not all(isfinite(float(v)) for v in (
            self.m00, self.m01, self.m02, self.m10, self.m11,
            self.m12, self.m20, self.m21, self.m22,
        )):
            raise ValueError("matrix values must be finite")


@dataclass(frozen=True)
class Vec3:
    x: float
    y: float
    z: float

    def __post_init__(self) -> None:
        if not all(isfinite(float(v)) for v in (self.x, self.y, self.z)):
            raise ValueError("vector values must be finite")

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)


def _vec(values: Sequence[float]) -> Vec3:
    if len(values) != 3:
        raise ValueError("vector must contain exactly three values")
    return Vec3(*(float(v) for v in values))


def transform_vector(matrix: Matrix3x3, vector: Sequence[float]) -> Vec3:
    """Mirror FUN_007af0a0, including float32 input conversion."""
    v = _vec(vector)
    fx = float(v.x)
    fy = float(v.y)
    fz = float(v.z)
    return Vec3(
        matrix.m20 * fz + matrix.m00 * fx + matrix.m10 * fy,
        matrix.m21 * fz + matrix.m11 * fy + matrix.m01 * fx,
        matrix.m22 * fz + matrix.m12 * fy + matrix.m02 * fx,
    )


def build_contract() -> dict:
    return {
        "format": FORMAT,
        "version": 1,
        "function": FUNCTION,
        "source_file": SOURCE_FILE,
        "source_line": SOURCE_LINE,
        "matrix_float_offsets": {
            "row0": ["0x00", "0x04", "0x08"],
            "row1": ["0x0c", "0x10", "0x14"],
            "row2": ["0x18", "0x1c", "0x20"],
        },
        "input_conversion": "each double input component is cast to float32",
        "output_conversion": "each float result is converted back to double",
        "formula": {
            "x": "m20*z + m00*x + m10*y",
            "y": "m21*z + m11*y + m01*x",
            "z": "m22*z + m12*y + m02*x",
        },
        "usage": {
            "body_context": "body + 0xd4",
            "caller_examples": [
                "FUN_00755f80",
                "FUN_00758fc0",
                "FUN_00766510",
            ],
        },
        "status": "instruction-stream exact 3x3 transform boundary; matrix coordinate convention remains unnamed",
    }


__all__ = [
    "FORMAT", "FUNCTION", "SOURCE_FILE", "SOURCE_LINE",
    "M00_OFFSET", "M01_OFFSET", "M02_OFFSET", "M10_OFFSET",
    "M11_OFFSET", "M12_OFFSET", "M20_OFFSET", "M21_OFFSET", "M22_OFFSET",
    "Matrix3x3", "Vec3", "transform_vector", "build_contract",
]
