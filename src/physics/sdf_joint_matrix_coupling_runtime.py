"""Exact JOINT matrix coupling from FUN_007bbb80."""
from __future__ import annotations

from typing import Any, Sequence

from matrix_vector_transform_runtime import Matrix3x3
from sdf_body_frame_runtime import transform_vector_transpose

FORMAT = "SHIFT.SDFJointMatrixCouplingRuntime/1"
SOURCE_LINE = 819720
JOINT_STRIDE = 0x40
HINGE_STRIDE = 0xA0
BAR_STRIDE = 0x60


def _vec3(values: Sequence[float | int], *, name: str) -> tuple[float, float, float]:
    if len(values) != 3:
        raise ValueError(f"{name} must contain exactly three values")
    return float(values[0]), float(values[1]), float(values[2])


def derive_joint_tensor_terms(
    body_tensor: Sequence[Sequence[float | int]],
    joint_position: Sequence[float | int],
) -> dict[str, float]:
    """Evaluate the nine source intermediates built from body tensor and JOINT position."""
    if len(body_tensor) != 3 or any(len(row) != 3 for row in body_tensor):
        raise ValueError("body_tensor must be 3x3")
    x, y, z = _vec3(joint_position, name="joint_position")
    a = float(body_tensor[0][0])
    b = float(body_tensor[0][1])
    c = float(body_tensor[0][2])
    d = float(body_tensor[1][1])
    e = float(body_tensor[1][2])
    f = float(body_tensor[2][2])
    return {
        "d6": b * z - c * y,
        "d10": d * z - e * y,
        "d1": e * z - f * y,
        "d2": c * x - a * z,
        "d3": e * x - b * z,
        "d12": f * x - e * z,
        "d15": a * y - b * x,
        "d19": b * y - d * x,
        "d18": c * y - e * x,
    }


def evaluate_joint_self_block(
    body_tensor: Sequence[Sequence[float | int]],
    *,
    joint_position: Sequence[float | int],
    inverse_scalar: float | int,
) -> dict[str, Any]:
    """Evaluate the 3x3 lower-triangle JOINT self block."""
    x, y, z = _vec3(joint_position, name="joint_position")
    inv = float(inverse_scalar)
    t = derive_joint_tensor_terms(body_tensor, (x, y, z))
    d6, d10, d1 = t["d6"], t["d10"], t["d1"]
    d2, d3, d12 = t["d2"], t["d3"], t["d12"]
    d15, d19, d18 = t["d15"], t["d19"], t["d18"]

    d7 = z * d10 - y * d1 + inv
    d13 = z * d3 - y * d12
    d11 = x * d12 - z * d2 + inv
    d17 = z * d19 - y * d18
    d16 = x * d18 - z * d15
    d14 = y * d15 - x * d19 + inv

    return {
        "format": FORMAT,
        "version": 1,
        "status": "computed",
        "ready": True,
        "function": "FUN_007bbb80",
        "source_line": SOURCE_LINE,
        "block": [
            [d7, 0.0, 0.0],
            [d13, d11, 0.0],
            [d17, d16, d14],
        ],
        "lower_triangle": {
            "00": d7,
            "10": d13,
            "11": d11,
            "20": d17,
            "21": d16,
            "22": d14,
        },
        "intermediates": t,
        "inverse_scalar": inv,
        "storage": {
            "scalar_base_offset": "+0x30",
            "row_pointer_table": "+0x158",
            "operation": "add lower-triangle entries at [base+i][base+j]",
        },
    }


def evaluate_joint_joint_pair_block(
    body_tensor: Sequence[Sequence[float | int]],
    *,
    outer_position: Sequence[float | int],
    inner_position: Sequence[float | int],
    inverse_scalar: float | int,
    outer_base: int,
    inner_base: int,
    same_side: bool,
) -> dict[str, Any]:
    """Evaluate the exact 3x3 JOINT/JOINT pair block."""
    ox, oy, oz = _vec3(outer_position, name="outer_position")
    ix, iy, iz = _vec3(inner_position, name="inner_position")
    inv = float(inverse_scalar)
    t = derive_joint_tensor_terms(body_tensor, (ox, oy, oz))
    d6, d10, d1 = t["d6"], t["d10"], t["d1"]
    d2, d3, d12 = t["d2"], t["d3"], t["d12"]
    d15, d19, d18 = t["d15"], t["d19"], t["d18"]

    d7 = iz * d10 - iy * d1 + inv
    d13 = iz * d3 - iy * d12
    d11 = ix * d12 - iz * d2 + inv
    d17 = iz * d19 - iy * d18
    d16 = ix * d18 - iz * d15
    d14 = iy * d15 - ix * d19 + inv
    d9 = ix * d1 - iz * d6
    d8 = d6 * iy - ix * d10
    d20 = iy * d2 - ix * d3

    raw = [
        [d7, d9, d8],
        [d13, d11, d20],
        [d17, d16, d14],
    ]
    sign = 1.0 if same_side else -1.0

    if int(inner_base) < int(outer_base):
        block = [[sign * value for value in row] for row in raw]
        orientation = "outer_rows_by_inner_columns"
        cell = {"row_base": int(outer_base), "column_base": int(inner_base)}
    else:
        block = [
            [sign * raw[0][0], sign * raw[1][0], sign * raw[2][0]],
            [sign * raw[0][1], sign * raw[1][1], sign * raw[2][1]],
            [sign * raw[0][2], sign * raw[1][2], sign * raw[2][2]],
        ]
        orientation = "inner_rows_by_outer_columns"
        cell = {"row_base": int(inner_base), "column_base": int(outer_base)}

    return {
        "format": FORMAT,
        "version": 1,
        "status": "computed",
        "ready": True,
        "function": "FUN_007bbb80",
        "source_line": SOURCE_LINE,
        "raw_block": raw,
        "block": block,
        "sign": sign,
        "same_side": bool(same_side),
        "storage_orientation": orientation,
        "storage": {
            **cell,
            "scalar_base_offset": "+0x30",
            "row_pointer_table": "+0x158",
        },
        "coefficients": {
            "d7": d7,
            "d9": d9,
            "d8": d8,
            "d13": d13,
            "d11": d11,
            "d20": d20,
            "d17": d17,
            "d16": d16,
            "d14": d14,
        },
    }


def evaluate_joint_hinge_pair_block(
    body_tensor: Sequence[Sequence[float | int]],
    *,
    joint_position: Sequence[float | int],
    hinge_angular: Sequence[float | int],
    hinge_linear: Sequence[float | int],
    inverse_scalar: float | int,
    joint_base: int,
    hinge_base: int,
    same_side: bool,
) -> dict[str, Any]:
    """Evaluate the exact JOINT/HINGE 3x2 pair block."""
    inv = float(inverse_scalar)
    t = derive_joint_tensor_terms(body_tensor, joint_position)
    d6, d10, d1 = t["d6"], t["d10"], t["d1"]
    d2, d3, d12 = t["d2"], t["d3"], t["d12"]
    d15, d19, d18 = t["d15"], t["d19"], t["d18"]
    az, ay, ax = _vec3(hinge_angular, name="hinge_angular")[::-1]
    lz, ly, lx = _vec3(hinge_linear, name="hinge_linear")[::-1]

    d7 = az * d1 + ay * d10 + ax * d6
    d14 = az * d12 + ax * d2 + ay * d3
    d17 = az * d18 + ax * d15 + ay * d19
    d11 = lz * d1 + ly * d10 + lx * d6
    d13 = lz * d12 + lx * d2 + ly * d3
    d16 = lz * d18 + lx * d15 + ly * d19

    raw = [
        [d7, d11],
        [d14, d13],
        [d17, d16],
    ]
    sign = 1.0 if same_side else -1.0
    if int(hinge_base) < int(joint_base):
        block = [[sign * value for value in row] for row in raw]
        orientation = "joint_rows_by_hinge_columns"
        cell = {"row_base": int(joint_base), "column_base": int(hinge_base)}
    else:
        block = [
            [sign * raw[0][0], sign * raw[1][0], sign * raw[2][0]],
            [sign * raw[0][1], sign * raw[1][1], sign * raw[2][1]],
        ]
        orientation = "hinge_rows_by_joint_columns"
        cell = {"row_base": int(hinge_base), "column_base": int(joint_base)}

    return {
        "format": FORMAT,
        "version": 1,
        "status": "computed",
        "ready": True,
        "function": "FUN_007bbb80",
        "source_line": SOURCE_LINE,
        "raw_block": raw,
        "block": block,
        "sign": sign,
        "same_side": bool(same_side),
        "storage_orientation": orientation,
        "storage": {**cell, "scalar_base_offset": "+0x30", "row_pointer_table": "+0x158"},
        "coefficients": {"d7": d7, "d11": d11, "d14": d14, "d13": d13, "d17": d17, "d16": d16},
        "sample_strides": {"joint": JOINT_STRIDE, "hinge": HINGE_STRIDE},
    }


def evaluate_joint_bar_pair_block(
    body_tensor: Sequence[Sequence[float | int]],
    *,
    joint_position: Sequence[float | int],
    bar_point: Sequence[float | int],
    bar_direction: Sequence[float | int],
    inverse_scalar: float | int,
    joint_base: int,
    bar_base: int,
    same_side: bool,
) -> dict[str, Any]:
    """Evaluate the exact JOINT/BAR 3x1 pair block."""
    _, _, _ = _vec3(joint_position, name="joint_position")
    px, py, pz = _vec3(bar_point, name="bar_point")
    qx, qy, qz = _vec3(bar_direction, name="bar_direction")
    inv = float(inverse_scalar)
    t = derive_joint_tensor_terms(body_tensor, joint_position)
    d6, d10, d1 = t["d6"], t["d10"], t["d1"]
    d2, d3, d12 = t["d2"], t["d3"], t["d12"]
    d15, d19, d18 = t["d15"], t["d19"], t["d18"]

    d7 = (
        (d6 * py - px * d10) * qz
        + (pz * d10 - d1 * py + inv) * qx
        + qy * (px * d1 - pz * d6)
    )
    d11 = (
        (pz * d3 - d12 * py) * qx
        + qy * (px * d12 - pz * d2 + inv)
        + qz * (d2 * py - px * d3)
    )
    d13 = (
        qz * (d15 * py - px * d19 + inv)
        + (pz * d19 - d18 * py) * qx
        + qy * (px * d18 - pz * d15)
    )
    raw = [d7, d11, d13]
    sign = 1.0 if same_side else -1.0

    if int(bar_base) < int(joint_base):
        block = [[sign * d7], [sign * d11], [sign * d13]]
        orientation = "joint_rows_by_bar_column"
        cell = {"row_base": int(joint_base), "column_base": int(bar_base)}
    else:
        block = [[sign * d7, sign * d11, sign * d13]]
        orientation = "bar_row_by_joint_columns"
        cell = {"row_base": int(bar_base), "column_base": int(joint_base)}

    return {
        "format": FORMAT,
        "version": 1,
        "status": "computed",
        "ready": True,
        "function": "FUN_007bbb80",
        "source_line": SOURCE_LINE,
        "raw_block": raw,
        "block": block,
        "sign": sign,
        "same_side": bool(same_side),
        "storage_orientation": orientation,
        "storage": {**cell, "scalar_base_offset": "+0x30", "row_pointer_table": "+0x158"},
        "sample_strides": {"joint": JOINT_STRIDE, "bar": BAR_STRIDE},
    }


def apply_lower_triangle_block(
    matrix: Sequence[Sequence[float | int]],
    *,
    row_base: int,
    column_base: int,
    block: Sequence[Sequence[float | int]],
) -> list[list[float]]:
    if not block or any(not row for row in block):
        raise ValueError("block must not be empty")
    rows = len(matrix)
    cols = len(matrix[0]) if matrix else 0
    out = [[float(value) for value in row] for row in matrix]
    for r_off, row in enumerate(block):
        for c_off, value in enumerate(row):
            r = int(row_base) + r_off
            c = int(column_base) + c_off
            if r < 0 or c < 0 or r >= rows or c >= cols:
                raise ValueError("block is outside matrix")
            out[r][c] += float(value)
    return out


def describe_joint_matrix_coupling_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "source-backed",
        "ready": True,
        "function": "FUN_007bbb80",
        "source_line": SOURCE_LINE,
        "joint": {
            "sample_array": "+0x160",
            "sample_stride": JOINT_STRIDE,
            "scalar_base_offset": "+0x30",
            "side_flag_offset": "+0x34",
            "self_block": "3x3 lower triangle",
        },
        "mixed": {
            "hinge": {
                "sample_stride": HINGE_STRIDE,
                "scalar_base_offset": "+0x94",
                "side_flag_offset": "+0x98",
                "block_shape": "3x2",
            },
            "bar": {
                "sample_stride": BAR_STRIDE,
                "scalar_base_offset": "+0x30",
                "side_flag_offset": "+0x34",
                "block_shape": "3x1",
            },
        },
        "matrix_storage": {
            "row_pointer_table": "+0x158",
            "orientation": "lower triangle, using max base as row and min base as column",
        },
        "sign_rule": "equal side flags add; differing flags subtract",
        "body_tensor": "+0xb0",
        "inverse_scalar": "+0x90",
        "limitations": [
            "This phase covers FUN_007bbb80 JOINT self and JOINT/HINGE/JOINT/BAR blocks; HINGE/HINGE and BAR/BAR remain in separate phase modules.",
        ],
    }
