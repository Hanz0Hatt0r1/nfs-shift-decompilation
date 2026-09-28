"""Extract the future-column factor pattern from specialized SHIFT solver source.

For pivot i, FUN_007c7200/FUN_007cdfc0 write normalized coefficients into the
current row's static factor segment. The parser identifies loop writes and direct
writes whose destination belongs to that exact row segment, then retains only
columns > i. This yields the unrolled factor sparsity pattern without copying
the proprietary source.
"""
from __future__ import annotations

import re
from typing import Any

from specialized_provider_row_storage_runtime import (
    get_row_pointers,
    get_storage_layout,
)
from specialized_provider_solver_fingerprint_runtime import extract_function_body
from specialized_provider_solver_fingerprint_runtime import extract_reciprocal_pivots

FORMAT = "SHIFT.SpecializedProviderFactorPatternRuntime/1"

SOLVER_SPECS = {
    0: {
        "function": "FUN_007c7200",
        "next_function_marker": "undefined4 * __fastcall FUN_007cd980",
    },
    1: {
        "function": "FUN_007cdfc0",
        "next_function_marker": "undefined * __fastcall FUN_007d2e70",
    },
}

LOOP_HEADER_RE = re.compile(
    r"for\s*\(\s*local_10\s*=\s*(0x[0-9A-Fa-f]+|\d+)\s*;\s*"
    r"local_10\s*<\s*(0x[0-9A-Fa-f]+|\d+)\s*;"
)

LOOP_LHS_RE = re.compile(
    r"\*\(double \*\)\(&DAT_([0-9A-Fa-f]+)\s*\+\s*local_10\s*\*\s*8\)"
)

ARRAY_LHS_RE = re.compile(
    r"\(&DAT_([0-9A-Fa-f]+)\)\[local_10\]\s*="
)

DIRECT_LHS_RE = re.compile(
    r"^\s*(?:_)?DAT_([0-9A-Fa-f]+)\s*="
)


def _int(value: str) -> int:
    return int(value, 0)


def _function_spec(provider_id: int) -> dict[str, Any]:
    try:
        return dict(SOLVER_SPECS[provider_id])
    except KeyError as exc:
        raise ValueError(f"unsupported provider id: {provider_id}") from exc


def _assignment_statements_with_loops(
    lines: list[str],
) -> tuple[tuple[int, str, tuple[int, int] | None], ...]:
    """Collect assignment statements while retaining local_10 loop bounds."""
    statements: list[tuple[int, str, tuple[int, int] | None]] = []
    active_range: tuple[int, int] | None = None
    brace_depth = 0
    active_depth: int | None = None

    for index, line in enumerate(lines):
        loop = LOOP_HEADER_RE.search(line)
        if loop:
            active_range = (_int(loop.group(1)), _int(loop.group(2)))
            active_depth = brace_depth + 1

        if (
            LOOP_LHS_RE.search(line)
            or ARRAY_LHS_RE.search(line)
            or DIRECT_LHS_RE.match(line)
        ):
            statement = line.strip()
            cursor = index
            while ";" not in statement and cursor + 1 < len(lines):
                cursor += 1
                statement += " " + lines[cursor].strip()
            statements.append((index, statement, active_range))

        brace_depth += line.count("{") - line.count("}")
        if (
            active_range is not None
            and active_depth is not None
            and brace_depth < active_depth
        ):
            active_range = None
            active_depth = None

    return tuple(statements)


def _lhs_match(statement: str) -> re.Match[str] | None:
    return (
        LOOP_LHS_RE.search(statement)
        or ARRAY_LHS_RE.search(statement)
        or DIRECT_LHS_RE.match(statement)
    )


def _expanded_factor_targets(
    lines: list[str],
    *,
    row_base: int,
    pivot_index: int,
    scalar_count: int,
    output_vector_base: int,
    output_vector_bytes: int,
) -> set[int]:
    """Recover factor destinations from the pre-output normalization prefix."""
    targets: set[int] = set()

    for _, statement, loop_range in _assignment_statements_with_loops(lines):
        match = _lhs_match(statement)
        if match is None:
            continue

        lhs_form = (
            "loop"
            if LOOP_LHS_RE.search(statement)
            else "array"
            if ARRAY_LHS_RE.search(statement)
            else "direct"
        )
        rhs = statement[match.end():]

        destinations: tuple[int, ...]
        if lhs_form in {"loop", "array"}:
            base = int(match.group(1), 16)
            if loop_range is None:
                continue
            destinations = tuple(
                base + local_10 * 8
                for local_10 in range(*loop_range)
            )
        else:
            destinations = (int(match.group(1), 16),)

        if any(
            output_vector_base <= address < output_vector_base + output_vector_bytes
            for address in destinations
        ):
            break

        if "dVar1" not in rhs:
            continue

        if lhs_form in {"loop", "array"}:
            base = int(match.group(1), 16)
            if base != row_base or loop_range is None:
                continue
            targets.update(
                local_10
                for local_10 in range(*loop_range)
                if pivot_index < local_10 < scalar_count
            )
            continue

        address = destinations[0]
        delta = address - row_base
        if delta >= 0 and delta % 8 == 0:
            column = delta // 8
            if pivot_index < column < scalar_count:
                targets.add(column)

    return targets


def extract_factor_pattern(
    source: str,
    *,
    provider_id: int,
) -> dict[str, Any]:
    spec = _function_spec(provider_id)
    body, source_start_line = extract_function_body(
        source,
        spec["function"],
        next_function_marker=spec["next_function_marker"],
    )
    pivots = extract_reciprocal_pivots(
        body.splitlines(),
        first_source_line=source_start_line,
    )
    pointers = get_row_pointers(provider_id)
    layout = get_storage_layout(provider_id)

    errors: list[str] = []
    if len(pivots) != layout.scalar_count:
        errors.append(
            f"pivot-count:expected={layout.scalar_count}:actual={len(pivots)}"
        )

    rows: list[dict[str, Any]] = []
    for i, pivot in enumerate(pivots):
        if i >= len(pointers):
            break
        next_address = (
            pointers[i + 1]
            if i + 1 < len(pointers)
            else layout.output_vector_base
        )
        segment_doubles = (next_address - pointers[i]) // 8
        next_pivot_line = (
            pivots[i + 1].source_line
            if i + 1 < len(pivots)
            else source_start_line + len(body.splitlines())
        )
        block = body.splitlines()[
            pivot.source_line - source_start_line:
            next_pivot_line - source_start_line
        ]
        columns = sorted(
            _expanded_factor_targets(
                block,
                row_base=pointers[i],
                pivot_index=i,
                scalar_count=layout.scalar_count,
                output_vector_base=layout.output_vector_base,
                output_vector_bytes=layout.output_vector_bytes,
            )
        )
        out_of_range = [
            column
            for column in columns
            if column < 0 or column >= layout.scalar_count
        ]
        if out_of_range:
            errors.append(f"pivot-{i}-factor-column-out-of-domain")
        rows.append(
            {
                "pivot_index": i,
                "source_line": pivot.source_line,
                "row_pointer": hex(pointers[i]),
                "row_segment_doubles": segment_doubles,
                "factor_columns": columns,
                "factor_column_count": len(columns),
                "pivot_diagonal_address": hex(pointers[i] + i * 8),
            }
        )

    return {
        "format": FORMAT,
        "version": 1,
        "provider_id": provider_id,
        "function": spec["function"],
        "source_start_line": source_start_line,
        "source_line_count": len(body.splitlines()),
        "scalar_count": layout.scalar_count,
        "rows": rows,
        "ready": not errors,
        "errors": errors,
    }


def summarize_factor_pattern(report: dict[str, Any]) -> dict[str, Any]:
    rows = report.get("rows") or []
    return {
        "provider_id": report.get("provider_id"),
        "scalar_count": report.get("scalar_count"),
        "rows": len(rows),
        "total_factor_edges": sum(
            int(row.get("factor_column_count", 0)) for row in rows
        ),
        "max_factor_column_count": max(
            (int(row.get("factor_column_count", 0)) for row in rows),
            default=0,
        ),
        "rows_with_no_future_factors": [
            int(row["pivot_index"])
            for row in rows
            if int(row.get("factor_column_count", 0)) == 0
        ],
        "max_factor_column_by_row": [
            (
                max(row["factor_columns"])
                if row.get("factor_columns")
                else int(row["pivot_index"])
            )
            for row in rows
        ],
        "ready": bool(report.get("ready")),
    }


def validate_factor_pattern(report: dict[str, Any]) -> dict[str, Any]:
    errors = list(report.get("errors") or [])
    rows = report.get("rows") or []
    expected_count = int(report.get("scalar_count", 0))
    if len(rows) != expected_count:
        errors.append(f"row-count:expected={expected_count}:actual={len(rows)}")

    for row in rows:
        pivot = int(row["pivot_index"])
        columns = [int(v) for v in row.get("factor_columns") or []]
        if columns != sorted(set(columns)):
            errors.append(f"pivot-{pivot}-columns-not-sorted-unique")
        if any(column <= pivot for column in columns):
            errors.append(f"pivot-{pivot}-contains-non-future-column")
        if any(column >= expected_count for column in columns):
            errors.append(f"pivot-{pivot}-column-exceeds-scalar-domain")
        if str(row["pivot_diagonal_address"]) != hex(
            int(row["row_pointer"], 16) + pivot * 8
        ):
            errors.append(f"pivot-{pivot}-diagonal-mismatch")

    return {
        "format": "SHIFT.SpecializedProviderFactorPatternValidation/1",
        "version": 1,
        "ready": not errors,
        "errors": errors,
        "rows": len(rows),
    }


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--provider", type=int, choices=(0, 1), required=True)
    args = parser.parse_args()

    report = extract_factor_pattern(
        args.source.read_text(encoding="utf-8"),
        provider_id=args.provider,
    )
    report["summary"] = summarize_factor_pattern(report)
    report["validation"] = validate_factor_pattern(report)
    print(json.dumps(report, indent=2, sort_keys=True))
    raise SystemExit(0 if report["validation"]["ready"] else 2)
