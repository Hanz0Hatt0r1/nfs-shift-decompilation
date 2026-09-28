"""Exact retail storage-level identity reset from FUN_007b2210."""
from __future__ import annotations

from typing import Any, Sequence

FORMAT = "SHIFT.SDFBuiltinIdentityResetRuntime/1"
SOURCE_LINE = 812551


def apply_identity_reset_to_row_storage(
    matrix_pool: Sequence[float | int],
    *,
    scalar_count: int,
    row_indices: Sequence[int],
    node: int,
    rhs: Sequence[float | int],
) -> dict[str, Any]:
    """Apply the retail row/column reset through the row-pointer/index layout."""
    n = int(scalar_count)
    target = int(node)
    if n < 0:
        raise ValueError("scalar_count must be non-negative")
    if len(row_indices) != n:
        raise ValueError("row_indices length must equal scalar_count")
    if len(rhs) != n:
        raise ValueError("rhs length must equal scalar_count")
    if target < 0 or target >= n:
        raise ValueError("reset node is outside solver scalar domain")
    if len(matrix_pool) < n * n:
        raise ValueError("matrix_pool is shorter than scalar_count^2")

    indices = [int(value) for value in row_indices]
    out_pool = [float(value) for value in matrix_pool]
    out_rhs = [float(value) for value in rhs]

    # First source loop: zero the selected row through row_ptr[target].
    target_row_offset = indices[target]
    for column in range(n):
        out_pool[target_row_offset + column] = 0.0

    # Second source loop: zero the selected column through every row pointer.
    for row in range(n):
        row_offset = indices[row]
        out_pool[row_offset + target] = 0.0

    # Source writes the unit diagonal and zeroes the corresponding RHS after both loops.
    out_pool[target_row_offset + target] = 1.0
    out_rhs[target] = 0.0

    return {
        "format": FORMAT,
        "version": 1,
        "status": "applied",
        "ready": True,
        "function": "FUN_007b2210",
        "source_line": SOURCE_LINE,
        "scalar_count": n,
        "node": target,
        "matrix_pool": out_pool,
        "rhs": out_rhs,
        "evidence": {
            "row_pointer_source": "+0x3c / per-body +0x158",
            "row_index_source": "+0x15c",
            "matrix_pool_source": "+0x38 / per-body +0x154",
            "operations": [
                "zero selected row",
                "zero selected column",
                "set selected diagonal to 1.0",
                "zero selected RHS",
            ],
            "operation_order": "row-zero -> column-zero -> diagonal-one -> rhs-zero",
        },
    }


def apply_identity_resets_to_row_storage(
    matrix_pool: Sequence[float | int],
    *,
    scalar_count: int,
    row_indices: Sequence[int],
    nodes: Sequence[int],
    rhs: Sequence[float | int],
) -> dict[str, Any]:
    """Apply multiple retail identity resets in the same helper contract."""
    out_pool = [float(value) for value in matrix_pool]
    out_rhs = [float(value) for value in rhs]
    applied: list[int] = []
    for node in sorted(set(int(value) for value in nodes)):
        result = apply_identity_reset_to_row_storage(
            out_pool,
            scalar_count=scalar_count,
            row_indices=row_indices,
            node=node,
            rhs=out_rhs,
        )
        out_pool = result["matrix_pool"]
        out_rhs = result["rhs"]
        applied.append(node)
    return {
        "format": FORMAT,
        "version": 1,
        "status": "applied",
        "ready": True,
        "function": "FUN_007b2210",
        "source_line": SOURCE_LINE,
        "scalar_count": int(scalar_count),
        "nodes": applied,
        "matrix_pool": out_pool,
        "rhs": out_rhs,
    }


def describe_identity_reset_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "source-backed",
        "ready": True,
        "function": "FUN_007b2210",
        "source_line": SOURCE_LINE,
        "builtin_path": {
            "row_storage": "matrix pool + row-pointer table",
            "operations": [
                "zero selected row",
                "zero selected column",
                "write 1.0 to diagonal",
                "zero RHS",
            ],
        },
        "provider_path": {
            "provider_pointer": "physics-system +0x48",
            "virtual_slot": "+0x1c",
            "status": "provider-owned when pointer is non-null",
        },
        "selection_source": "caller passes one scalar node index; frame layer derives selected nodes from runtime constraint flag bit 0",
    }


__all__ = [
    "FORMAT",
    "SOURCE_LINE",
    "apply_identity_reset_to_row_storage",
    "apply_identity_resets_to_row_storage",
    "describe_identity_reset_contract",
]
