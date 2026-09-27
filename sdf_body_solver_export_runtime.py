"""Source-backed export of per-body solver vector/matrix contributions."""
from __future__ import annotations

from typing import Any, Sequence

FORMAT = "SHIFT.SDFBodySolverExportRuntime/2"

SOURCE_OFFSETS = {
    "solver_vector": "+0x150",
    "solver_vector_count": "+0xa4",
    "solver_matrix": "+0x154",
    "solver_matrix_count": "+0xa8",
}


def describe_sdf_body_solver_export_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 2,
        "status": "source-backed",
        "ready": True,
        "function": "FUN_007ba570",
        "sources": SOURCE_OFFSETS,
        "destination_arguments": {
            "solver_vector_destination": "param_1 (PhysicsSystem +0x40)",
            "solver_matrix_destination": "param_2 (PhysicsSystem +0x44)",
        },
        "operations": [
            {
                "source": "+0x150",
                "count": "+0xa4",
                "stride": 8,
                "operation": "solver_vector_destination[i] += source[i]",
            },
            {
                "source": "+0x154",
                "count": "+0xa8",
                "stride": 8,
                "operation": "solver_matrix_destination[i] += source[i]",
            },
        ],
        "order": [
            "add per-body solver vector contribution",
            "add per-body solver matrix contribution",
        ],
        "limitations": [
            "Destination buffers are caller-owned and their higher-level role is intentionally unnamed.",
            "No physical units are inferred from the double channels.",
        ],
    }


def export_body_solver_contributions(
    solver_vector: Sequence[float | int],
    solver_matrix: Sequence[float | int],
    solver_vector_destination: Sequence[float | int],
    solver_matrix_destination: Sequence[float | int],
) -> dict[str, Any]:
    """Apply FUN_007ba570's additive transfer into vector and matrix destinations."""
    if len(solver_vector_destination) < len(solver_vector):
        raise ValueError("solver vector destination is shorter than solver vector")
    if len(solver_matrix_destination) < len(solver_matrix):
        raise ValueError("solver matrix destination is shorter than solver matrix")

    vector_out = [float(value) for value in solver_vector_destination]
    matrix_out = [float(value) for value in solver_matrix_destination]
    for index, value in enumerate(solver_vector):
        vector_out[index] += float(value)
    for index, value in enumerate(solver_matrix):
        matrix_out[index] += float(value)

    return {
        "format": "SHIFT.SDFBodySolverExportResult/2",
        "version": 2,
        "status": "applied",
        "ready": True,
        "solver_vector": vector_out,
        "solver_matrix": matrix_out,
        "source_counts": {
            "solver_vector": len(solver_vector),
            "solver_matrix": len(solver_matrix),
        },
        "evidence": {
            "function": "FUN_007ba570",
            "solver_vector_source": "+0x150",
            "solver_matrix_source": "+0x154",
            "solver_vector_count": "+0xa4",
            "solver_matrix_count": "+0xa8",
        },
    }


def export_body_accumulators(
    primary: Sequence[float | int],
    secondary: Sequence[float | int],
    primary_destination: Sequence[float | int],
    secondary_destination: Sequence[float | int],
) -> dict[str, Any]:
    """Backward-compatible alias for export_body_solver_contributions."""
    return export_body_solver_contributions(
        primary,
        secondary,
        primary_destination,
        secondary_destination,
    )
