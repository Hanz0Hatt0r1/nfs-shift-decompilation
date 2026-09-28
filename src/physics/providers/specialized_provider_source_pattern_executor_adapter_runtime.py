"""Bridge the retail-derived factor pattern to the experimental numeric executor.

Phase 459 keeps the source parser and numerical core decoupled. The adapter loads
the source-derived factor edge set, exposes a machine-readable pattern contract,
and provides a guarded solve entry point that delegates to Phase 458's
admissibility gate.
"""
from __future__ import annotations

from typing import Any, Sequence

from specialized_provider_experimental_numeric_runtime import (
    compare_factor_pattern,
    solve_guided,
)
from specialized_provider_factor_pattern_runtime import (
    extract_factor_pattern,
)
from specialized_provider_storage_runtime import get_storage_layout

FORMAT = "SHIFT.SpecializedProviderSourcePatternExecutorAdapter/1"


def extract_source_factor_edges(
    source: str,
    *,
    provider_id: int,
) -> dict[str, Any]:
    report = extract_factor_pattern(
        source,
        provider_id=provider_id,
    )
    layout = get_storage_layout(provider_id)

    edges = [
        (
            int(row["pivot_index"]),
            int(column),
        )
        for row in report.get("rows") or []
        for column in row.get("factor_columns") or []
    ]

    expected_rows = list(range(layout.scalar_count))
    actual_rows = [
        int(row["pivot_index"])
        for row in report.get("rows") or []
    ]
    errors = list(report.get("errors") or [])

    if actual_rows != expected_rows:
        errors.append("factor-row-order-mismatch")

    return {
        "format": FORMAT,
        "version": 1,
        "provider_id": provider_id,
        "scalar_count": layout.scalar_count,
        "edge_count": len(set(edges)),
        "edges": [
            {"pivot_index": pivot, "column": column}
            for pivot, column in sorted(set(edges))
        ],
        "source_ready": report.get("ready") is True,
        "ready": not errors,
        "errors": errors,
    }


def check_source_pattern_admissibility(
    matrix: Sequence[Sequence[float]],
    source_pattern: dict[str, Any],
    *,
    symmetry_tolerance: float = 1e-10,
    factor_tolerance: float = 1e-12,
    pivot_tolerance: float = 1e-14,
) -> dict[str, Any]:
    edges = {
        (
            int(item["pivot_index"]),
            int(item["column"]),
        )
        for item in source_pattern.get("edges") or []
    }
    return compare_factor_pattern(
        matrix,
        edges,
        symmetry_tolerance=symmetry_tolerance,
        factor_tolerance=factor_tolerance,
        pivot_tolerance=pivot_tolerance,
    )


def solve_with_source_pattern(
    matrix: Sequence[Sequence[float]],
    rhs: Sequence[float],
    source_pattern: dict[str, Any],
    *,
    symmetry_tolerance: float = 1e-10,
    factor_tolerance: float = 1e-12,
    pivot_tolerance: float = 1e-14,
) -> list[float]:
    """Solve only when the runtime matrix passes the source-pattern gate."""
    if source_pattern.get("ready") is not True:
        raise ValueError("source factor pattern is not ready")

    edges = {
        (
            int(item["pivot_index"]),
            int(item["column"]),
        )
        for item in source_pattern.get("edges") or []
    }
    return solve_guided(
        matrix,
        rhs,
        factor_edges=edges,
        symmetry_tolerance=symmetry_tolerance,
        factor_tolerance=factor_tolerance,
        pivot_tolerance=pivot_tolerance,
    )


def build_source_pattern_executor_contract(
    source: str,
) -> dict[str, Any]:
    providers: list[dict[str, Any]] = []
    for provider_id in (0, 1):
        pattern = extract_source_factor_edges(
            source,
            provider_id=provider_id,
        )
        providers.append(pattern)

    return {
        "format": FORMAT,
        "version": 1,
        "source_file": "SHIFT.exe.c",
        "providers": providers,
        "pipeline": [
            "retail source",
            "factor pattern extractor",
            "source factor edge contract",
            "dense factor support admissibility gate",
            "sparse-guided numeric executor",
        ],
        "status": "experimental-source-pattern-executor-adapter",
        "limitations": [
            "The source-derived pattern is a candidate structural mask, not a proof of retail numerical identity.",
            "A logical matrix must pass dense support admissibility before sparse-guided execution.",
            "Packed workspace address mapping and runtime capture parity remain separate.",
        ],
    }
