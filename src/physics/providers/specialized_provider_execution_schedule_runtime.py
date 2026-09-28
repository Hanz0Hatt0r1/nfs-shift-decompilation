"""Extract the observed execution schedule of specialized SHIFT provider solvers.

Phase 445 records source-order events around each reciprocal pivot without
reconstructing proprietary numeric expressions. The terminal pivot is kept as a
separate back-substitution block. Destination addresses are retained only as
structural evidence: workspace packing remains a distinct unresolved boundary.
"""
from __future__ import annotations

import re
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

FORMAT = "SHIFT.SpecializedProviderExecutionScheduleRuntime/1"

DIRECT_LHS_RE = re.compile(
    r"^\s*(?:_)?DAT_([0-9A-Fa-f]+)\s*="
)
LOOP_PTR_RE = re.compile(
    r"\*\(double \*\)\(&DAT_([0-9A-Fa-f]+)\s*\+\s*local_10\s*\*\s*8\)"
)
ARRAY_RE = re.compile(
    r"\(&DAT_([0-9A-Fa-f]+)\)\[local_10\]"
)

def _function_spec(provider_id: int) -> dict[str, Any]:
    try:
        return dict(SOLVER_SPECS[provider_id])
    except KeyError as exc:
        raise ValueError(f"unsupported provider id: {provider_id}") from exc



def _lhs_address(statement: str, loop_index: int | None) -> int | None:
    direct = DIRECT_LHS_RE.match(statement)
    if direct is not None:
        return int(direct.group(1), 16)

    pointer = LOOP_PTR_RE.search(statement)
    if pointer is not None and loop_index is not None:
        return int(pointer.group(1), 16) + loop_index * 8

    array = ARRAY_RE.search(statement)
    if array is not None and loop_index is not None:
        return int(array.group(1), 16) + loop_index * 8

    return None


def _lhs_base(statement: str) -> int | None:
    direct = DIRECT_LHS_RE.match(statement)
    if direct is not None:
        return int(direct.group(1), 16)

    pointer = LOOP_PTR_RE.search(statement)
    if pointer is not None:
        return int(pointer.group(1), 16)

    array = ARRAY_RE.search(statement)
    if array is not None:
        return int(array.group(1), 16)

    return None


def _output_vector_base(provider_id: int) -> int:
    return get_storage_layout(provider_id).output_vector_base


def _classify_assignment(
    statement: str,
    *,
    provider_id: int,
    loop_index: int | None,
    terminal: bool,
    current_pivot_diagonal: int | None = None,
    future_pivot_diagonals: set[int] | None = None,
) -> str:
    lhs = _lhs_address(statement, loop_index)
    lhs_base = _lhs_base(statement)
    output_base = _output_vector_base(provider_id)
    output_end = output_base + get_storage_layout(provider_id).output_vector_bytes

    if terminal:
        if lhs is not None and output_base <= lhs < output_end:
            return "backsubstitution"
        if lhs_base == output_base:
            return "backsubstitution"

    rhs = statement[
        (
            _find_lhs_match(statement)
        ).end():
    ]

    if lhs is not None and output_base <= lhs < output_end:
        return "forward-rhs"

    if lhs_base == output_base:
        return "forward-rhs"

    if "dVar1" in rhs:
        return "factor-normalization"

    return "workspace-or-global-update"


def extract_execution_schedule(
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

    blocks: list[dict[str, Any]] = []
    for pivot_index, pivot in enumerate(pivots):
        next_line = (
            pivots[pivot_index + 1].source_line
            if pivot_index + 1 < len(pivots)
            else source_start_line + len(lines)
        )
        block_start = pivot.source_line - source_start_line
        block_end = next_line - source_start_line
        block = lines[block_start:block_end]

        terminal = pivot_index == layout.scalar_count - 1
        events: list[dict[str, Any]] = []

        events.append(
            {
                "kind": "pivot-reciprocal",
                "source_line": pivot.source_line,
                "pivot_index": pivot_index,
                "denominator": pivot.denominator,
            }
        )

        for local_line, statement, loop_range in _assignment_statements(block):
            absolute_line = pivot.source_line + local_line
            loop_values = (
                tuple(range(*loop_range))
                if loop_range is not None
                else (None,)
            )
            for loop_index in loop_values:
                if not pivot.denominator.startswith("_DAT_"):
                    errors.append(
                        f"pivot-{pivot_index}-invalid-denominator:{pivot.denominator}"
                    )
                    continue
                kind = _classify_assignment(
                    statement,
                    provider_id=provider_id,
                    loop_index=loop_index,
                    terminal=terminal,
                )
                event: dict[str, Any] = {
                    "kind": kind,
                    "source_line": absolute_line,
                }
                if loop_index is not None:
                    event["loop_index"] = int(loop_index)
                address = _lhs_address(statement, loop_index)
                if address is not None:
                    event["destination_address"] = hex(address)
                elif _lhs_base(statement) is not None:
                    event["destination_base"] = hex(_lhs_base(statement))
                events.append(event)

        blocks.append(
            {
                "pivot_index": pivot_index,
                "source_line": pivot.source_line,
                "terminal": terminal,
                "event_count": len(events),
                "events": events,
            }
        )

    return {
        "format": FORMAT,
        "version": 1,
        "provider_id": provider_id,
        "function": spec["function"],
        "source_start_line": source_start_line,
        "source_line_count": len(lines),
        "scalar_count": layout.scalar_count,
        "blocks": blocks,
        "ready": not errors,
        "errors": errors,
    }


def summarize_execution_schedule(report: dict[str, Any]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for block in report.get("blocks") or []:
        for event in block.get("events") or []:
            kind = str(event.get("kind"))
            counts[kind] = counts.get(kind, 0) + 1

    return {
        "provider_id": report.get("provider_id"),
        "scalar_count": report.get("scalar_count"),
        "blocks": len(report.get("blocks") or []),
        "event_count": sum(
            int(block.get("event_count", 0))
            for block in report.get("blocks") or []
        ),
        "event_counts": dict(sorted(counts.items())),
        "terminal_blocks": sum(
            bool(block.get("terminal"))
            for block in report.get("blocks") or []
        ),
        "ready": bool(report.get("ready")),
    }


def validate_execution_schedule(report: dict[str, Any]) -> dict[str, Any]:
    errors = list(report.get("errors") or [])
    scalar_count = int(report.get("scalar_count", 0))
    blocks = report.get("blocks") or []

    if len(blocks) != scalar_count:
        errors.append(
            f"block-count:expected={scalar_count}:actual={len(blocks)}"
        )

    expected_pivots = list(range(scalar_count))
    actual_pivots = [
        int(block.get("pivot_index", -1))
        for block in blocks
    ]
    if actual_pivots != expected_pivots:
        errors.append("pivot-order-mismatch")

    terminal_count = 0
    for block in blocks:
        pivot = int(block.get("pivot_index", -1))
        events = block.get("events") or []
        if not events or events[0].get("kind") != "pivot-reciprocal":
            errors.append(f"pivot-{pivot}-missing-leading-reciprocal")
        is_terminal = bool(block.get("terminal"))
        if is_terminal:
            terminal_count += 1
            if not any(
                event.get("kind") == "backsubstitution"
                for event in events
            ):
                errors.append(f"terminal-pivot-{pivot}-missing-backsub-event")
        else:
            if any(
                event.get("kind") == "backsubstitution"
                for event in events
            ):
                errors.append(
                    f"pivot-{pivot}-unexpected-backsubstitution"
                )

    if terminal_count != 1:
        errors.append(
            f"terminal-block-count:expected=1:actual={terminal_count}"
        )

    return {
        "format": "SHIFT.SpecializedProviderExecutionScheduleValidation/1",
        "version": 1,
        "provider_id": report.get("provider_id"),
        "ready": not errors,
        "errors": errors,
        "blocks": len(blocks),
    }


def build_execution_schedule_contract(source: str) -> dict[str, Any]:
    providers: list[dict[str, Any]] = []
    for provider_id in (0, 1):
        report = extract_execution_schedule(
            source,
            provider_id=provider_id,
        )
        report["summary"] = summarize_execution_schedule(report)
        report["validation"] = validate_execution_schedule(report)
        providers.append(report)

    return {
        "format": FORMAT,
        "version": 1,
        "source_file": "SHIFT.exe.c",
        "providers": providers,
        "scope": {
            "representation": "source-order execution event stream",
            "pivot": "unique reciprocal pivot from Phase 437",
            "workspace": "destination addresses retained structurally; packing semantics remain separate",
            "terminal": "final pivot block is classified as back-substitution when writing the output vector",
        },
        "limitations": [
            "Event classification uses decompiler-visible syntax and destination address classes; it does not reconstruct numeric RHS expressions.",
            "Some non-output workspace writes remain intentionally grouped as workspace-or-global-update.",
            "Provider workspace packing and semantic matrix coordinates are not inferred by this phase.",
        ],
        "status": "source-backed-provider-execution-schedule",
    }


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()

    contract = build_execution_schedule_contract(
        args.source.read_text(encoding="utf-8")
    )
    print(json.dumps(contract, indent=2, sort_keys=True))
    ready = all(
        provider["validation"]["ready"]
        for provider in contract["providers"]
    )
    raise SystemExit(0 if ready else 2)
