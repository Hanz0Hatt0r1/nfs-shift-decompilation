"""Extract operator-level signatures from specialized-provider solver assignments.

The retail provider implementations are fully unrolled. This phase classifies
assignment shapes (scale, subtract-product, update-then-scale, etc.) without
emitting proprietary RHS expressions. It is intended to bridge the address-level
dependency graph and a later executable fixed-layout numeric model.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from specialized_provider_rhs_stencil_runtime import (
    SOLVER_SPECS,
    _assignment_statements,
    _find_lhs_match,
)
from specialized_provider_solver_fingerprint_runtime import (
    extract_function_body,
    extract_reciprocal_pivots,
)
from specialized_provider_storage_runtime import get_storage_layout

FORMAT = "SHIFT.SpecializedProviderOperatorSignatureRuntime/1"


def _operator_shape(rhs: str) -> str:
    expression = rhs.strip().rstrip(";").strip()

    if "1.0 /" in expression and "*" not in expression and "-" not in expression:
        return "literal-reciprocal"

    has_subtraction = " - " in expression
    has_multiplication = "*" in expression
    scales_with_pivot = expression.endswith("* dVar1") or expression.endswith("*dVar1")

    if has_subtraction and has_multiplication and scales_with_pivot:
        return "subtract-product-then-scale"
    if has_subtraction and has_multiplication:
        return "subtract-product"
    if has_subtraction:
        return "subtraction"
    if has_multiplication and scales_with_pivot:
        return "scale-or-product-by-pivot"
    if has_multiplication:
        return "product"
    if "/" in expression:
        return "division"
    return "other"


def classify_assignment(statement: str) -> str:
    """Classify only the visible operator shape on the RHS."""
    lhs = _find_lhs_match(statement)
    return _operator_shape(statement[lhs.end():])


def extract_operator_signatures(
    source: str,
    *,
    provider_id: int,
) -> dict[str, Any]:
    try:
        spec = dict(SOLVER_SPECS[provider_id])
    except KeyError as exc:
        raise ValueError(f"unsupported provider id: {provider_id}") from exc

    body, source_start_line = extract_function_body(
        source,
        spec["function"],
        next_function_marker=spec["next_function_marker"],
    )
    lines = body.splitlines()
    pivots = extract_reciprocal_pivots(
        lines,
        first_source_line=source_start_line,
    )
    layout = get_storage_layout(provider_id)

    errors: list[str] = []
    if len(pivots) != layout.scalar_count:
        errors.append(
            f"pivot-count:expected={layout.scalar_count}:actual={len(pivots)}"
        )

    operators: list[dict[str, Any]] = []
    pivot_summaries: list[dict[str, Any]] = []

    for pivot_index, pivot in enumerate(pivots):
        next_line = (
            pivots[pivot_index + 1].source_line
            if pivot_index + 1 < len(pivots)
            else source_start_line + len(lines)
        )
        block_start = pivot.source_line - source_start_line
        block_end = next_line - source_start_line
        block = lines[block_start:block_end]

        counts: Counter[str] = Counter()
        statement_count = 0
        for local_line, statement, _loop_range in _assignment_statements(block):
            operator = classify_assignment(statement)
            counts[operator] += 1
            statement_count += 1
            operators.append(
                {
                    "pivot_index": pivot_index,
                    "source_line": pivot.source_line + local_line,
                    "operator": operator,
                }
            )

        pivot_summaries.append(
            {
                "pivot_index": pivot_index,
                "source_line": pivot.source_line,
                "assignment_count": statement_count,
                "operator_counts": dict(sorted(counts.items())),
            }
        )

    aggregate = Counter(item["operator"] for item in operators)

    return {
        "format": FORMAT,
        "version": 1,
        "provider_id": provider_id,
        "function": spec["function"],
        "source_start_line": source_start_line,
        "source_line_count": len(lines),
        "scalar_count": layout.scalar_count,
        "assignments": operators,
        "pivot_summaries": pivot_summaries,
        "aggregate_operator_counts": dict(sorted(aggregate.items())),
        "ready": not errors,
        "errors": errors,
    }


def summarize_operator_signatures(report: dict[str, Any]) -> dict[str, Any]:
    counts = {
        str(key): int(value)
        for key, value in (report.get("aggregate_operator_counts") or {}).items()
    }
    return {
        "provider_id": report.get("provider_id"),
        "scalar_count": report.get("scalar_count"),
        "assignment_count": len(report.get("assignments") or []),
        "operator_counts": counts,
        "pivots": len(report.get("pivot_summaries") or []),
        "ready": bool(report.get("ready")),
    }


def validate_operator_signatures(report: dict[str, Any]) -> dict[str, Any]:
    errors = list(report.get("errors") or [])
    scalar_count = int(report.get("scalar_count", 0))
    pivots = report.get("pivot_summaries") or []

    if len(pivots) != scalar_count:
        errors.append(
            f"pivot-summary-count:expected={scalar_count}:actual={len(pivots)}"
        )

    for pivot in pivots:
        counts = pivot.get("operator_counts") or {}
        assignment_count = int(pivot.get("assignment_count", 0))
        if sum(int(value) for value in counts.values()) != assignment_count:
            errors.append(
                f"pivot-{pivot.get('pivot_index')}-operator-count-mismatch"
            )
        if int(pivot.get("pivot_index", -1)) < 0:
            errors.append("negative-pivot-index")

    return {
        "format": "SHIFT.SpecializedProviderOperatorSignatureValidation/1",
        "version": 1,
        "provider_id": report.get("provider_id"),
        "ready": not errors,
        "errors": errors,
        "assignments": len(report.get("assignments") or []),
        "pivots": len(pivots),
    }


def build_operator_signature_contract(source: str) -> dict[str, Any]:
    providers: list[dict[str, Any]] = []
    for provider_id in (0, 1):
        report = extract_operator_signatures(
            source,
            provider_id=provider_id,
        )
        report["summary"] = summarize_operator_signatures(report)
        report["validation"] = validate_operator_signatures(report)
        providers.append(report)

    return {
        "format": FORMAT,
        "version": 1,
        "source_file": "SHIFT.exe.c",
        "providers": providers,
        "scope": {
            "representation": "assignment operator-shape signature",
            "expression_text": "omitted",
            "source_order": "preserved at assignment/pivot level",
        },
        "limitations": [
            "The classifier uses decompiler-visible operator tokens and does not reconstruct AST precedence.",
            "A shape such as subtract-product does not assign a semantic matrix operation name.",
            "Literal constants and proprietary numeric operands are intentionally omitted.",
        ],
        "status": "source-backed-operator-signatures",
    }


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()

    contract = build_operator_signature_contract(
        args.source.read_text(encoding="utf-8")
    )
    print(json.dumps(contract, indent=2, sort_keys=True))
    ready = all(
        provider["validation"]["ready"]
        for provider in contract["providers"]
    )
    raise SystemExit(0 if ready else 2)
