"""Exact BAR/BAR matrix coupling from FUN_007bb6c0."""
from __future__ import annotations

from typing import Any, Sequence

from matrix_vector_transform_runtime import Matrix3x3
from sdf_body_frame_runtime import transform_vector_transpose

FORMAT = "SHIFT.SDFBarMatrixCouplingRuntime/1"
SOURCE_LINE = 819471
SAMPLE_STRIDE = 0x60


def _vec3(values: Sequence[float | int], *, name: str) -> tuple[float, float, float]:
    if len(values) != 3:
        raise ValueError(f"{name} must contain exactly three values")
    return float(values[0]), float(values[1]), float(values[2])


def evaluate_bar_cross_frame(
    body_frame: Matrix3x3,
    point: Sequence[float | int],
    direction: Sequence[float | int],
) -> dict[str, list[float]]:
    """Build p x q and transform it through FUN_007aefb0."""
    px, py, pz = _vec3(point, name="point")
    qx, qy, qz = _vec3(direction, name="direction")
    cross = (
        py * qz - pz * qy,
        pz * qx - qz * px,
        qy * px - py * qx,
    )
    transformed = transform_vector_transpose(body_frame, cross)
    return {
        "cross": [cross[0], cross[1], cross[2]],
        "transformed": [transformed[0], transformed[1], transformed[2]],
    }


def evaluate_bar_self_coefficient(
    body_frame: Matrix3x3,
    *,
    point: Sequence[float | int],
    direction: Sequence[float | int],
    inverse_scalar: float | int,
) -> dict[str, Any]:
    """Evaluate BAR self scalar coefficient written by FUN_007bb6c0."""
    px, py, pz = _vec3(point, name="point")
    qx, qy, qz = _vec3(direction, name="direction")
    inv = float(inverse_scalar)
    transformed = evaluate_bar_cross_frame(body_frame, (px, py, pz), (qx, qy, qz))
    lx, ly, lz = transformed["transformed"]

    dx = qx * inv
    dy = qy * inv
    dz = qz * inv

    coefficient = (
        ((py * lx - px * ly) + dz) * qz
        + qy * ((px * lz - pz * lx) + dy)
        + qx * ((pz * ly - py * lz) + dx)
    )
    return {
        "format": FORMAT,
        "version": 1,
        "status": "computed",
        "ready": True,
        "function": "FUN_007bb6c0",
        "source_line": SOURCE_LINE,
        "scalar_coefficient": coefficient,
        "inverse_scalar_terms": [dx, dy, dz],
        "cross": transformed["cross"],
        "transformed_cross": transformed["transformed"],
        "storage": {
            "sample_stride": SAMPLE_STRIDE,
            "scalar_base_offset": "+0x30",
            "self_destination": "this +0x158 row-pointer table [base][base]",
        },
    }


def evaluate_bar_pair_coefficient(
    body_frame: Matrix3x3,
    *,
    outer_point: Sequence[float | int],
    outer_direction: Sequence[float | int],
    inner_point: Sequence[float | int],
    inner_direction: Sequence[float | int],
    inverse_scalar: float | int,
    outer_base: int,
    inner_base: int,
    same_side: bool,
) -> dict[str, Any]:
    """Evaluate a BAR/BAR pair scalar coupling coefficient."""
    ox, oy, oz = _vec3(outer_point, name="outer_point")
    qx, qy, qz = _vec3(outer_direction, name="outer_direction")
    ix, iy, iz = _vec3(inner_point, name="inner_point")
    iqx, iqy, iqz = _vec3(inner_direction, name="inner_direction")
    inv = float(inverse_scalar)

    transformed = evaluate_bar_cross_frame(
        body_frame,
        (ox, oy, oz),
        (qx, qy, qz),
    )
    lx, ly, lz = transformed["transformed"]
    dx = qx * inv
    dy = qy * inv
    dz = qz * inv

    coefficient = (
        iqy * ((lz * ix - lx * iz) + dy)
        + iqx * ((ly * iz - iy * lz) + dx)
        + iqz * ((lx * iy - ly * ix) + dz)
    )
    sign = 1.0 if same_side else -1.0

    if int(inner_base) < int(outer_base):
        storage = {"row": int(outer_base), "column": int(inner_base)}
    else:
        storage = {"row": int(inner_base), "column": int(outer_base)}

    return {
        "format": FORMAT,
        "version": 1,
        "status": "computed",
        "ready": True,
        "function": "FUN_007bb6c0",
        "source_line": SOURCE_LINE,
        "raw_coefficient": coefficient,
        "coefficient": sign * coefficient,
        "sign": sign,
        "same_side": bool(same_side),
        "storage": {
            "sample_stride": SAMPLE_STRIDE,
            "scalar_base_offset": "+0x30",
            "matrix_cell": storage,
        },
        "evidence": {
            "inner_point_offsets": ["+0x18", "+0x20", "+0x28"],
            "inner_direction_offsets": ["+0x40", "+0x48", "+0x50"],
            "outer_point_offsets": ["+0x18", "+0x20", "+0x28"],
            "outer_direction_offsets": ["+0x40", "+0x48", "+0x50"],
            "inverse_scalar": "+0x90",
            "cross_transform": "FUN_007aefb0(body +0xb0, outer p x outer q)",
            "side_rule": "equal flags add, differing flags subtract",
        },
    }


def apply_bar_scalar(
    matrix: Sequence[Sequence[float | int]],
    *,
    row: int,
    column: int,
    value: float | int,
) -> list[list[float]]:
    out = [[float(entry) for entry in line] for line in matrix]
    r = int(row)
    c = int(column)
    if r < 0 or c < 0 or r >= len(out) or c >= len(out):
        raise ValueError("BAR matrix cell is outside matrix")
    out[r][c] += float(value)
    return out


def describe_bar_matrix_coupling_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "source-backed",
        "ready": True,
        "function": "FUN_007bb6c0",
        "source_line": SOURCE_LINE,
        "sample_array": "+0x168",
        "sample_stride": SAMPLE_STRIDE,
        "scalar_base_offset": "+0x30",
        "side_flag_offset": "+0x34",
        "body_frame": "+0xb0",
        "inverse_scalar": "+0x90",
        "self": {
            "operation": "build p x q, transform through FUN_007aefb0, evaluate scalar coefficient",
            "destination": "row_ptr[base][base]",
        },
        "pair": {
            "operation": "evaluate inner BAR against transformed outer p x q",
            "same_side": "add",
            "different_side": "subtract",
            "storage": "lower-triangle cell using max(base_i,base_j), min(base_i,base_j)",
        },
        "limitations": [
            "This phase covers BAR/BAR coupling only. JOINT/BAR and HINGE/BAR coupling remain in FUN_007bbb80/FUN_007bb250.",
        ],
    }


__all__ = [
    "FORMAT",
    "SOURCE_LINE",
    "evaluate_bar_cross_frame",
    "evaluate_bar_self_coefficient",
    "evaluate_bar_pair_coefficient",
    "apply_bar_scalar",
    "describe_bar_matrix_coupling_contract",
]
