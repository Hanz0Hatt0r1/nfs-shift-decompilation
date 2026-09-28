"""Exact 3x3 float-matrix transform boundaries used by SHIFT.

The retail helpers FUN_007af0a0 and FUN_007aefb0 both consume the same nine
float values. The public API names each helper by its retail function name so
callers do not have to guess the matrix coordinate convention.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence

FORMAT = "SHIFT.MatrixVectorTransformRuntime/2"
SOURCE_FILE = "SHIFT.exe.c"
FUN_007AF0A0_LINE = 810279
FUN_007AEFB0_LINE = 810220

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

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)


def _vec(values: Sequence[float]) -> Vec3:
    if len(values) != 3:
        raise ValueError("vector must contain exactly three values")
    return Vec3(*(float(v) for v in values))


def transform_fun_007af0a0(matrix: Matrix3x3, vector: Sequence[float]) -> Vec3:
    """Exact coefficient ordering emitted by FUN_007af0a0."""
    v = _vec(vector)
    return Vec3(
        matrix.m20 * v.z + matrix.m00 * v.x + matrix.m10 * v.y,
        matrix.m21 * v.z + matrix.m11 * v.y + matrix.m01 * v.x,
        matrix.m22 * v.z + matrix.m12 * v.y + matrix.m02 * v.x,
    )


def transform_fun_007aefb0(matrix: Matrix3x3, vector: Sequence[float]) -> Vec3:
    """Exact coefficient ordering emitted by FUN_007aefb0."""
    v = _vec(vector)
    return Vec3(
        matrix.m02 * v.z + matrix.m00 * v.x + matrix.m01 * v.y,
        matrix.m12 * v.z + matrix.m11 * v.y + matrix.m10 * v.x,
        matrix.m22 * v.z + matrix.m21 * v.y + matrix.m20 * v.x,
    )


# Backward-compatible Phase 396/428 name. This preserves the established
# FUN_007af0a0 call contract without introducing a second implementation.
transform_vector = transform_fun_007af0a0


def build_contract() -> dict:
    return {
        "format": FORMAT,
        "version": 2,
        "source_file": SOURCE_FILE,
        "matrix_float_offsets": {
            "row0": ["0x00", "0x04", "0x08"],
            "row1": ["0x0c", "0x10", "0x14"],
            "row2": ["0x18", "0x1c", "0x20"],
        },
        "helpers": {
            "FUN_007af0a0": {
                "source_line": FUN_007AF0A0_LINE,
                "formula": {
                    "x": "m20*z + m00*x + m10*y",
                    "y": "m21*z + m11*y + m01*x",
                    "z": "m22*z + m12*y + m02*x",
                },
                "canonical_api": "transform_fun_007af0a0",
            },
            "FUN_007aefb0": {
                "source_line": FUN_007AEFB0_LINE,
                "formula": {
                    "x": "m02*z + m00*x + m01*y",
                    "y": "m12*z + m11*y + m10*x",
                    "z": "m22*z + m21*y + m20*x",
                },
                "canonical_api": "transform_fun_007aefb0",
            },
        },
        "usage": {
            "body_context": "body + 0xd4",
        },
        "numeric_boundary": {
            "input_components_are_cast_to_float": True,
            "matrix_components_are_float": True,
            "output_components_are_stored_as_double": True,
        },
        "status": "instruction-stream exact helper pair; matrix coordinate convention remains unnamed",
    }


__all__ = [
    "FORMAT", "Matrix3x3", "Vec3", "transform_fun_007af0a0",
    "transform_fun_007aefb0", "transform_vector", "build_contract",
]
