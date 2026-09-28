"""Source-backed body tensor construction from FUN_007ba630."""
from __future__ import annotations

import struct
from typing import Any, Sequence

FORMAT = "SHIFT.SDFBodyTensorRuntime/1"

SOURCE_DIAGONAL_OFFSETS = ["+0x138", "+0x140", "+0x148"]
SOURCE_BASIS_OFFSETS = [
    ["+0xd4", "+0xd8", "+0xdc"],
    ["+0xe0", "+0xe4", "+0xe8"],
    ["+0xec", "+0xf0", "+0xf4"],
]
RUNTIME_TENSOR_OFFSETS = [
    ["+0xb0", "+0xb4", "+0xb8"],
    ["+0xbc", "+0xc0", "+0xc4"],
    ["+0xc8", "+0xcc", "+0xd0"],
]


def _f32(value: float | int) -> float:
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


def _matrix3(values: Sequence[Sequence[float | int]]) -> list[list[float]]:
    if len(values) != 3 or any(len(row) != 3 for row in values):
        raise ValueError("matrix must be 3x3")
    return [[_f32(value) for value in row] for row in values]


def build_symmetric_body_tensor(
    diagonal: Sequence[float | int],
    basis: Sequence[Sequence[float | int]],
) -> dict[str, Any]:
    """Reproduce FUN_007ba630 as B * diag(D) * B^T with retail float inputs."""
    if len(diagonal) != 3:
        raise ValueError("diagonal must contain exactly 3 values")
    d0, d1, d2 = (_f32(value) for value in diagonal)
    b = _matrix3(basis)

    matrix = []
    for row in range(3):
        matrix.append([
            _f32(
                b[row][0] * b[column][0] * d0
                + b[row][1] * b[column][1] * d1
                + b[row][2] * b[column][2] * d2
            )
            for column in range(3)
        ])

    matrix[1][0] = matrix[0][1]
    matrix[2][0] = matrix[0][2]
    matrix[2][1] = matrix[1][2]

    return {
        "format": FORMAT,
        "version": 1,
        "status": "computed",
        "ready": True,
        "diagonal": [d0, d1, d2],
        "basis": b,
        "matrix": matrix,
        "source_offsets": {
            "diagonal": SOURCE_DIAGONAL_OFFSETS,
            "basis": SOURCE_BASIS_OFFSETS,
        },
        "runtime_offsets": RUNTIME_TENSOR_OFFSETS,
        "evidence": {
            "function": "FUN_007ba630",
            "operation": "basis * diag(diagonal) * transpose(basis)",
            "storage_pattern": "symmetric 3x3 tensor",
            "float_behavior": "source coefficients are read as float32",
        },
    }


def describe_sdf_body_tensor_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "source-backed",
        "ready": True,
        "function": "FUN_007ba630",
        "source_diagonal_offsets": SOURCE_DIAGONAL_OFFSETS,
        "source_basis_offsets": SOURCE_BASIS_OFFSETS,
        "runtime_tensor_offsets": RUNTIME_TENSOR_OFFSETS,
        "symmetry": [
            "runtime +0xbc mirrors +0xb4",
            "runtime +0xc8 mirrors +0xb8",
            "runtime +0xcc mirrors +0xc4",
        ],
        "operation": "basis * diag(diagonal) * transpose(basis)",
        "float_behavior": "diagonal and basis values are consumed as float32",
        "related_initialization": {
            "function": "FUN_007ba860",
            "inverse_diagonal_storage": ["+0x138", "+0x140", "+0x148"],
            "inverse_source": ["+0x128", "+0x12c", "+0x130"],
        },
        "limitations": [
            "The tensor is kept as a raw symmetric matrix; no physical inertia label is assigned.",
            "The basis matrix's coordinate-system semantics remain source-opaque.",
        ],
    }
