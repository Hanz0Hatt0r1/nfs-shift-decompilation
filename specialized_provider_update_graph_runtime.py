"""Source-derived workspace update graph for the two specialized SHIFT solvers.

The retail provider solvers are fully unrolled. This module does not copy their
numeric expressions; it resolves the left-hand-side workspace addresses in each
pivot block into provider row/column coordinates.

The result is a structural write graph: exact workspace cells written by each
pivot block, grouped by row relation (current/future/prior). It is intentionally
not presented as a semantic matrix graph or a reconstructed solver implementation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

from specialized_provider_factor_pattern_runtime import extract_factor_pattern
from specialized_provider_row_storage_runtime import (
    build_row_segments,
    get_storage_layout,
)
from specialized_provider_solver_fingerprint_runtime import (
    extract_function_body,
    extract_reciprocal_pivots,
)

FORMAT = "SHIFT.SpecializedProviderUpdateGraph/1"

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

LOOP_PTR_LHS_RE = re.compile(
    r"\*\(double \*\)\(&DAT_([0-9A-Fa-f]+)\s*\+\s*local_10\s*\*\s*8\)\s*="
)

ARRAY_LHS_RE = re.compile(
    r"\(&DAT_([0-9A-Fa-f]+)\)\[local_10\]\s*="
)

DIRECT_LHS_RE = re.compile(
    r"^\s*(?:_)?DAT_([0-9A-Fa-f]+)\s*="
)


@dataclass(frozen=True)
class WorkspaceCell:
    row: int
    column: int


@dataclass(frozen=True)
class WorkspaceWrite:
    source_line: int
    cell: WorkspaceCell
    access: str


def _parse_int(value: str) -> int:
    return int(value, 0)


def _function_spec(provider_id: int) -> dict[str, Any]:
    try:
        return dict(SOLVER_SPECS[provider_id])
    except KeyError as exc:
        raise ValueError(f"unsupported provider id: {provider_id}") from exc


def _locate_workspace_cell(address: int, segments: Iterable[Any]) -> WorkspaceCell | None:
    for segment in segments:
        if segment.start <= address < segment.end:
            delta = address - segment.start
            if delta % 8:
                return None
            return WorkspaceCell(segment.row, delta // 8)
    return None


def _extract_workspace_writes(
    lines: list[str],
    *,
    first_source_line: int,
    segments: Iterable[Any],
) -> tuple[WorkspaceWrite, ...]:
    """Resolve workspace LHS writes, including flat array writes crossing segments."""
    segment_list = tuple(segments)
    active_range: tuple[int, int] | None = None
    active_depth: int | None = None
    brace_depth = 0
    writes: list[WorkspaceWrite] = []

    def emit(address: int, source_line: int, access: str) -> None:
        cell = _locate_workspace_cell(address, segment_list)
        if cell is not None:
            writes.append(
                WorkspaceWrite(
                    source_line=source_line,
                    cell=cell,
                    access=access,
                )
            )

    for offset, line in enumerate(lines):
        source_line = first_source_line + offset
        loop_match = LOOP_HEADER_RE.search(line)
        if loop_match:
            active_range = (
                _parse_int(loop_match.group(1)),
                _parse_int(loop_match.group(2)),
            )
            active_depth = brace_depth + 1

        loop_match = LOOP_PTR_LHS_RE.search(line)
        if loop_match and active_range is not None:
            base = int(loop_match.group(1), 16)
            for local_10 in range(*active_range):
                emit(base + local_10 * 8, source_line, "loop-pointer-lhs")

        array_match = ARRAY_LHS_RE.search(line)
        if array_match and active_range is not None:
            base = int(array_match.group(1), 16)
            for local_10 in range(*active_range):
                emit(base + local_10 * 8, source_line, "loop-array-lhs")

        direct_match = DIRECT_LHS_RE.match(line)
        if direct_match:
            emit(int(direct_match.group(1), 16), source_line, "direct-lhs")

        brace_depth += line.count("{") - line.count("}")
        if active_range is not None and active_depth is not None and brace_depth < active_depth:
            active_range = None
            active_depth = None

    return tuple(writes)


def _group_target_rows(
    pivot_index: int,
    writes: Iterable[WorkspaceWrite],
) -> tuple[dict[str, Any], ...]:
    grouped: dict[int, set[int]] = {}
    for write in writes:
        if write.cell.row <= pivot_index:
            continue
        grouped.setdefault(write.cell.row, set()).add(write.cell.column)

    return tuple(
        {
            "row": row,
            "columns": sorted(columns),
            "column_count": len(columns),
        }
        for row, columns in sorted(grouped.items())
    )


def extract_update_graph(source: str, *, provider_id: int) -> dict[str, Any]:
    spec = _function_spec(provider_id)
    body, source_start_line = extract_function_body(
        source,
        spec["function"],
        next_function_marker=spec["next_function_marker"],
    )
    body_lines = body.splitlines()
    pivots = extract_reciprocal_pivots(
        body_lines,
        first_source_line=source_start_line,
    )
    layout = get_storage_layout(provider_id)
    segments = build_row_segments(provider_id)
    factor_report = extract_factor_pattern(source, provider_id=provider_id)

    errors: list[str] = []
    if len(pivots) != layout.scalar_count:
        errors.append(
            f"pivot-count:expected={layout.scalar_count}:actual={len(pivots)}"
        )
    if len(segments) != layout.scalar_count:
        errors.append(
            f"segment-count:expected={layout.scalar_count}:actual={len(segments)}"
        )

    rows: list[dict[str, Any]] = []
    for i, pivot in enumerate(pivots):
        if i >= layout.scalar_count:
            break

        next_line = (
            pivots[i + 1].source_line
            if i + 1 < len(pivots)
            else source_start_line + len(body_lines)
        )
        block_start = pivot.source_line - source_start_line
        block_end = next_line - source_start_line
        block_lines = body_lines[block_start:block_end]
        writes = _extract_workspace_writes(
            block_lines,
            first_source_line=pivot.source_line,
            segments=segments,
        )

        unique_cells = {(write.cell.row, write.cell.column) for write in writes}
        factor_columns = sorted(
            {
                column
                for row, column in unique_cells
                if row == i and column > i
            }
        )
        current_nonfuture = sorted(
            {
                column
                for row, column in unique_cells
                if row == i and column <= i
            }
        )
        prior_rows = sorted({row for row, _ in unique_cells if row < i})
        target_rows = _group_target_rows(i, writes)

        expected_factor_row = (
            factor_report.get("rows", [])[i]
            if i < len(factor_report.get("rows", []))
            else None
        )
        expected_factor_columns = (
            sorted(int(value) for value in expected_factor_row.get("factor_columns", []))
            if expected_factor_row is not None
            else []
        )
        if factor_columns != expected_factor_columns:
            errors.append(
                f"pivot-{i}-factor-cross-check-mismatch"
            )

        rows.append(
            {
                "pivot_index": i,
                "source_line": pivot.source_line,
                "workspace_write_site_count": len(writes),
                "workspace_unique_cell_count": len(unique_cells),
                "factor_columns": factor_columns,
                "current_row_nonfuture_columns": current_nonfuture,
                "prior_workspace_rows": prior_rows,
                "target_rows": list(target_rows),
            }
        )

    return {
        "format": FORMAT,
        "version": 1,
        "provider_id": provider_id,
        "function": spec["function"],
        "source_start_line": source_start_line,
        "source_line_count": len(body_lines),
        "scalar_count": layout.scalar_count,
        "rows": rows,
        "ready": not errors,
        "errors": errors,
    }


def summarize_update_graph(report: dict[str, Any]) -> dict[str, Any]:
    rows = report.get("rows") or []
    future_writes = sum(
        sum(int(item.get("column_count", 0)) for item in row.get("target_rows") or [])
        for row in rows
    )
    target_edges = sum(len(row.get("target_rows") or []) for row in rows)
    prior_row_writes = sum(len(row.get("prior_workspace_rows") or []) for row in rows)
    return {
        "provider_id": report.get("provider_id"),
        "scalar_count": report.get("scalar_count"),
        "rows": len(rows),
        "target_row_edges": target_edges,
        "future_target_unique_cell_writes": future_writes,
        "prior_workspace_row_edges": prior_row_writes,
        "workspace_write_sites": sum(
            int(row.get("workspace_write_site_count", 0)) for row in rows
        ),
        "workspace_unique_cells": sum(
            int(row.get("workspace_unique_cell_count", 0)) for row in rows
        ),
        "rows_with_no_future_target": [
            int(row["pivot_index"])
            for row in rows
            if not row.get("target_rows")
        ],
        "ready": bool(report.get("ready")),
    }


def validate_update_graph(report: dict[str, Any]) -> dict[str, Any]:
    errors = list(report.get("errors") or [])
    rows = report.get("rows") or []
    expected_count = int(report.get("scalar_count", 0))
    if len(rows) != expected_count:
        errors.append(f"row-count:expected={expected_count}:actual={len(rows)}")

    for row in rows:
        pivot = int(row["pivot_index"])
        factor_columns = [int(v) for v in row.get("factor_columns") or []]
        if factor_columns != sorted(set(factor_columns)):
            errors.append(f"pivot-{pivot}-factor-columns-not-sorted-unique")
        if any(column <= pivot for column in factor_columns):
            errors.append(f"pivot-{pivot}-factor-column-not-future")

        for target in row.get("target_rows") or []:
            target_row = int(target["row"])
            columns = [int(v) for v in target.get("columns") or []]
            if target_row <= pivot:
                errors.append(f"pivot-{pivot}-invalid-forward-target-row-{target_row}")
            if columns != sorted(set(columns)):
                errors.append(f"pivot-{pivot}-target-{target_row}-columns-not-sorted-unique")

        prior_rows = [int(v) for v in row.get("prior_workspace_rows") or []]
        if pivot != expected_count - 1 and prior_rows:
            errors.append(f"pivot-{pivot}-unexpected-prior-workspace-row-write")

    return {
        "format": "SHIFT.SpecializedProviderUpdateGraphValidation/1",
        "version": 1,
        "provider_id": report.get("provider_id"),
        "ready": not errors,
        "errors": errors,
        "rows": len(rows),
    }


def build_provider_update_graph_contract(source: str) -> dict[str, Any]:
    providers: list[dict[str, Any]] = []
    for provider_id in (0, 1):
        report = extract_update_graph(source, provider_id=provider_id)
        report["summary"] = summarize_update_graph(report)
        report["validation"] = validate_update_graph(report)
        providers.append(report)

    return {
        "format": FORMAT,
        "version": 1,
        "source_file": "SHIFT.exe.c",
        "providers": providers,
        "scope": {
            "representation": "workspace-cell-write graph",
            "coordinate_system": "provider static row/column cells resolved from row-pointer segments",
            "array_lhs_handling": "flat local_10 array writes are resolved by absolute address and may cross row-segment boundaries",
        },
        "limitations": [
            "This phase records source-derived write destinations, not proprietary numeric RHS expressions.",
            "A target row/column write is not asserted to be a semantic sparse-matrix edge by itself.",
            "The final pivot block also contains descending-solution workspace activity; prior-row writes are therefore expected only in the terminal pivot block.",
        ],
        "status": "source-backed-workspace-write-graph",
    }


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()

    contract = build_provider_update_graph_contract(
        args.source.read_text(encoding="utf-8")
    )
    print(json.dumps(contract, indent=2, sort_keys=True))
    ready = all(
        provider["validation"]["ready"]
        for provider in contract["providers"]
    )
    raise SystemExit(0 if ready else 2)
