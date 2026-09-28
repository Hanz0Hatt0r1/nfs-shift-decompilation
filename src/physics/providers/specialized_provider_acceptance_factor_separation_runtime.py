"""Compare specialized-provider acceptance sparsity with factor-write topology.

Phase 454 keeps two independently observed structures separate:
the acceptance helper's strict-upper matrix mask and the provider solver's
source-derived normalized-factor destinations.

A difference is reported as expected structural divergence, not treated as an
error. The acceptance mask describes the matrix state consumed by the probe;
factor edges describe writes performed during the solver.
"""
from __future__ import annotations

from typing import Any

from specialized_provider_factor_pattern_runtime import extract_factor_pattern
from specialized_provider_runtime import provider_signature
from specialized_provider_storage_runtime import get_storage_layout

FORMAT = "SHIFT.SpecializedProviderAcceptanceFactorSeparationRuntime/1"


def acceptance_edges(provider_id: int) -> set[tuple[int, int]]:
    layout = get_storage_layout(provider_id)
    bits = provider_signature(provider_id)
    edges: set[tuple[int, int]] = set()
    cursor = 0
    for row in range(layout.scalar_count):
        for column in range(row + 1, layout.scalar_count):
            if bits[cursor]:
                edges.add((row, column))
            cursor += 1
    if cursor != len(bits):
        raise ValueError("acceptance signature cursor mismatch")
    return edges


def factor_edges_from_report(report: dict[str, Any]) -> set[tuple[int, int]]:
    edges: set[tuple[int, int]] = set()
    for row in report.get("rows") or []:
        pivot = int(row["pivot_index"])
        for column in row.get("factor_columns") or []:
            edges.add((pivot, int(column)))
    return edges


def compare_acceptance_and_factor(
    source: str,
    *,
    provider_id: int,
) -> dict[str, Any]:
    layout = get_storage_layout(provider_id)
    factor_report = extract_factor_pattern(
        source,
        provider_id=provider_id,
    )
    acceptance = acceptance_edges(provider_id)
    factor = factor_edges_from_report(factor_report)

    errors = list(factor_report.get("errors") or [])
    invalid_factor = {
        (row, column)
        for row, column in factor
        if not (0 <= row < column < layout.scalar_count)
    }
    if invalid_factor:
        errors.append(
            f"invalid-factor-edges:{len(invalid_factor)}"
        )

    return {
        "format": FORMAT,
        "version": 1,
        "provider_id": provider_id,
        "scalar_count": layout.scalar_count,
        "acceptance_edge_count": len(acceptance),
        "factor_edge_count": len(factor),
        "overlap_count": len(acceptance & factor),
        "factor_only_count": len(factor - acceptance),
        "acceptance_only_count": len(acceptance - factor),
        "factor_edges": [
            {"row": row, "column": column}
            for row, column in sorted(factor)
        ],
        "acceptance_only_edges_sample": [
            {"row": row, "column": column}
            for row, column in sorted(acceptance - factor)[:64]
        ],
        "factor_only_edges_sample": [
            {"row": row, "column": column}
            for row, column in sorted(factor - acceptance)[:64]
        ],
        "relationship": "distinct-structural-domains",
        "ready": not errors,
        "errors": errors,
    }


def summarize_comparison(report: dict[str, Any]) -> dict[str, Any]:
    acceptance = int(report.get("acceptance_edge_count", 0))
    factor = int(report.get("factor_edge_count", 0))
    overlap = int(report.get("overlap_count", 0))
    union = acceptance + factor - overlap
    return {
        "provider_id": report.get("provider_id"),
        "scalar_count": report.get("scalar_count"),
        "acceptance_edges": acceptance,
        "factor_edges": factor,
        "overlap": overlap,
        "factor_only": int(report.get("factor_only_count", 0)),
        "acceptance_only": int(report.get("acceptance_only_count", 0)),
        "union": union,
        "jaccard": (overlap / union) if union else 1.0,
        "ready": bool(report.get("ready")),
    }


def validate_comparison(report: dict[str, Any]) -> dict[str, Any]:
    errors = list(report.get("errors") or [])
    expected = int(report.get("scalar_count", 0))

    if int(report.get("acceptance_edge_count", 0)) < 0:
        errors.append("negative-acceptance-edge-count")
    if int(report.get("factor_edge_count", 0)) < 0:
        errors.append("negative-factor-edge-count")
    if int(report.get("overlap_count", 0)) > min(
        int(report.get("acceptance_edge_count", 0)),
        int(report.get("factor_edge_count", 0)),
    ):
        errors.append("overlap-exceeds-input-sets")

    for edge in report.get("factor_edges") or []:
        row = int(edge["row"])
        column = int(edge["column"])
        if not (0 <= row < column < expected):
            errors.append(
                f"invalid-factor-edge:{row},{column}"
            )

    return {
        "format": "SHIFT.SpecializedProviderAcceptanceFactorSeparationValidation/1",
        "version": 1,
        "provider_id": report.get("provider_id"),
        "ready": not errors,
        "errors": errors,
    }


def build_separation_contract(source: str) -> dict[str, Any]:
    providers: list[dict[str, Any]] = []
    for provider_id in (0, 1):
        report = compare_acceptance_and_factor(
            source,
            provider_id=provider_id,
        )
        report["summary"] = summarize_comparison(report)
        report["validation"] = validate_comparison(report)
        providers.append(report)

    return {
        "format": FORMAT,
        "version": 1,
        "source_file": "SHIFT.exe.c",
        "providers": providers,
        "interpretation": {
            "acceptance_mask": "strict-upper sparsity signature consumed by the provider acceptance helper",
            "factor_pattern": "source-derived normalized-factor destination pattern from the provider solve function",
            "comparison": "descriptive only; no equality or subset relation is required",
        },
        "limitations": [
            "The two edge sets are intentionally not treated as the same matrix.",
            "Factor edge coordinates depend on source-context extraction and remain an implementation topology, not a semantic matrix label.",
            "No numerical values or physical units are inferred.",
        ],
        "status": "source-backed-acceptance-factor-separation",
    }


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()

    contract = build_separation_contract(
        args.source.read_text(encoding="utf-8")
    )
    print(json.dumps(contract, indent=2, sort_keys=True))
    ready = all(
        provider["validation"]["ready"]
        for provider in contract["providers"]
    )
    raise SystemExit(0 if ready else 2)
