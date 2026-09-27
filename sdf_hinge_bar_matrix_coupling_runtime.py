"""Exact HINGE/BAR matrix coupling from FUN_007bb250."""
from __future__ import annotations

from typing import Any, Sequence

from matrix_vector_transform_runtime import Matrix3x3
from sdf_hinge_matrix_coupling_runtime import transform_hinge_rows

FORMAT = "SHIFT.SDFHingeBarMatrixCouplingRuntime/1"
SOURCE_LINE = 819302
HINGE_STRIDE = 0xA0
BAR_STRIDE = 0x60


def _vec3(values: Sequence[float | int], *, name: str) -> tuple[float, float, float]:
    if len(values) != 3:
        raise ValueError(f"{name} must contain exactly three values")
    return float(values[0]), float(values[1]), float(values[2])


def evaluate_hinge_bar_pair(
    body_frame: Matrix3x3,
    *,
    hinge_angular: Sequence[float | int],
    hinge_linear: Sequence[float | int],
    bar_point: Sequence[float | int],
    bar_direction: Sequence[float | int],
    hinge_base: int,
    bar_base: int,
    same_side: bool,
) -> dict[str, Any]:
    """Evaluate the exact HINGE/BAR 2x1 mixed block."""
    hx, hy, hz = _vec3(hinge_angular, name="hinge_angular")
    lx, ly, lz = _vec3(hinge_linear, name="hinge_linear")
    px, py, pz = _vec3(bar_point, name="bar_point")
    qx, qy, qz = _vec3(bar_direction, name="bar_direction")

    transformed = transform_hinge_rows(body_frame, (hx, hy, hz), (lx, ly, lz))
    a0, a1, a2 = transformed["angular"]
    b0, b1, b2 = transformed["linear"]

    d5 = (
        (a0 * py - px * a1) * qz
        + (a2 * px - pz * a0) * qy
        + qx * (pz * a1 - a2 * py)
    )
    d6 = (
        (b0 * py - px * b1) * qz
        + (b2 * px - pz * b0) * qy
        + qx * (pz * b1 - b2 * py)
    )
    sign = 1.0 if same_side else -1.0

    if int(bar_base) < int(hinge_base):
        block = [[sign * d5], [sign * d6]]
        orientation = "hinge_rows_by_bar_column"
        storage = {"row_base": int(hinge_base), "column_base": int(bar_base)}
    else:
        block = [[sign * d5, sign * d6]]
        orientation = "bar_row_by_hinge_columns"
        storage = {"row_base": int(bar_base), "column_base": int(hinge_base)}

    return {
        "format": FORMAT,
        "version": 1,
        "status": "computed",
        "ready": True,
        "function": "FUN_007bb250",
        "source_line": SOURCE_LINE,
        "raw_coefficients": {"d5": d5, "d6": d6},
        "block": block,
        "sign": sign,
        "same_side": bool(same_side),
        "storage_orientation": orientation,
        "storage": {
            **storage,
            "row_pointer_table": "+0x158",
            "scalar_base": {"hinge": "+0x94", "bar": "+0x30"},
        },
        "sample_strides": {
            "hinge": HINGE_STRIDE,
            "bar": BAR_STRIDE,
        },
    }


def apply_hinge_bar_block(
    matrix: Sequence[Sequence[float | int]],
    *,
    row_base: int,
    column_base: int,
    block: Sequence[Sequence[float | int]],
) -> list[list[float]]:
    if not block or any(not row for row in block):
        raise ValueError("block must not be empty")
    out = [[float(value) for value in row] for row in matrix]
    for r_offset, row in enumerate(block):
        for c_offset, value in enumerate(row):
            r = int(row_base) + r_offset
            c = int(column_base) + c_offset
            if r < 0 or c < 0 or r >= len(out) or c >= len(out):
                raise ValueError("HINGE/BAR block is outside matrix")
            out[r][c] += float(value)
    return out


def describe_hinge_bar_matrix_coupling_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "source-backed",
        "ready": True,
        "function": "FUN_007bb250",
        "source_line": SOURCE_LINE,
        "hinge": {
            "sample_stride": HINGE_STRIDE,
            "angular_offset": "+0x48",
            "linear_offset": "+0x60",
            "scalar_base": "+0x94",
            "side_flag": "+0x98",
        },
        "bar": {
            "sample_stride": BAR_STRIDE,
            "point_offset": "+0x18",
            "direction_offset": "+0x40",
            "scalar_base": "+0x30",
            "side_flag": "+0x34",
        },
        "block": {
            "shape": "2x1",
            "d5": "hinge.angular_transformed × bar point/direction scalar expression",
            "d6": "hinge.linear_transformed × bar point/direction scalar expression",
            "same_side": "add",
            "different_side": "subtract",
            "orientation": "max scalar base becomes row, min becomes column",
        },
        "body_frame_helper": "FUN_007aefb0",
        "matrix_storage": "+0x158 row-pointer table",
        "limitations": [
            "This phase covers the HINGE/BAR mixed block only.",
        ],
    }


__all__ = [
    "FORMAT",
    "SOURCE_LINE",
    "evaluate_hinge_bar_pair",
    "apply_hinge_bar_block",
    "describe_hinge_bar_matrix_coupling_contract",
]
