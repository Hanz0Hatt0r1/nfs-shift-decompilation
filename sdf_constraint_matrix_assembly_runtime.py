"""End-to-end lower-triangle assembly for reconstructed SHIFT SDF coupling kernels."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.SDFConstraintMatrixAssemblyRuntime/1"


def create_zero_matrix(scalar_count: int) -> list[list[float]]:
    n = int(scalar_count)
    if n < 0:
        raise ValueError("scalar_count must be non-negative")
    return [[0.0 for _ in range(n)] for _ in range(n)]


def add_block(
    matrix: Sequence[Sequence[float | int]],
    *,
    row_base: int,
    column_base: int,
    block: Sequence[Sequence[float | int]],
) -> list[list[float]]:
    if not block or any(len(row) == 0 for row in block):
        raise ValueError("block must not be empty")
    out = [[float(value) for value in row] for row in matrix]
    n = len(out)
    if any(len(row) != n for row in out):
        raise ValueError("matrix must be square")
    for r_offset, row in enumerate(block):
        for c_offset, value in enumerate(row):
            row_index = int(row_base) + r_offset
            column_index = int(column_base) + c_offset
            if (
                row_index < 0
                or column_index < 0
                or row_index >= n
                or column_index >= n
            ):
                raise ValueError("block is outside matrix")
            out[row_index][column_index] += float(value)
    return out


def assemble_lower_triangle(
    scalar_count: int,
    contributions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Apply all reconstructed source blocks without fabricating upper-triangle writes."""
    matrix = create_zero_matrix(scalar_count)
    applied: list[dict[str, Any]] = []
    for contribution in contributions:
        block = contribution.get("block")
        if block is None:
            raise ValueError("contribution is missing block")
        row_base = int(contribution["row_base"])
        column_base = int(contribution["column_base"])
        matrix = add_block(
            matrix,
            row_base=row_base,
            column_base=column_base,
            block=block,
        )
        applied.append({
            "kind": str(contribution.get("kind", "unknown")),
            "row_base": row_base,
            "column_base": column_base,
            "rows": len(block),
            "cols": len(block[0]) if block else 0,
        })

    nonzero_entries = sum(
        1
        for row in matrix
        for value in row
        if float(value) != 0.0
    )
    upper_nonzero_without_lower = [
        (row, column)
        for row in range(len(matrix))
        for column in range(row + 1, len(matrix))
        if matrix[row][column] != 0.0 and matrix[column][row] == 0.0
    ]

    return {
        "format": FORMAT,
        "version": 1,
        "status": "assembled",
        "ready": True,
        "scalar_count": int(scalar_count),
        "matrix": matrix,
        "applied": applied,
        "contribution_count": len(applied),
        "nonzero_entries": nonzero_entries,
        "upper_nonzero_without_lower": upper_nonzero_without_lower,
        "storage": {
            "row_pointer_table": "+0x158",
            "matrix_domain": "lower triangle contributions",
        },
        "evidence": {
            "jo_int_kernel": "FUN_007bbb80",
            "hinge_kernel": "FUN_007bb250",
            "bar_kernel": "FUN_007bb6c0",
            "upper_triangle_policy": "not synthesized during source assembly",
        },
        "limitations": [
            "The upper triangle can be materialized as a derived symmetric view for analysis, but retail write sites are preserved as lower-triangle-only.",
            "Diagonal row/column identity resets from FUN_007b2210 are a separate later stage.",
        ],
    }


def materialize_symmetric_view(
    lower_matrix: Sequence[Sequence[float | int]],
) -> list[list[float]]:
    """Create a derived symmetric matrix view from a lower-triangle source matrix."""
    n = len(lower_matrix)
    if any(len(row) != n for row in lower_matrix):
        raise ValueError("matrix must be square")
    out = [[float(value) for value in row] for row in lower_matrix]
    for row in range(n):
        for column in range(row + 1, n):
            out[row][column] = out[column][row]
    return out


def describe_sdf_constraint_matrix_assembly_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "source-backed-orchestration",
        "ready": True,
        "kernels": {
            "JOINT": "FUN_007bbb80",
            "HINGE": "FUN_007bb250",
            "BAR": "FUN_007bb6c0",
        },
        "blocks": [
            "JOINT self 3x3 lower triangle",
            "JOINT/JOINT 3x3",
            "JOINT/HINGE 3x2",
            "JOINT/BAR 3x1",
            "HINGE/HINGE 2x2 lower triangle",
            "HINGE/BAR 2x1 or 1x2",
            "BAR/BAR 1x1",
        ],
        "assembly_order": [
            "JOINT kernel",
            "HINGE kernel",
            "BAR kernel",
        ],
        "matrix_storage": "+0x158 row-pointer table",
        "derived_view": "materialize_symmetric_view()",
        "limitations": [
            "The assembler does not reorder constraints or apply FUN_007b2210 identity resets.",
            "Coefficient values remain owned by the individual source-backed kernels.",
        ],
    }
