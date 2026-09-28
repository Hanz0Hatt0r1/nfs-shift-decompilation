"""Source-backed 1.0 scalar-matrix seed writes from FUN_007ba2b0."""
from __future__ import annotations

import hashlib
import struct
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.SDFConstraintSeedWriteRuntime/1"
SOURCE_LINE = 818608


def _validate_matrix(matrix: Sequence[Sequence[float | int]]) -> int:
    n = len(matrix)
    if any(len(row) != n for row in matrix):
        raise ValueError("matrix must be square")
    return n


def enumerate_seed_writes(
    matrix: Sequence[Sequence[float | int]],
) -> list[dict[str, Any]]:
    """Enumerate the non-zero 1.0 matrix cells represented by FUN_007ba2b0."""
    n = _validate_matrix(matrix)
    writes: list[dict[str, Any]] = []
    for row in range(n):
        for column in range(n):
            value = float(matrix[row][column])
            if value == 0.0:
                continue
            if value != 1.0:
                raise ValueError(
                    "seed matrix must contain only 0.0 and 1.0 values"
                )
            writes.append({
                "row": row,
                "column": column,
                "value": 1.0,
            })
    return writes


def materialize_seed_matrix(
    matrix: Sequence[Sequence[float | int]],
) -> dict[str, Any]:
    """Normalize a scalar connectivity matrix to the retail 1.0 seed domain."""
    n = _validate_matrix(matrix)
    writes = enumerate_seed_writes(matrix)
    normalized = [[0.0 for _ in range(n)] for _ in range(n)]
    for write in writes:
        normalized[int(write["row"])][int(write["column"])] = 1.0

    diagonal_one = all(normalized[index][index] == 1.0 for index in range(n))
    symmetric = all(
        normalized[row][column] == normalized[column][row]
        for row in range(n)
        for column in range(n)
    )
    row_nonzero_counts = [sum(1 for value in row if value != 0.0) for row in normalized]
    pool = bytes(
        int(value)
        for row in normalized
        for value in row
    )
    return {
        "format": FORMAT,
        "version": 1,
        "status": "materialized",
        "ready": True,
        "function": "FUN_007ba2b0",
        "source_line": SOURCE_LINE,
        "scalar_count": n,
        "matrix": normalized,
        "writes": writes,
        "write_count": len(writes),
        "diagonal_one": diagonal_one,
        "symmetric": symmetric,
        "row_nonzero_counts": row_nonzero_counts,
        "matrix_bit_hash_sha256": hashlib.sha256(pool).hexdigest(),
        "storage": {
            "matrix_pool": "+0x154",
            "row_pointers": "+0x158",
            "row_indices": "+0x15c",
            "cell_rule": "row_ptr[row][column] = 1.0",
        },
        "evidence": {
            "source_function": "FUN_007ba2b0",
            "seed_value": 1.0,
            "self_block_rule": "every scalar block seeds its Cartesian product",
            "shared_block_rule": "every endpoint-sharing pair seeds both cross-products",
        },
    }


def apply_seed_writes(
    matrix: Sequence[Sequence[float | int]],
    writes: Sequence[Mapping[str, Any]],
) -> list[list[float]]:
    """Apply materialized 1.0 writes additively to an existing matrix."""
    n = _validate_matrix(matrix)
    out = [[float(value) for value in row] for row in matrix]
    for write in writes:
        row = int(write["row"])
        column = int(write["column"])
        value = float(write["value"])
        if value != 1.0:
            raise ValueError("FUN_007ba2b0 seed write value must be 1.0")
        if row < 0 or column < 0 or row >= n or column >= n:
            raise ValueError("seed write is outside matrix")
        out[row][column] += value
    return out


def describe_seed_write_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "source-backed",
        "ready": True,
        "function": "FUN_007ba2b0",
        "source_line": SOURCE_LINE,
        "value": 1.0,
        "operation": "seed scalar matrix cells with 1.0 across self/shared scalar blocks",
        "storage": {
            "matrix_pool": "+0x154",
            "row_pointers": "+0x158",
            "row_indices": "+0x15c",
        },
        "symmetry": "both cross-products are written",
        "diagonal": "self scalar blocks are fully seeded",
        "remaining_boundary": "FUN_007b2210 may later replace selected rows/columns with identity constraints",
    }


__all__ = [
    "FORMAT",
    "SOURCE_LINE",
    "enumerate_seed_writes",
    "materialize_seed_matrix",
    "apply_seed_writes",
    "describe_seed_write_contract",
]
