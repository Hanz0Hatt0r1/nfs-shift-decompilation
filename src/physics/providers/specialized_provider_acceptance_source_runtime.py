"""Regenerate specialized-provider acceptance RLE arrays from retail C source.

FUN_007c6e50 and FUN_007cdb40 embed their strict-upper sparsity signatures as
contiguous local short arrays. This module extracts those array writes and can
compare them with the static signatures stored in specialized_provider_runtime.
"""
from __future__ import annotations

import re
from typing import Any

from specialized_provider_solver_fingerprint_runtime import extract_function_body
from specialized_provider_runtime import get_provider

FORMAT = "SHIFT.SpecializedProviderAcceptanceSourceRuntime/1"

ACCEPTANCE_SPECS = {
    0: {
        "function": "FUN_007c6e50",
        "local_array": "local_b4",
        "scalar_count": 40,
        "expected_rle_count": 83,
    },
    1: {
        "function": "FUN_007cdb40",
        "local_array": "local_e4",
        "scalar_count": 34,
        "expected_rle_count": 107,
    },
}

ARRAY_WRITE_TEMPLATE = re.compile(
    r"{name}\[(0x[0-9A-Fa-f]+|\d+)\]\s*=\s*(0x[0-9A-Fa-f]+|\d+);"
)


def extract_rle_array(function_body: str, local_array: str) -> tuple[int, ...]:
    pattern = re.compile(
        ARRAY_WRITE_TEMPLATE.pattern.format(name=re.escape(local_array))
    )
    values: dict[int, int] = {}
    for match in pattern.finditer(function_body):
        index = int(match.group(1), 0)
        value = int(match.group(2), 0)
        if index in values and values[index] != value:
            raise ValueError(f"duplicate array index with conflicting value: {index}")
        values[index] = value

    if not values:
        raise ValueError(f"no writes found for {local_array}")

    max_index = max(values)
    missing = [index for index in range(max_index + 1) if index not in values]
    if missing:
        raise ValueError(f"missing array indexes: {missing[:8]}")

    runs = tuple(values[index] for index in range(max_index + 1))
    if any(value < 0 for value in runs):
        raise ValueError("RLE values must be non-negative")
    return runs


def validate_rle_shape(
    runs: tuple[int, ...],
    scalar_count: int,
    expected_count: int | None = None,
) -> dict[str, Any]:
    n = int(scalar_count)
    errors: list[str] = []
    if expected_count is not None and len(runs) != int(expected_count):
        errors.append(
            f"rle-entry-count:expected={expected_count}:actual={len(runs)}"
        )
    decoded_length = sum(runs) + max(0, len(runs) - 1)
    expected_cells = n * (n - 1) // 2
    if decoded_length != expected_cells:
        errors.append(
            f"decoded-cell-count:expected={expected_cells}:actual={decoded_length}"
        )
    return {
        "ready": not errors,
        "errors": errors,
        "rle_entry_count": len(runs),
        "decoded_cells": decoded_length,
        "expected_cells": expected_cells,
    }


def extract_provider_acceptance_source(
    source: str,
    *,
    provider_id: int,
    next_function_marker: str | None = None,
) -> dict[str, Any]:
    try:
        spec = dict(ACCEPTANCE_SPECS[provider_id])
    except KeyError as exc:
        raise ValueError(f"unsupported provider id: {provider_id}") from exc

    body, source_start_line = extract_function_body(
        source,
        spec["function"],
        next_function_marker=next_function_marker,
    )
    runs = extract_rle_array(body, spec["local_array"])
    shape = validate_rle_shape(
        runs,
        spec["scalar_count"],
        expected_count=spec["expected_rle_count"],
    )
    static = get_provider(provider_id).rle
    return {
        "format": FORMAT,
        "version": 1,
        "provider_id": provider_id,
        "function": spec["function"],
        "local_array": spec["local_array"],
        "source_start_line": source_start_line,
        "source_line_count": len(body.splitlines()),
        "rle": list(runs),
        "shape": shape,
        "matches_static_signature": runs == static,
        "ready": shape["ready"] and runs == static,
        "errors": ([] if shape["ready"] else list(shape["errors"]))
        + ([] if runs == static else ["static-rle-mismatch"]),
    }


def build_provider_acceptance_contract(
    source: str,
    *,
    provider_id: int | None = None,
    next_function_markers: dict[int, str] | None = None,
) -> dict[str, Any]:
    ids = (provider_id,) if provider_id is not None else (0, 1)
    results = []
    for item in ids:
        marker = (next_function_markers or {}).get(item)
        results.append(
            extract_provider_acceptance_source(
                source,
                provider_id=item,
                next_function_marker=marker,
            )
        )
    return {
        "format": FORMAT,
        "version": 1,
        "providers": results,
        "status": "source-backed-acceptance-rle",
        "limitations": [
            "This extracts the source literal RLE arrays and validates their shape; it does not infer the semantic meaning of the accepted graph beyond the retail comparison routine.",
        ],
    }


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--provider", type=int, choices=(0, 1))
    parser.add_argument("--next-function")
    args = parser.parse_args()

    payload = build_provider_acceptance_contract(
        args.source.read_text(encoding="utf-8"),
        provider_id=args.provider,
        next_function_markers=(
            {args.provider: args.next_function}
            if args.provider is not None and args.next_function
            else None
        ),
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    raise SystemExit(0 if all(item["ready"] for item in payload["providers"]) else 2)
