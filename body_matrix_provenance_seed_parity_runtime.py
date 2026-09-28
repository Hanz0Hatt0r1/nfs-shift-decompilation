"""Combine BODY matrix construction, cell provenance and BMW seed parity.

Phase 490 produces a single structural report in which every non-zero matrix
cell is explainable by at least one BODY/group provenance witness and the full
40x40 support can be checked against the Phase 406 BMW seed fingerprint.
"""
from __future__ import annotations

from typing import Any, Mapping

from body_solver_domain_matrix_builder_runtime import (
    build_structural_matrix,
)
from body_matrix_cell_provenance_runtime import (
    build_cell_provenance,
    provenance_for_cell,
)
from bmw_preacceptance_matrix_verifier_runtime import (
    EXPECTED_SEED,
)

FORMAT = "SHIFT.BODYMatrixProvenanceSeedParityRuntime/1"


def build_provenance_seed_parity(
    solver_domain: Mapping[str, Any],
) -> dict[str, Any]:
    generated = build_structural_matrix(solver_domain)
    provenance = build_cell_provenance(solver_domain)

    errors = list(generated.get("errors") or [])
    errors.extend(provenance.get("errors") or [])

    matrix = generated.get("matrix") or []
    n = int(generated.get("scalar_count", 0))

    if len(matrix) != n:
        errors.append("matrix-row-count-mismatch")
        matrix = []

    missing_provenance_cells: list[str] = []
    unsupported_nonzero_cells: list[str] = []

    for row in range(n):
        if len(matrix[row]) != n:
            errors.append(f"matrix-column-count-mismatch:{row}")
            continue

        for column in range(n):
            key = f"{row},{column}"
            nonzero = float(matrix[row][column]) != 0.0
            producers = provenance_for_cell(
                provenance,
                row,
                column,
            )
            if nonzero and not producers:
                missing_provenance_cells.append(key)
            if producers and not nonzero:
                unsupported_nonzero_cells.append(key)

    if missing_provenance_cells:
        errors.append(
            f"nonzero-cells-without-provenance:{len(missing_provenance_cells)}"
        )
    if unsupported_nonzero_cells:
        errors.append(
            f"provenance-without-nonzero-cell:{len(unsupported_nonzero_cells)}"
        )

    row_counts = [
        sum(
            1
            for value in row
            if float(value) != 0.0
        )
        for row in matrix
    ] if matrix else []

    actual_nonzero = sum(row_counts)
    strict_upper = sum(
        1
        for row in range(n)
        for column in range(row + 1, n)
        if matrix[row][column] != 0.0
    ) if matrix else 0

    seed_metrics = {
        "nonzero": actual_nonzero,
        "zero": n * n - actual_nonzero,
        "strict_upper_nonzero": strict_upper,
        "row_nonzero_counts": row_counts,
    }

    expected = EXPECTED_SEED
    seed_match = (
        n == 40
        and seed_metrics["nonzero"] == expected["matrix_nonzero_cells"]
        and seed_metrics["zero"] == expected["matrix_zero_cells"]
        and seed_metrics["strict_upper_nonzero"]
        == expected["strict_upper_nonzero_cells"]
        and seed_metrics["row_nonzero_counts"]
        == expected["row_nonzero_counts"]
    )

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if not errors else "blocked",
        "ready": not errors,
        "scalar_count": n,
        "generated_matrix": generated,
        "provenance": provenance,
        "seed_metrics": seed_metrics,
        "seed_shape_match": seed_match,
        "expected_seed_shape": {
            "scalar_count": 40,
            "matrix_nonzero_cells": expected["matrix_nonzero_cells"],
            "matrix_zero_cells": expected["matrix_zero_cells"],
            "strict_upper_nonzero_cells": expected[
                "strict_upper_nonzero_cells"
            ],
            "row_nonzero_counts": list(
                expected["row_nonzero_counts"]
            ),
        },
        "missing_provenance_cells": missing_provenance_cells,
        "unsupported_nonzero_cells": unsupported_nonzero_cells,
        "errors": errors,
    }


def summarize_provenance_seed_parity(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    seed_metrics = report.get("seed_metrics") or {}
    provenance = report.get("provenance") or {}
    return {
        "scalar_count": report.get("scalar_count"),
        "nonzero_cells": seed_metrics.get("nonzero"),
        "strict_upper_nonzero": seed_metrics.get(
            "strict_upper_nonzero"
        ),
        "provenance_cells": provenance.get("nonzero_cell_count"),
        "missing_provenance_cells": len(
            report.get("missing_provenance_cells") or []
        ),
        "unsupported_nonzero_cells": len(
            report.get("unsupported_nonzero_cells") or []
        ),
        "seed_shape_match": bool(
            report.get("seed_shape_match")
        ),
        "ready": bool(report.get("ready")),
    }


def validate_provenance_seed_parity(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    errors = list(report.get("errors") or [])

    seed_metrics = report.get("seed_metrics") or {}
    provenance = report.get("provenance") or {}

    if int(
        seed_metrics.get("nonzero", 0)
    ) != int(
        provenance.get("nonzero_cell_count", 0)
    ):
        errors.append("matrix-provenance-cell-count-mismatch")

    if report.get("seed_shape_match") is not True:
        errors.append("bmw-seed-shape-mismatch")

    if report.get("missing_provenance_cells"):
        errors.append("missing-provenance-present")

    if report.get("unsupported_nonzero_cells"):
        errors.append("unsupported-nonzero-cell-present")

    return {
        "format": "SHIFT.BODYMatrixProvenanceSeedParityValidation/1",
        "version": 1,
        "ready": not errors,
        "errors": list(dict.fromkeys(errors)),
    }


def build_provenance_seed_parity_contract(
    solver_domain: Mapping[str, Any],
) -> dict[str, Any]:
    report = build_provenance_seed_parity(solver_domain)
    report["summary"] = summarize_provenance_seed_parity(report)
    report["validation"] = validate_provenance_seed_parity(report)
    return report


__all__ = [
    "FORMAT",
    "build_provenance_seed_parity",
    "summarize_provenance_seed_parity",
    "validate_provenance_seed_parity",
    "build_provenance_seed_parity_contract",
]
