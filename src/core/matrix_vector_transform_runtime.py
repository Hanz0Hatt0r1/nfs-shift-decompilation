"""Machine-backed 3x3 float-matrix transform boundaries used by SHIFT.

The retail helpers FUN_007aefb0, FUN_007af0a0 and FUN_007af010 consume float32
matrix coefficients, but the x86 instruction stream multiplies them by QWORD
(double) vector/scalar operands.  Earlier source-shaped contracts incorrectly
inserted an f64 -> f32 input cast because the decompiler rendered those products
as `(float)param`.  Phase 687 follows the machine operands and operation order.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence

FORMAT = "SHIFT.MatrixVectorTransformRuntime/3"
SOURCE_FILE = "SHIFT.exe.c"
FUN_007AEFB0_LINE = 810220
FUN_007AF010_LINE = 810237
FUN_007AF0A0_LINE = 810279

FUN_007AEFB0_SHA256 = "76c52235cce08d3ec131d43e1b62cda623ac8528944e44f902846a0a71b14f29"
FUN_007AF010_SHA256 = "f3256201dee28b97260576ee14c522e236a44d1808516ed8e42efd2e2e2e8324"
FUN_007AF0A0_SHA256 = "8cd039935dbbe493db7742f7af1859d9abcc7d9c40f212c3f2fa331e992c52cc"

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
    result = Vec3(*(float(v) for v in values))
    if not all(isfinite(v) for v in result.as_tuple()):
        raise ValueError("vector values must be finite")
    return result


def _mul_add3(
    c0: float,
    v0: float,
    c1: float,
    v1: float,
    c2: float,
    v2: float,
) -> float:
    """Preserve the retail x87 multiply/add ordering at Python-double precision."""
    acc = float(c0) * float(v0)
    acc = acc + float(c1) * float(v1)
    acc = acc + float(c2) * float(v2)
    if not isfinite(acc):
        raise ValueError("transform result is non-finite")
    return acc


def transform_fun_007af0a0(matrix: Matrix3x3, vector: Sequence[float]) -> Vec3:
    """FUN_007af0a0 QWORD-input transform in retail instruction order."""
    v = _vec(vector)
    return Vec3(
        _mul_add3(matrix.m10, v.y, matrix.m00, v.x, matrix.m20, v.z),
        _mul_add3(matrix.m01, v.x, matrix.m11, v.y, matrix.m21, v.z),
        _mul_add3(matrix.m02, v.x, matrix.m12, v.y, matrix.m22, v.z),
    )


def transform_fun_007aefb0(matrix: Matrix3x3, vector: Sequence[float]) -> Vec3:
    """FUN_007aefb0 QWORD-input transform in retail instruction order."""
    v = _vec(vector)
    return Vec3(
        _mul_add3(matrix.m01, v.y, matrix.m00, v.x, matrix.m02, v.z),
        _mul_add3(matrix.m10, v.x, matrix.m11, v.y, matrix.m12, v.z),
        _mul_add3(matrix.m20, v.x, matrix.m21, v.y, matrix.m22, v.z),
    )


def transform_fun_007af010(matrix: Matrix3x3, scalar: float) -> Vec3:
    """Scale the first matrix column by the retail QWORD scalar operand."""
    scalar = float(scalar)
    if not isfinite(scalar):
        raise ValueError("scalar must be finite")
    result = Vec3(
        float(matrix.m00) * scalar,
        float(matrix.m10) * scalar,
        float(matrix.m20) * scalar,
    )
    if not all(isfinite(v) for v in result.as_tuple()):
        raise ValueError("FUN_007af010 result is non-finite")
    return result


# Backward-compatible Phase 396/428 name.
transform_vector = transform_fun_007af0a0


def build_contract() -> dict:
    return {
        "format": FORMAT,
        "version": 3,
        "source_file": SOURCE_FILE,
        "matrix_float_offsets": {
            "row0": ["0x00", "0x04", "0x08"],
            "row1": ["0x0c", "0x10", "0x14"],
            "row2": ["0x18", "0x1c", "0x20"],
        },
        "helpers": {
            "FUN_007aefb0": {
                "source_line": FUN_007AEFB0_LINE,
                "address_range": ["0x007aefb0", "0x007af003"],
                "sha256": FUN_007AEFB0_SHA256,
                "machine_formula_order": {
                    "x": "m01*y + m00*x + m02*z",
                    "y": "m10*x + m11*y + m12*z",
                    "z": "m20*x + m21*y + m22*z",
                },
                "canonical_api": "transform_fun_007aefb0",
            },
            "FUN_007af010": {
                "source_line": FUN_007AF010_LINE,
                "address_range": ["0x007af010", "0x007af033"],
                "sha256": FUN_007AF010_SHA256,
                "machine_formula_order": {
                    "x": "m00*scalar",
                    "y": "m10*scalar",
                    "z": "m20*scalar",
                },
                "canonical_api": "transform_fun_007af010",
            },
            "FUN_007af0a0": {
                "source_line": FUN_007AF0A0_LINE,
                "address_range": ["0x007af0a0", "0x007af0f3"],
                "sha256": FUN_007AF0A0_SHA256,
                "machine_formula_order": {
                    "x": "m10*y + m00*x + m20*z",
                    "y": "m01*x + m11*y + m21*z",
                    "z": "m02*x + m12*y + m22*z",
                },
                "canonical_api": "transform_fun_007af0a0",
            },
        },
        "usage": {"body_context": "body + 0xd4"},
        "input_conversion": "QWORD vector/scalar operands are preserved as float64; matrix operands are float32",
        "numeric_boundary": {
            "input_components_are_cast_to_float": False,
            "machine_vector_operand_width_bits": 64,
            "matrix_component_width_bits": 32,
            "output_component_width_bits": 64,
            "x87_extended_intermediates": True,
            "python_oracle_models_extended_intermediates_exactly": False,
        },
        "status": (
            "machine-backed operand widths and operation order; Python oracle uses binary64 "
            "intermediates while native Phase 687 models x87 intermediates with long double"
        ),
    }


__all__ = [
    "FORMAT", "Matrix3x3", "Vec3", "transform_fun_007af0a0",
    "transform_fun_007aefb0", "transform_fun_007af010", "transform_vector",
    "build_contract",
]
