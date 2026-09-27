"""End-to-end lower-triangle assembly for reconstructed SHIFT SDF coupling kernels."""
from __future__ import annotations

from typing import Any, Mapping, Sequence
from sdf_constraint_seed_write_runtime import materialize_seed_matrix

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



def materialize_source_seed_matrix(
    scalar_connectivity: Mapping[str, Any],
) -> dict[str, Any]:
    """Materialize the exact 1.0 seed-write layer from FUN_007ba2b0."""
    matrix = scalar_connectivity.get("matrix")
    if not isinstance(matrix, Sequence):
        raise ValueError("scalar_connectivity must provide a matrix")
    result = materialize_seed_matrix(matrix)
    result["source_connectivity"] = {
        "format": scalar_connectivity.get("format"),
        "solver_scalar_count": scalar_connectivity.get("solver_scalar_count"),
        "shared_block_count": scalar_connectivity.get("shared_block_count"),
    }
    return result

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



def build_retail_matrix_storage(
    scalar_count: int,
    matrix_base_address: int = 0,
    row_indices: Sequence[int] | None = None,
) -> dict[str, Any]:
    """Reproduce the row-pointer/index layout initialized by retail SDF setup."""
    n = int(scalar_count)
    base = int(matrix_base_address)
    if n < 0:
        raise ValueError("scalar_count must be non-negative")
    if row_indices is None:
        indices = [n * row for row in range(n)]
    else:
        indices = [int(value) for value in row_indices]
        if len(indices) != n:
            raise ValueError("row_indices length must equal scalar_count")
        if any(value < 0 or value >= n * n for value in indices):
            raise ValueError("row_indices must reference matrix double offsets")
    row_pointers = [base + index * 8 for index in indices]
    return {
        "format": "SHIFT.SDFRetailMatrixStorage/1",
        "version": 1,
        "status": "materialized",
        "ready": True,
        "scalar_count": n,
        "matrix_base_address": base,
        "matrix_double_count": n * n,
        "matrix_bytes": n * n * 8,
        "row_pointer_count": n,
        "row_pointer_bytes": n * 4,
        "row_indices": indices,
        "row_pointers": row_pointers,
        "row_stride_doubles": n,
        "evidence": {
            "allocation": "FUN_007b3820",
            "allocation_source_line": 813669,
            "per_body_rebuild": "FUN_007bb8d0",
            "per_body_rebuild_source_line": 814093,
            "row_zeroing": "FUN_007b2010",
            "row_zeroing_source_line": 812385,
            "row_pointer_formula": "matrix_base + row_index*8",
            "canonical_row_index_formula": "scalar_count*row",
        },
    }


def flatten_retail_matrix(
    matrix: Sequence[Sequence[float | int]],
) -> list[float]:
    """Flatten a square matrix in row-major double order."""
    n = len(matrix)
    if any(len(row) != n for row in matrix):
        raise ValueError("matrix must be square")
    return [float(value) for row in matrix for value in row]


def read_retail_matrix_cell(
    matrix_pool: Sequence[float | int],
    *,
    scalar_count: int,
    row_index_offset: int,
    column: int,
) -> float:
    """Read one matrix cell through a retail row-index offset."""
    n = int(scalar_count)
    row_offset = int(row_index_offset)
    col = int(column)
    if n < 0:
        raise ValueError("scalar_count must be non-negative")
    if row_offset < 0 or row_offset >= n * n:
        raise ValueError("row_index_offset is outside matrix pool")
    if col < 0 or col >= n:
        raise ValueError("column is outside matrix width")
    cell = row_offset + col
    if cell >= len(matrix_pool):
        raise ValueError("matrix cell is outside matrix pool")
    return float(matrix_pool[cell])


def materialize_retail_matrix(
    matrix: Sequence[Sequence[float | int]],
    matrix_base_address: int = 0,
) -> dict[str, Any]:
    """Build logical matrix plus retail row-pointer/index representation."""
    n = len(matrix)
    layout = build_retail_matrix_storage(n, matrix_base_address)
    pool = flatten_retail_matrix(matrix)
    return {
        "format": "SHIFT.SDFRetailMatrixMaterialization/1",
        "version": 1,
        "status": "materialized",
        "ready": True,
        "matrix": [[float(value) for value in row] for row in matrix],
        "matrix_pool": pool,
        "layout": layout,
    }


def validate_retail_matrix_storage(
    matrix: Sequence[Sequence[float | int]],
    layout: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate logical rows against retail row-index/pointer formulas."""
    n = len(matrix)
    if any(len(row) != n for row in matrix):
        return {"ready": False, "errors": ["matrix-not-square"]}
    indices = [int(value) for value in layout.get("row_indices", [])]
    pointers = [int(value) for value in layout.get("row_pointers", [])]
    errors: list[str] = []
    if len(indices) != n:
        errors.append("row-index-count-mismatch")
    if len(pointers) != n:
        errors.append("row-pointer-count-mismatch")
    base = int(layout.get("matrix_base_address", 0))
    for row in range(min(n, len(indices), len(pointers))):
        expected_index = n * row
        if indices[row] != expected_index:
            errors.append(f"row-{row}-index-mismatch")
        if pointers[row] != base + indices[row] * 8:
            errors.append(f"row-{row}-pointer-mismatch")
    return {
        "format": "SHIFT.SDFRetailMatrixStorageValidation/1",
        "version": 1,
        "ready": not errors,
        "errors": errors,
        "validated_rows": n,
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
            "SEED": "FUN_007ba2b0",
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
            "FUN_007ba2b0 scalar seed",
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


def apply_builtin_row_identity_constraints(
    matrix: Sequence[Sequence[float | int]],
    rhs: Sequence[float | int],
    selected_nodes: Sequence[int],
) -> dict[str, Any]:
    """Apply the already reconstructed FUN_007b2210 stage after matrix assembly."""
    from sdf_constraint_solver_frame_runtime import apply_builtin_diagonal_reset

    return apply_builtin_diagonal_reset(matrix, rhs, selected_nodes)


def build_solver_ready_matrix(
    scalar_count: int,
    contributions: Sequence[Mapping[str, Any]],
    rhs: Sequence[float | int],
    selected_identity_nodes: Sequence[int],
) -> dict[str, Any]:
    """Assemble source lower-triangle contributions and apply row/column identity resets."""
    if len(rhs) != int(scalar_count):
        raise ValueError("rhs length must equal scalar_count")
    assembled = assemble_lower_triangle(scalar_count, contributions)
    reset = apply_builtin_row_identity_constraints(
        assembled["matrix"],
        rhs,
        selected_identity_nodes,
    )
    return {
        "format": "SHIFT.SDFSolverReadyMatrix/1",
        "version": 1,
        "status": "ready",
        "ready": True,
        "assembled": assembled,
        "identity_reset": reset,
        "matrix": reset["matrix"],
        "rhs": reset["rhs"],
        "selected_identity_nodes": list(reset["nodes"]),
        "evidence": {
            "assembly": "FUN_007bbb80/FUN_007bb250/FUN_007bb6c0",
            "identity_reset": "FUN_007b2210",
        },
    }
