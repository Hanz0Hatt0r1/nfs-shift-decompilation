"""Run the recovered provider acceptance predicates as a candidate analyzer.

Phase 482 evaluates one captured logical matrix against both specialized
provider signatures. It does not select a provider class; it only reports which
source-backed sparsity predicates match the supplied matrix.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from specialized_provider_acceptance_predicate_runtime import (
    evaluate_acceptance_predicate,
)
from sdf_solver_capture_runtime import normalize_solver_capture

FORMAT = "SHIFT.SpecializedProviderAcceptanceCandidateRuntime/1"


def analyze_acceptance_candidates(
    matrix: Sequence[Sequence[float | int]],
    *,
    provider_ids: Sequence[int] = (0, 1),
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for provider_id in provider_ids:
        result = evaluate_acceptance_predicate(
            int(provider_id),
            matrix,
        )
        results.append(result)

    matches = [
        int(result["provider_id"])
        for result in results
        if result.get("matched") is True
    ]

    return {
        "format": FORMAT,
        "version": 1,
        "matrix_dimension": len(matrix),
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
        "ready": all(
            result.get("ready") is True
            for result in results
        ),
        "provider_identity_inferred": False,
        "limitations": [
            "A sparsity match is only a candidate-provider signal.",
            "Dimension mismatch prevents a provider predicate from being evaluated.",
            "No provider class identity is inferred from sparsity alone.",
        ],
    }


def analyze_capture_candidates(
    capture: Mapping[str, Any],
    *,
    provider_ids: Sequence[int] = (0, 1),
) -> dict[str, Any]:
    """Run candidate predicates over an existing logical SDF capture."""
    normalized = normalize_solver_capture(capture)
    return analyze_acceptance_candidates(
        normalized["matrix"],
        provider_ids=provider_ids,
    )


def summarize_acceptance_candidates(
    report: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "matrix_dimension": report.get("matrix_dimension"),
        "matching_provider_ids": list(
            report.get("matching_provider_ids") or []
        ),
        "match_count": int(report.get("match_count", 0)),
        "status": report.get("status"),
        "ready": bool(report.get("ready")),
        "provider_identity_inferred": bool(
            report.get("provider_identity_inferred")
        ),
    }


def build_acceptance_candidate_contract() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "input": {
            "matrix": "logical square matrix supplied by caller",
            "provider_ids": "candidate provider IDs; defaults to 0 and 1",
        },
        "output": {
            "matching_provider_ids": "providers whose source-backed acceptance predicate matches",
            "status": "unique-match / multiple-match / no-match",
        },
        "scope": {
            "criterion": "exact strict-upper zero/non-zero RLE predicate",
            "identity": "not inferred",
        },
        "known_bmw_seed_boundary": {
            "scalar_count": 40,
            "matrix_nonzero_cells": 700,
            "strict_upper_nonzero_cells": 330,
            "provider0_expected_strict_upper_nonzero": 450,
            "provider1_expected_dimension": 34,
            "interpretation": (
                "the repository seed metadata is insufficient for a cell-level "
                "predicate run because the full seed matrix is not stored"
            ),
        },
        "status": "source-backed-acceptance-candidate-analyzer",
    }


__all__ = [
    "FORMAT",
    "analyze_acceptance_candidates",
    "analyze_capture_candidates",
    "summarize_acceptance_candidates",
    "build_acceptance_candidate_contract",
]
