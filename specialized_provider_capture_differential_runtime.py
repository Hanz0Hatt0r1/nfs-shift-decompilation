"""Differential harness for the experimental provider numeric executor.

Phase 460 consumes the existing SHIFT.SDFSolverCaptureRuntime/1 pre-solve schema
and compares an experimental solve result with an optional real post-solve
vector. Structural/provider gating remains separate from the numeric comparison.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from sdf_solver_capture_runtime import (
    compare_solver_vectors,
    normalize_solver_capture,
)
from specialized_provider_experimental_numeric_runtime import (
    solve_ldlt,
    solve_guided,
)

FORMAT = "SHIFT.SpecializedProviderSolverCaptureDifferentialRuntime/1"


def normalize_post_solve(
    post_solve: Mapping[str, Any],
    *,
    scalar_count: int,
) -> list[float]:
    values = post_solve.get("rhs")
    if values is None:
        values = post_solve.get("solution")
    if values is None:
        raise ValueError("post-solve capture must contain rhs or solution")

    result = [float(value) for value in values]
    if len(result) != int(scalar_count):
        raise ValueError(
            "post-solve vector length must equal pre-solve scalar_count"
        )
    return result


def run_capture_differential(
    pre_solve: Mapping[str, Any],
    *,
    expected_post_solve: Mapping[str, Any] | None = None,
    factor_edges: Iterable[tuple[int, int]] | None = None,
    abs_tol: float = 0.0,
    rel_tol: float = 0.0,
) -> dict[str, Any]:
    normalized = normalize_solver_capture(pre_solve)
    matrix = normalized["matrix"]
    rhs = normalized["rhs"]
    scalar_count = int(normalized["scalar_count"])

    edge_list = None
    if factor_edges is not None:
        edge_list = sorted(
            {
                (int(row), int(column))
                for row, column in factor_edges
            }
        )

    try:
        if edge_list is None:
            predicted = solve_ldlt(
                matrix,
                rhs,
            )
            mode = "dense-reference"
        else:
            predicted = solve_guided(
                matrix,
                rhs,
                factor_edges=edge_list,
                symmetry_tolerance=1e-10,
                factor_tolerance=1e-12,
                pivot_tolerance=1e-14,
            )
            mode = "source-pattern-guided"
    except (ValueError, ZeroDivisionError) as exc:
        return {
            "format": FORMAT,
            "version": 1,
            "status": "blocked",
            "ready": False,
            "scalar_count": scalar_count,
            "mode": (
                "source-pattern-guided"
                if edge_list is not None
                else "dense-reference"
            ),
            "predicted_solution": None,
            "comparison": None,
            "errors": [{"kind": "executor", "message": str(exc)}],
        }

    result: dict[str, Any] = {
        "format": FORMAT,
        "version": 1,
        "status": "predicted-only",
        "ready": True,
        "scalar_count": scalar_count,
        "mode": mode,
        "predicted_solution": predicted,
        "comparison": None,
        "errors": [],
    }

    if expected_post_solve is None:
        return result

    try:
        observed = normalize_post_solve(
            expected_post_solve,
            scalar_count=scalar_count,
        )
    except (TypeError, ValueError) as exc:
        result["status"] = "blocked"
        result["ready"] = False
        result["errors"] = [
            {"kind": "post-solve-schema", "message": str(exc)}
        ]
        return result

    comparison = compare_solver_vectors(
        observed,
        predicted,
        abs_tol=abs_tol,
        rel_tol=rel_tol,
    )
    result["comparison"] = comparison
    result["status"] = (
        "matched"
        if comparison["ready"]
        else "numeric-divergence"
    )
    result["ready"] = bool(comparison["ready"])
    return result


def summarize_capture_differential(report: Mapping[str, Any]) -> dict[str, Any]:
    comparison = report.get("comparison") or {}
    return {
        "scalar_count": report.get("scalar_count"),
        "mode": report.get("mode"),
        "status": report.get("status"),
        "predicted_only": report.get("status") == "predicted-only",
        "matched": report.get("status") == "matched",
        "numeric_divergence": report.get("status") == "numeric-divergence",
        "mismatch_count": int(comparison.get("mismatch_count", 0)),
        "max_abs_error": float(comparison.get("max_abs_error", 0.0)),
        "max_rel_error": float(comparison.get("max_rel_error", 0.0)),
        "ready": bool(report.get("ready")),
    }


def build_differential_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "input_schema": "SHIFT.SDFSolverCaptureRuntime/1",
        "post_solve": {
            "accepted_fields": ["rhs", "solution"],
            "length": "must equal pre_solve.scalar_count",
        },
        "modes": {
            "dense-reference": "experimental LDLT without provider topology",
            "source-pattern-guided": "experimental LDLT after Phase 458 support gate",
        },
        "result_statuses": [
            "predicted-only",
            "matched",
            "numeric-divergence",
            "blocked",
        ],
        "scope": {
            "numeric": "comparison only",
            "storage": "not reinterpreted",
            "provider_identity": "not inferred",
        },
        "limitations": [
            "A numeric match does not prove retail binary equivalence.",
            "A mismatch can originate from matrix capture, workspace mapping, initialization, or solver algebra.",
            "Provider backend captures remain distinct from builtin solver captures.",
        ],
        "status": "experimental-capture-differential-harness",
    }


__all__ = [
    "FORMAT",
    "normalize_post_solve",
    "run_capture_differential",
    "summarize_capture_differential",
    "build_differential_contract",
]
