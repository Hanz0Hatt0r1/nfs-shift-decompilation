"""Build the pre-acceptance logical matrix from the recovered solver domain.

Phase 486 closes the gap left by Phase 485: it derives BODY-local scalar groups
from ordered runtime constraint records, then applies the exact
cartesian-product/symmetric 1.0 write rule of FUN_007ba2b0.

No physical coefficient values are invented.
"""
from __future__ import annotations

from typing import Any, Mapping

from body_matrix_structure_runtime import (
    BodyGroup,
    build_body_group,
    matrix_cells_for_body_groups,
)
from specialized_provider_acceptance_predicate_runtime import (
    evaluate_acceptance_predicate,
)

FORMAT = "SHIFT.BODYSolverDomainMatrixBuilderRuntime/1"


def _body_name(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text.upper() if text else None


def build_body_group_map(
    solver_domain: Mapping[str, Any],
) -> dict[str, list[BodyGroup]]:
    """Group every ordered solver block by each BODY endpoint it touches."""
    groups: dict[str, list[BodyGroup]] = {}

    for record in solver_domain.get("records") or []:
        width = int(record.get("solver_width", 0))
        scalar_indices = [
            int(value)
            for value in (record.get("scalar_indices") or [])
        ]
        group = build_body_group(width, scalar_indices)

        for field in ("posbody", "negbody"):
            body = _body_name(record.get(field))
            if body is None:
                continue
            groups.setdefault(body, []).append(group)

    return {
        body: list(body_groups)
        for body, body_groups in sorted(groups.items())
    }


def build_structural_matrix(
    solver_domain: Mapping[str, Any],
    *,
    scalar_count: int | None = None,
) -> dict[str, Any]:
    """Build the 0/1 matrix implied by BODY group topology."""
    inferred = int(solver_domain.get("solver_scalar_count", 0))
    n = inferred if scalar_count is None else int(scalar_count)
    if n <= 0:
        raise ValueError("solver scalar count must be positive")

    groups_by_body = build_body_group_map(solver_domain)
    matrix = [[0.0] * n for _ in range(n)]
    body_cells: dict[str, set[tuple[int, int]]] = {}
    errors: list[str] = []

    for body, groups in groups_by_body.items():
        cells = matrix_cells_for_body_groups(groups)
        valid = {
            (row, column)
            for row, column in cells
            if 0 <= row < n and 0 <= column < n
        }
        if valid != cells:
            errors.append(f"body-{body}-scalar-index-out-of-domain")
        body_cells[body] = valid

        for row, column in valid:
            matrix[row][column] = 1.0

    diagonal_missing = [
        index
        for index in range(n)
        if matrix[index][index] == 0.0
    ]

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if not errors else "blocked",
        "ready": not errors,
        "scalar_count": n,
        "body_count": len(groups_by_body),
        "body_groups": {
            body: [
                {
                    "width": group.width,
                    "scalar_indices": list(group.scalar_indices),
                }
                for group in groups
            ]
            for body, groups in groups_by_body.items()
        },
        "body_cell_counts": {
            body: len(cells)
            for body, cells in body_cells.items()
        },
        "matrix": matrix,
        "matrix_nonzero_cells": sum(
            1
            for row in matrix
            for value in row
            if value != 0.0
        ),
        "strict_upper_nonzero_cells": sum(
            1
            for row in range(n)
            for column in range(row + 1, n)
            if matrix[row][column] != 0.0
        ),
        "diagonal_missing": diagonal_missing,
        "symmetric": all(
            matrix[row][column] == matrix[column][row]
            for row in range(n)
            for column in range(n)
        ),
        "body_cells": {
            body: [
                [row, column]
                for row, column in sorted(cells)
            ]
            for body, cells in body_cells.items()
        },
        "errors": errors,
    }


def build_bmw_matrix_structure(
    solver_domain: Mapping[str, Any],
) -> dict[str, Any]:
    """Build and guard the real 40-scalar BMW-shaped solver domain."""
    scalar_count = int(solver_domain.get("solver_scalar_count", 0))
    if scalar_count != 40:
        return {
            "format": FORMAT,
            "version": 1,
            "status": "dimension-mismatch",
            "ready": False,
            "expected_scalar_count": 40,
            "actual_scalar_count": scalar_count,
            "matrix": [],
            "errors": ["expected-bmw-scalar-count-40"],
        }

    result = build_structural_matrix(
        solver_domain,
        scalar_count=40,
    )
    result["expected_bmw"] = {
        "body_count": 11,
        "constraint_records": 28,
        "scalar_count": 40,
    }
    result["bmw_shape_ready"] = (
        result["body_count"] == 11
        and len(solver_domain.get("records") or []) == 28
        and result["scalar_count"] == 40
    )
    if not result["bmw_shape_ready"]:
        result["errors"].append("bmw-topology-shape-mismatch")
        result["ready"] = False
        result["status"] = "blocked"

    return result


def compare_structure_to_seed(
    generated: Mapping[str, Any],
    seed_matrix: Mapping[str, Any],
) -> dict[str, Any]:
    generated_matrix = generated.get("matrix") or []
    observed_matrix = seed_matrix.get("matrix") or []
    n = int(generated.get("scalar_count", 0))

    if len(observed_matrix) != n:
        return {
            "format": "SHIFT.BODYSolverDomainMatrixSeedComparison/1",
            "version": 1,
            "status": "blocked",
            "ready": False,
            "errors": ["seed-dimension-mismatch"],
        }

    mismatches: list[dict[str, Any]] = []
    for row in range(n):
        if len(observed_matrix[row]) != n:
            return {
                "format": "SHIFT.BODYSolverDomainMatrixSeedComparison/1",
                "version": 1,
                "status": "blocked",
                "ready": False,
                "errors": ["seed-row-dimension-mismatch"],
            }
        for column in range(n):
            generated_nonzero = (
                float(generated_matrix[row][column]) != 0.0
            )
            observed_nonzero = (
                float(observed_matrix[row][column]) != 0.0
            )
            if generated_nonzero != observed_nonzero:
                mismatches.append(
                    {
                        "row": row,
                        "column": column,
                        "generated_nonzero": generated_nonzero,
                        "seed_nonzero": observed_nonzero,
                    }
                )

    generated_nonzero_count = sum(
        1
        for row in generated_matrix
        for value in row
        if float(value) != 0.0
    )
    observed_nonzero_count = sum(
        1
        for row in observed_matrix
        for value in row
        if float(value) != 0.0
    )

    return {
        "format": "SHIFT.BODYSolverDomainMatrixSeedComparison/1",
        "version": 1,
        "status": (
            "matched"
            if not mismatches
            else "structural-divergence"
        ),
        "ready": not mismatches,
        "scalar_count": n,
        "generated_nonzero_cells": generated_nonzero_count,
        "seed_nonzero_cells": observed_nonzero_count,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
    }


def evaluate_generated_acceptance(
    generated: Mapping[str, Any],
    *,
    provider_ids: tuple[int, ...] = (0, 1),
) -> dict[str, Any]:
    matrix = generated.get("matrix") or []
    results = [
        evaluate_acceptance_predicate(
            provider_id,
            matrix,
        )
        for provider_id in provider_ids
    ]
    matches = [
        int(result["provider_id"])
        for result in results
        if result.get("matched") is True
    ]

    return {
        "format": "SHIFT.BODYSolverDomainMatrixAcceptance/1",
        "version": 1,
        "scalar_count": generated.get("scalar_count"),
        "providers": results,
        "matching_provider_ids": matches,
        "match_count": len(matches),
        "status": (
            "unique-match"
            if len(matches) == 1
            else "multiple-match"
            if len(matches) > 1
            else "no-match"
        ),
        "provider_identity_inferred": False,
        "ready": all(
            result.get("ready") is True
            for result in results
        ),
    }


def summarize_structural_matrix(
    generated: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "scalar_count": generated.get("scalar_count"),
        "body_count": generated.get("body_count"),
        "matrix_nonzero_cells": generated.get(
            "matrix_nonzero_cells"
        ),
        "strict_upper_nonzero_cells": generated.get(
            "strict_upper_nonzero_cells"
        ),
        "diagonal_missing_count": len(
            generated.get("diagonal_missing") or []
        ),
        "symmetric": bool(generated.get("symmetric")),
        "ready": bool(generated.get("ready")),
    }


def build_body_matrix_builder_contract(
    solver_domain: Mapping[str, Any],
) -> dict[str, Any]:
    generated = build_structural_matrix(solver_domain)
    acceptance = evaluate_generated_acceptance(generated)

    return {
        "format": FORMAT,
        "version": 1,
        "source": "FUN_007b2010 -> FUN_007ba2b0",
        "input": {
            "solver_domain": (
                "ordered runtime constraint records from FUN_007b1b60"
            ),
        },
        "generated": generated,
        "summary": summarize_structural_matrix(generated),
        "acceptance": acceptance,
        "formula": {
            "body_groups": (
                "all runtime constraint blocks incident on posbody/negbody"
            ),
            "group_width": "JOINT=3, HINGE=2, BAR=1",
            "matrix_write": (
                "for each BODY, write 1.0 over every ordered pair of scalars "
                "across all local groups"
            ),
            "symmetry": (
                "write both row/column directions"
            ),
        },
        "limitations": [
            "The solver domain must already contain scalar bases/order from FUN_007b1b60.",
            "The generated matrix is a structural 0/1 seed; later coefficient accumulation is outside this phase.",
            "A provider acceptance match remains a candidate signal and does not identify a provider class.",
        ],
        "status": "source-backed-body-solver-domain-matrix-builder",
    }


__all__ = [
    "FORMAT",
    "build_body_group_map",
    "build_structural_matrix",
    "build_bmw_matrix_structure",
    "compare_structure_to_seed",
    "evaluate_generated_acceptance",
    "summarize_structural_matrix",
    "build_body_matrix_builder_contract",
]
