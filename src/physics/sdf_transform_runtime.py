"""Compatibility adapter for the SDF transform helper pair.

The canonical implementations live in matrix_vector_transform_runtime.py.
This module keeps the Phase 428 SDF-facing names while binding them directly to
the retail machine-backed functions. Phase 687 upgrades the numeric contract to
preserve QWORD vector operands instead of the older decompiler-shaped f32 cast.
"""
from __future__ import annotations

from typing import Iterable, Sequence

from matrix_vector_transform_runtime import (
    FORMAT as CANONICAL_TRANSFORM_FORMAT,
    Matrix3x3,
    build_contract as build_canonical_transform_contract,
    transform_fun_007aefb0,
    transform_fun_007af0a0,
)

FORMAT = "SHIFT.SDFTransformRuntime/3"
MATRIX_BLOCK_BASE = 0xD4
MATRIX_FLOAT_OFFSETS = tuple(MATRIX_BLOCK_BASE + i * 4 for i in range(9))


def _mat9(values: Iterable[float]) -> Matrix3x3:
    value = tuple(float(v) for v in values)
    if len(value) != 9:
        raise ValueError("expected exactly nine matrix components")
    return Matrix3x3(*value)


def transform_forward(matrix: Sequence[float], vector: Sequence[float]) -> tuple[float, float, float]:
    """Legacy SDF adapter for the FUN_007aefb0 coefficient ordering."""
    return transform_fun_007aefb0(_mat9(matrix), vector).as_tuple()


def transform_transposed(matrix: Sequence[float], vector: Sequence[float]) -> tuple[float, float, float]:
    """Legacy SDF adapter for the FUN_007af0a0 coefficient ordering."""
    return transform_fun_007af0a0(_mat9(matrix), vector).as_tuple()


def build_matrix_block_contract() -> dict:
    return {
        "format": "SHIFT.BodyRotationMatrixBlock/2",
        "version": 2,
        "base_offset": MATRIX_BLOCK_BASE,
        "float_offsets": [hex(offset) for offset in MATRIX_FLOAT_OFFSETS],
        "layout": {
            "m00": hex(0xD4), "m01": hex(0xD8), "m02": hex(0xDC),
            "m10": hex(0xE0), "m11": hex(0xE4), "m12": hex(0xE8),
            "m20": hex(0xEC), "m21": hex(0xF0), "m22": hex(0xF4),
        },
        "canonical_source": "matrix_vector_transform_runtime.py",
        "status": "ready",
    }


def build_transform_helper_contract() -> dict:
    canonical = build_canonical_transform_contract()
    if canonical["format"] != CANONICAL_TRANSFORM_FORMAT:
        raise ValueError("canonical transform contract format mismatch")
    return {
        "format": FORMAT,
        "version": 3,
        "matrix_block": build_matrix_block_contract(),
        "canonical_transform_format": CANONICAL_TRANSFORM_FORMAT,
        "helpers": canonical["helpers"],
        "numeric_boundary": canonical["numeric_boundary"],
        "status": "ready",
        "limitations": [
            "No matrix coordinate convention or physical meaning is inferred.",
            "No translation component is part of these two SDF-facing helpers.",
            "Ambient retail x87 control-word state is not proven by this adapter.",
        ],
    }


__all__ = [
    "FORMAT", "MATRIX_BLOCK_BASE", "MATRIX_FLOAT_OFFSETS",
    "transform_forward", "transform_transposed",
    "build_matrix_block_contract", "build_transform_helper_contract",
]
