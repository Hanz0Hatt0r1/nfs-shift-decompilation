"""Exact HINGE/HINGE matrix coupling from FUN_007bb250."""
from __future__ import annotations

from typing import Any, Sequence

from matrix_vector_transform_runtime import Matrix3x3, transform_vector_transpose

FORMAT = "SHIFT.SDFHingeMatrixCouplingRuntime/1"
SOURCE_LINE = 819302
SAMPLE_STRIDE = 0xA0


def _vec3(values: Sequence[float | int], *, name: str) -> tuple[float, float, float]:
    if len(values) != 3:
        raise ValueError(f"{name} must contain exactly three values")
    return float(values[0]), float(values[1]), float(values[2])


def _dot(left: Sequence[float], right: Sequence[float]) -> float:
    return float(left[0]) * float(right[0]) + float(left[1]) * float(right[1]) + float(left[2]) * float(right[2])


def transform_hinge_rows(
    body_frame: Matrix3x3,
    angular: Sequence[float | int],
    linear: Sequence[float | int],
) -> dict[str, list[float]]:
    """Mirror FUN_007bb250's two FUN_007aefb0 row transforms."""
    a = _vec3(angular, name="angular")
    b = _vec3(linear, name="linear")
    ta = transform_vector_transpose(body_frame, a)
    tb = transform_vector_transpose(body_frame, b)
    return {
        "angular": [ta[0], ta[1], ta[2]],
        "linear": [tb[0], tb[1], tb[2]],
    }


def evaluate_hinge_self_lower_block(
    body_frame: Matrix3x3,
    angular: Sequence[float | int],
    linear: Sequence[float | int],
) -> dict[str, Any]:
    """Return the three lower-triangle values written for one HINGE sample."""
    a = _vec3(angular, name="angular")
    b = _vec3(linear, name="linear")
    transformed = transform_hinge_rows(body_frame, a, b)
    ta = transformed["angular"]
    tb = transformed["linear"]
    return {
        "format": FORMAT,
        "version": 1,
        "status": "computed",
        "ready": True,
        "function": "FUN_007bb250",
        "source_line": SOURCE_LINE,
        "self_block": {
            "row_base_col_base": _dot(a, ta),
            "row_base_plus_1_col_base": _dot(a, tb),
            "row_base_plus_1_col_base_plus_1": _dot(b, tb),
        },
        "transformed_rows": transformed,
        "storage": {
            "row_base_col_base": "row_ptr[base][base]",
            "row_base_plus_1_col_base": "row_ptr[base+1][base]",
            "row_base_plus_1_col_base_plus_1": "row_ptr[base+1][base+1]",
        },
    }


def evaluate_hinge_pair_block(
    body_frame: Matrix3x3,
    *,
    outer_angular: Sequence[float | int],
    outer_linear: Sequence[float | int],
    inner_angular: Sequence[float | int],
    inner_linear: Sequence[float | int],
    outer_base: int,
    inner_base: int,
    same_side: bool,
) -> dict[str, Any]:
    """Return the exact 2x2 HINGE pair block and source storage orientation."""
    outer_a = _vec3(outer_angular, name="outer_angular")
    outer_b = _vec3(outer_linear, name="outer_linear")
    inner_a = _vec3(inner_angular, name="inner_angular")
    inner_b = _vec3(inner_linear, name="inner_linear")
    transformed = transform_hinge_rows(body_frame, outer_a, outer_b)
    ta = transformed["angular"]
    tb = transformed["linear"]

    d5 = _dot(inner_a, ta)
    d6 = _dot(inner_b, ta)
    d8 = _dot(inner_a, tb)
    d7 = _dot(inner_b, tb)
    sign = 1.0 if same_side else -1.0

    if inner_base < outer_base:
        # Source stores [[d5,d6],[d8,d7]] at rows outer/outer+1,
        # columns inner/inner+1.
        block = [
            [sign * d5, sign * d6],
            [sign * d8, sign * d7],
        ]
        storage_orientation = "outer_rows_by_inner_columns"
    else:
        # Source stores [[d5,d8],[d6,d7]] at rows inner/inner+1,
        # columns outer/outer+1.
        block = [
            [sign * d5, sign * d8],
            [sign * d6, sign * d7],
        ]
        storage_orientation = "inner_rows_by_outer_columns"

    return {
        "format": FORMAT,
        "version": 1,
        "status": "computed",
        "ready": True,
        "function": "FUN_007bb250",
        "source_line": SOURCE_LINE,
        "outer_base": int(outer_base),
        "inner_base": int(inner_base),
        "same_side": bool(same_side),
        "sign": sign,
        "raw_coefficients": {
            "d5": d5,
            "d6": d6,
            "d8": d8,
            "d7": d7,
        },
        "block": block,
        "storage_orientation": storage_orientation,
        "evidence": {
            "sample_stride": SAMPLE_STRIDE,
            "side_flag_offset": "+0x98",
            "scalar_base_offset": "+0x94",
            "matrix_pointer_table": "+0x158",
            "same_side_rule": "equal flags add; differing flags subtract",
        },
    }


def apply_hinge_pair_block(
    matrix: Sequence[Sequence[float | int]],
    *,
    row_base: int,
    col_base: int,
    block: Sequence[Sequence[float | int]],
) -> list[list[float]]:
    """Apply a 2x2 pair block to a scalar matrix at the supplied base indices."""
    if len(block) != 2 or any(len(row) != 2 for row in block):
        raise ValueError("HINGE pair block must be 2x2")
    out = [[float(value) for value in row] for row in matrix]
    for row_offset in range(2):
        for col_offset in range(2):
            row = int(row_base) + row_offset
            col = int(col_base) + col_offset
            if row < 0 or col < 0 or row >= len(out) or col >= len(out):
                raise ValueError("HINGE pair block index is outside matrix")
            out[row][col] += float(block[row_offset][col_offset])
    return out


def describe_hinge_matrix_coupling_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "source-backed",
        "ready": True,
        "function": "FUN_007bb250",
        "source_line": SOURCE_LINE,
        "sample_stride": SAMPLE_STRIDE,
        "scalar_base_offset": "+0x94",
        "side_flag_offset": "+0x98",
        "body_frame_helper": "FUN_007aefb0",
        "self_block": {
            "entries": [
                "[base,base] += A_i dot (M A_i)",
                "[base+1,base] += A_i dot (M B_i)",
                "[base+1,base+1] += B_i dot (M B_i)",
            ],
            "upper_off_diagonal": "not written by this helper",
        },
        "pair_block": {
            "d5": "A_j dot (M A_i)",
            "d6": "B_j dot (M A_i)",
            "d8": "A_j dot (M B_i)",
            "d7": "B_j dot (M B_i)",
            "same_side": "add",
            "different_side": "subtract",
            "orientation": {
                "inner_base < outer_base": "[[d5,d6],[d8,d7]]",
                "inner_base >= outer_base": "[[d5,d8],[d6,d7]]",
            },
        },
        "destination": "this +0x158 row-pointer table",
        "limitations": [
            "This phase covers HINGE/HINGE coupling inside FUN_007bb250; HINGE/BAR coupling is separate.",
        ],
    }


__all__ = [
    "FORMAT",
    "SOURCE_LINE",
    "transform_hinge_rows",
    "evaluate_hinge_self_lower_block",
    "evaluate_hinge_pair_block",
    "apply_hinge_pair_block",
    "describe_hinge_matrix_coupling_contract",
]
