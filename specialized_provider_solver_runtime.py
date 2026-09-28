"""Source-backed pivot geometry for the two specialized SHIFT solvers.

FUN_007c7200 (provider 0) and FUN_007cdfc0 (provider 1) are fully unrolled
numeric routines. The retail source contains exactly one unique reciprocal
pivot per solver scalar, and each pivot diagonal is stored at:

    row_pointer[i] + 8*i

This module records and validates that exact relation while keeping the
individual unrolled coefficient updates in the retail source boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from specialized_provider_row_storage_runtime import get_row_pointers
from specialized_provider_storage_runtime import get_storage_layout

FORMAT = "SHIFT.SpecializedProviderSolverPivotRuntime/1"

PROVIDER_SOLVER = {
    0: {
        "function": "FUN_007c7200",
        "source_start_line": 825788,
        "source_end_line": 827354,
        "unique_reciprocal_count": 40,
        "first_reciprocal_line": 825794,
        "last_reciprocal_line": 827122,
    },
    1: {
        "function": "FUN_007cdfc0",
        "source_start_line": 827583,
        "source_end_line": 828788,
        "unique_reciprocal_count": 34,
        "first_reciprocal_line": 827589,
        "last_reciprocal_line": 828556,
    },
}


@dataclass(frozen=True)
class SolverPivot:
    index: int
    row_pointer: int
    diagonal_address: int
    diagonal_offset: int


def get_solver_spec(provider_id: int) -> dict[str, Any]:
    try:
        return dict(PROVIDER_SOLVER[provider_id])
    except KeyError as exc:
        raise ValueError(f"unsupported provider id: {provider_id}") from exc


def build_pivot_geometry(provider_id: int) -> tuple[SolverPivot, ...]:
    layout = get_storage_layout(provider_id)
    pointers = get_row_pointers(provider_id)
    spec = get_solver_spec(provider_id)
    if len(pointers) != layout.scalar_count:
        raise ValueError("row-pointer count and scalar count disagree")
    if int(spec["unique_reciprocal_count"]) != layout.scalar_count:
        raise ValueError("solver reciprocal count and scalar count disagree")
    return tuple(
        SolverPivot(
            index=i,
            row_pointer=pointers[i],
            diagonal_address=pointers[i] + i * 8,
            diagonal_offset=i * 8,
        )
        for i in range(layout.scalar_count)
    )


def validate_pivot_geometry(provider_id: int) -> dict[str, Any]:
    layout = get_storage_layout(provider_id)
    spec = get_solver_spec(provider_id)
    pivots = build_pivot_geometry(provider_id)
    errors: list[str] = []

    if len(pivots) != layout.scalar_count:
        errors.append("pivot-count-does-not-equal-scalar-count")
    if int(spec["unique_reciprocal_count"]) != len(pivots):
        errors.append("source-reciprocal-count-mismatch")

    for pivot in pivots:
        expected = pivot.row_pointer + pivot.diagonal_offset
        if pivot.diagonal_address != expected:
            errors.append(f"pivot-{pivot.index}-diagonal-address-mismatch")
            break

    if pivots and pivots[0].diagonal_address != layout.factor_workspace_base:
        errors.append("first-pivot-does-not-equal-workspace-base")

    return {
        "format": "SHIFT.SpecializedProviderSolverPivotValidation/1",
        "version": 1,
        "provider_id": provider_id,
        "ready": not errors,
        "errors": errors,
        "scalar_count": layout.scalar_count,
        "unique_reciprocal_count": spec["unique_reciprocal_count"],
        "pivot_count": len(pivots),
        "source_line_range": [spec["source_start_line"], spec["source_end_line"]],
        "first_reciprocal_line": spec["first_reciprocal_line"],
        "last_reciprocal_line": spec["last_reciprocal_line"],
    }


def build_solver_pivot_contract() -> dict[str, Any]:
    providers: list[dict[str, Any]] = []
    for provider_id in (0, 1):
        layout = get_storage_layout(provider_id)
        spec = get_solver_spec(provider_id)
        pivots = build_pivot_geometry(provider_id)
        providers.append(
            {
                "provider_id": provider_id,
                "function": spec["function"],
                "scalar_count": layout.scalar_count,
                "unique_reciprocal_count": spec["unique_reciprocal_count"],
                "source_line_range": [
                    spec["source_start_line"],
                    spec["source_end_line"],
                ],
                "reciprocal_line_range": [
                    spec["first_reciprocal_line"],
                    spec["last_reciprocal_line"],
                ],
                "pivot_formula": "row_pointer[i] + 8*i",
                "pivot_addresses": [hex(p.diagonal_address) for p in pivots],
                "pivot_offsets": [p.diagonal_offset for p in pivots],
                "output_vector_base": hex(
                    layout.output_vector_base
                ),
                "validation": validate_pivot_geometry(provider_id),
            }
        )
    return {
        "format": FORMAT,
        "version": 1,
        "source_file": "SHIFT.exe.c",
        "providers": providers,
        "solver_family": {
            "classification": "fully-unrolled symmetric pivot/elimination routine",
            "numeric_core_observed": [
                "reciprocal pivot",
                "normalized coefficient writes",
                "target-row subtraction",
                "forward RHS accumulation",
                "descending solved-vector elimination",
            ],
            "relationship_to_builtin": "same broad sparse LDL^T-style algebra family, but provider implementations are fixed-layout and unrolled",
        },
        "limitations": [
            "This phase records pivot geometry and source-level solver-family evidence; it does not replace every unrolled coefficient expression with generated code.",
            "Provider acceptance still occurs against the populated runtime matrix.",
        ],
        "status": "source-backed-pivot-geometry",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(build_solver_pivot_contract(), indent=2, sort_keys=True))
