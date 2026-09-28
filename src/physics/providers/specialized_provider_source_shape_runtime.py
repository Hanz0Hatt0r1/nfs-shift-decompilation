"""Compact source-shape contract for the fully unrolled provider solvers.

The shape records exact reciprocal pivot order and loop families observed in the
retail Ghidra source. It is intentionally coefficient-free and independent of
the packed workspace numeric mapping.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from specialized_provider_solver_fingerprint_runtime import (
    extract_function_body,
    extract_reciprocal_pivots,
)

FORMAT = "SHIFT.SpecializedProviderSourceShapeRuntime/1"

PROVIDER_SPECS = {
    0: {
        "function": "FUN_007c7200",
        "next_function_marker": "undefined4 * __fastcall FUN_007cd980",
        "expected_scalar_count": 40,
    },
    1: {
        "function": "FUN_007cdfc0",
        "next_function_marker": "undefined * __fastcall FUN_007d2e70",
        "expected_scalar_count": 34,
    },
}


def build_source_shape(
    source: str,
    *,
    provider_id: int,
) -> dict[str, Any]:
    try:
        spec = PROVIDER_SPECS[int(provider_id)]
    except KeyError as exc:
        raise ValueError(f"unsupported provider id: {provider_id}") from exc

    body, start_line = extract_function_body(
        source,
        spec["function"],
        next_function_marker=spec["next_function_marker"],
    )
    pivots = extract_reciprocal_pivots(
        body.splitlines(),
        first_source_line=start_line,
    )

    loop_families: Counter[tuple[int, int]] = Counter()
    for pivot in pivots:
        loop_families.update(pivot.loop_ranges)

    errors: list[str] = []
    if len(pivots) != spec["expected_scalar_count"]:
        errors.append(
            "pivot-count:"
            f"expected={spec['expected_scalar_count']}:actual={len(pivots)}"
        )

    return {
        "format": FORMAT,
        "version": 1,
        "provider_id": int(provider_id),
        "function": spec["function"],
        "source_start_line": start_line,
        "source_line_count": len(body.splitlines()),
        "scalar_count": int(spec["expected_scalar_count"]),
        "pivot_count": len(pivots),
        "pivot_denominators": [pivot.denominator for pivot in pivots],
        "loop_family_counts": [
            {
                "start": int(start),
                "end": int(end),
                "count": int(count),
            }
            for (start, end), count in sorted(
                loop_families.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ],
        "pivot_loop_counts": [
            {
                "pivot_index": int(pivot.index),
                "denominator": pivot.denominator,
                "loop_count": len(pivot.loop_ranges),
            }
            for pivot in pivots
        ],
        "ready": not errors,
        "errors": errors,
    }


def summarize_source_shape(report: dict[str, Any]) -> dict[str, Any]:
    families = report.get("loop_family_counts") or []
    return {
        "provider_id": report.get("provider_id"),
        "scalar_count": report.get("scalar_count"),
        "pivot_count": report.get("pivot_count"),
        "unique_loop_families": len(families),
        "loop_headers_total": sum(
            int(item.get("count", 0))
            for item in families
        ),
        "ready": bool(report.get("ready")),
    }


def validate_source_shape(report: dict[str, Any]) -> dict[str, Any]:
    errors = list(report.get("errors") or [])
    scalar_count = int(report.get("scalar_count", 0))
    if int(report.get("pivot_count", 0)) != scalar_count:
        errors.append("pivot-count-does-not-match-scalar-count")

    denominators = list(report.get("pivot_denominators") or [])
    if len(denominators) != scalar_count:
        errors.append("pivot-denominator-list-length-mismatch")
    if len(denominators) != len(set(denominators)):
        errors.append("pivot-denominators-not-unique")

    for item in report.get("loop_family_counts") or []:
        start = int(item.get("start", -1))
        end = int(item.get("end", -1))
        count = int(item.get("count", 0))
        if start < 0 or end <= start:
            errors.append(f"invalid-loop-family:{start}:{end}")
        if count <= 0:
            errors.append(f"invalid-loop-family-count:{start}:{end}")

    return {
        "format": "SHIFT.SpecializedProviderSourceShapeValidation/1",
        "version": 1,
        "provider_id": report.get("provider_id"),
        "ready": not errors,
        "errors": list(dict.fromkeys(errors)),
    }


def build_source_shape_contract(source: str) -> dict[str, Any]:
    providers: list[dict[str, Any]] = []
    for provider_id in (0, 1):
        report = build_source_shape(
            source,
            provider_id=provider_id,
        )
        report["summary"] = summarize_source_shape(report)
        report["validation"] = validate_source_shape(report)
        providers.append(report)

    return {
        "format": FORMAT,
        "version": 1,
        "source_file": "SHIFT.exe.c",
        "providers": providers,
        "status": "source-backed-specialized-provider-source-shape",
        "limitations": [
            "Loop-family counts describe source syntax only and are not runtime iteration counts.",
            "No numeric coefficient or packed-workspace semantic is inferred.",
        ],
    }


__all__ = [
    "FORMAT",
    "PROVIDER_SPECS",
    "build_source_shape",
    "summarize_source_shape",
    "validate_source_shape",
    "build_source_shape_contract",
]
