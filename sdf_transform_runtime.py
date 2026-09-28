"""Exact 3x3 transform helpers used by SHIFT SDF post-load code.

FUN_007aefb0 reads nine float values from a matrix block and performs standard
row-major matrix times vector multiplication. FUN_007af0a0 uses the transposed
matrix ordering. The implementation keeps the helper boundary independent from
any claim about wider body-transform semantics.
"""
from __future__ import annotations

import argparse
import json
from typing import Iterable, Sequence

FORMAT = "SHIFT.SDFTransformRuntime/1"
MATRIX_BLOCK_BASE = 0xD4
MATRIX_FLOAT_OFFSETS = tuple(MATRIX_BLOCK_BASE + i * 4 for i in range(9))


def _vec3(values: Iterable[float]) -> tuple[float, float, float]:
    value = tuple(float(v) for v in values)
    if len(value) != 3:
        raise ValueError("expected exactly three vector components")
    return value  # type: ignore[return-value]


def _mat9(values: Iterable[float]) -> tuple[float, ...]:
    value = tuple(float(v) for v in values)
    if len(value) != 9:
        raise ValueError("expected exactly nine matrix components")
    return value


def transform_forward(matrix: Sequence[float], vector: Sequence[float]) -> tuple[float, float, float]:
    """Reproduce FUN_007aefb0's row-major matrix-times-vector ordering."""
    m00, m01, m02, m10, m11, m12, m20, m21, m22 = _mat9(matrix)
    x, y, z = _vec3(vector)
    return (
        m02 * z + m00 * x + m01 * y,
        m12 * z + m11 * y + m10 * x,
        m22 * z + m21 * y + m20 * x,
    )


def transform_transposed(matrix: Sequence[float], vector: Sequence[float]) -> tuple[float, float, float]:
    """Reproduce FUN_007af0a0's transposed matrix ordering."""
    m00, m01, m02, m10, m11, m12, m20, m21, m22 = _mat9(matrix)
    x, y, z = _vec3(vector)
    return (
        m20 * z + m00 * x + m10 * y,
        m21 * z + m11 * y + m01 * x,
        m22 * z + m12 * y + m02 * x,
    )


def build_matrix_block_contract() -> dict:
    return {
        "format": "SHIFT.BodyRotationMatrixBlock/1",
        "version": 1,
        "base_offset": MATRIX_BLOCK_BASE,
        "float_offsets": [hex(offset) for offset in MATRIX_FLOAT_OFFSETS],
        "layout": {
            "m00": hex(0xD4),
            "m01": hex(0xD8),
            "m02": hex(0xDC),
            "m10": hex(0xE0),
            "m11": hex(0xE4),
            "m12": hex(0xE8),
            "m20": hex(0xEC),
            "m21": hex(0xF0),
            "m22": hex(0xF4),
        },
        "forward_helper": "FUN_007aefb0",
        "transpose_helper": "FUN_007af0a0",
        "status": "ready",
    }


def build_transform_helper_contract() -> dict:
    return {
        "format": FORMAT,
        "version": 1,
        "source": ".\\Source\\System\\SDF.cpp",
        "helpers": {
            "forward": {
                "function": "FUN_007aefb0",
                "input": "double[3]",
                "output": "double[3]",
                "matrix_source": "+0xd4 .. +0xf4 as nine float values",
            },
            "transposed": {
                "function": "FUN_007af0a0",
                "input": "double[3]",
                "output": "double[3]",
                "matrix_source": "+0xd4 .. +0xf4 as nine float values",
            },
        },
        "matrix_block": build_matrix_block_contract(),
        "numeric_boundary": {
            "input_components_are_cast_to_float": True,
            "matrix_components_are_float": True,
            "output_components_are_stored_as_double": True,
        },
        "status": "ready",
        "limitations": [
            "No assumption is made that the matrix is orthonormal outside contexts where retail code separately establishes that.",
            "No translation component is part of these two helpers.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit SHIFT SDF transform helper contracts.")
    parser.add_argument("--matrix", action="store_true")
    parser.add_argument("--helpers", action="store_true")
    args = parser.parse_args()
    if not (args.matrix or args.helpers):
        args.matrix = args.helpers = True
    payload = {}
    if args.matrix:
        payload["matrix"] = build_matrix_block_contract()
    if args.helpers:
        payload["helpers"] = build_transform_helper_contract()
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
