"""Body-frame compatibility layer using the canonical transform helpers."""
from __future__ import annotations

import struct
from typing import Any, Sequence

from matrix_vector_transform_runtime import (
    Matrix3x3,
    transform_fun_007aefb0,
    transform_fun_007af0a0,
)

FORMAT = "SHIFT.SDFBodyFrameRuntime/2"


def _f32(value: float | int) -> float:
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


def transform_vector_transpose(
    matrix: Matrix3x3,
    vector: Sequence[float | int],
) -> tuple[float, float, float]:
    """Mirror FUN_007aefb0 through the canonical helper."""
    return transform_fun_007aefb0(matrix, vector).as_tuple()


def prepare_body_frame_vector(
    matrix: Matrix3x3,
    body_vector: Sequence[float | int],
    scale: Sequence[float | int],
) -> dict[str, Any]:
    """Reproduce FUN_007ba7e0's transform-scale-transpose chain."""
    if len(scale) != 3:
        raise ValueError("scale must contain exactly three values")
    local = transform_fun_007af0a0(matrix, body_vector)
    sx, sy, sz = (_f32(value) for value in scale)
    scaled = (
        _f32(local.x * sx),
        _f32(local.y * sy),
        _f32(local.z * sz),
    )
    output = transform_fun_007aefb0(matrix, scaled)
    return {
        "format": FORMAT,
        "version": 2,
        "status": "computed",
        "ready": True,
        "input": {
            "body_vector": [float(value) for value in body_vector],
            "scale": [sx, sy, sz],
        },
        "local_vector": [local.x, local.y, local.z],
        "scaled_local_vector": list(scaled),
        "output_vector": list(output.as_tuple()),
        "source": {
            "frame_prepare": "FUN_007ba7e0",
            "forward_transform": "FUN_007af0a0",
            "transpose_transform": "FUN_007aefb0",
        },
        "runtime_output_offsets": ["+0x30", "+0x38", "+0x40"],
    }


def describe_sdf_body_frame_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 2,
        "status": "source-backed",
        "ready": True,
        "function": "FUN_007ba7e0",
        "forward_transform": {
            "function": "FUN_007af0a0",
            "matrix": "+0xd4",
            "input_vector": "+0x18",
            "temporary_output": "local_28/local_20/local_18",
        },
        "scale": {
            "source_offsets": ["+0x128", "+0x12c", "+0x130"],
            "operation": "component-wise multiply after forward transform",
        },
        "transpose_transform": {
            "function": "FUN_007aefb0",
            "matrix": "+0xd4",
            "input": "scaled temporary vector",
            "destination": ["+0x30", "+0x38", "+0x40"],
        },
        "composite": "M^T * diag(C) * M * body_vector",
        "canonical_helpers": "matrix_vector_transform_runtime.py",
        "float_behavior": [
            "forward-transform reads matrix/input as float32",
            "scale coefficients are float32",
            "transpose-transform casts scaled values through the canonical helper",
        ],
        "limitations": [
            "The matrix coordinate convention and physical meaning remain unnamed.",
        ],
    }
