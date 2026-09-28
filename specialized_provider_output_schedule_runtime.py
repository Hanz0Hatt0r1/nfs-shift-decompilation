"""Extract specialized-provider output-vector execution and dependency schedules.

Phase 453 isolates assignments whose destination lies in the provider output
vector. Each expanded loop iteration is represented by its output index and
ordered RHS output/workspace/global references.

The module describes source order and data dependencies only; it does not infer
a mathematical meaning for the output vector.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from specialized_provider_rhs_stencil_runtime import (
    ARRAY_LHS_RE,
    DIRECT_LHS_RE,
    LOOP_PTR_LHS_RE,
    SOLVER_SPECS,
    _assignment_statements,
    _find_lhs_match,
    _rhs_references,
)
from specialized_provider_solver_fingerprint_runtime import (
    extract_function_body,
    extract_reciprocal_pivots,
)
from specialized_provider_storage_runtime import get_storage_layout

FORMAT = "SHIFT.SpecializedProviderOutputScheduleRuntime/1"


def _function_spec(provider_id: int) -> dict[str, Any]:
    try:
        return dict(SOLVER_SPECS[provider_id])
    except KeyError as exc:
        raise ValueError(f"unsupported provider id: {provider_id}") from exc


def _destination_address(
    statement: str,
    loop_index: int | None,
) -> int | None:
    direct = DIRECT_LHS_RE.match(statement)
    if direct:
        return int(direct.group(1), 16)

    loop_ptr = LOOP_PTR_LHS_RE.search(statement)
    if loop_ptr and loop_index is not None:
        return int(loop_ptr.group(1), 16) + int(loop_index) * 8

    loop_array = ARRAY_LHS_RE.search(statement)
    if loop_array and loop_index is not None:
        return int(loop_array.group(1), 16) + int(loop_index) * 8

    return None


def extract_output_schedule(
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

    assignments: list[dict[str, Any]] = []
    edges: set[tuple[int, int, int]] = set()

    output_start = layout.output_vector_base
    output_end = output_start + layout.output_vector_bytes

    for pivot_index, pivot in enumerate(pivots):
        next_line = (
            pivots[pivot_index + 1].source_line
            if pivot_index + 1 < len(pivots)
            else source_start_line + len(lines)
        )
        block = lines[
            pivot.source_line - source_start_line:
            next_line - source_start_line
        ]
        terminal = pivot_index == layout.scalar_count - 1

        for local_line, statement, loop_range in _assignment_statements(block):
            absolute_line = pivot.source_line + local_line
            loop_values = (
                tuple(range(*loop_range))
                if loop_range is not None
                else (None,)
            )

            lhs_match = _find_lhs_match(statement)
            rhs_text = statement[lhs_match.end():]

            for loop_index in loop_values:
                address = _destination_address(statement, loop_index)
                if address is None or not (output_start <= address < output_end):
                    continue
                if (address - output_start) % 8:
                    errors.append(
                        f"pivot-{pivot_index}-line-{absolute_line}-unaligned-output-destination"
                    )
                    continue

                destination_index = (address - output_start) // 8
                rhs = _rhs_references(
                    rhs_text,
                    provider_id=provider_id,
                    loop_index=(
                        0
                        if loop_index is None
                        else int(loop_index)
                    ),
                )
                output_refs = [
                    dict(reference.as_dict())
                    for reference in rhs
                    if reference.domain == "output_vector"
                ]

                for reference in output_refs:
                    edges.add(
                        (
                            pivot_index,
                            destination_index,
                            int(reference["index"]),
                        )
                    )

                assignments.append(
                    {
                        "pivot_index": pivot_index,
                        "source_line": absolute_line,
                        "loop_index": (
                            None
                            if loop_index is None
                            else int(loop_index)
                        ),
                        "stage": (
                            "terminal-output"
                            if terminal
                            else "forward-output"
                        ),
                        "destination": {
                            "domain": "output_vector",
                            "index": destination_index,
                            "address": hex(address),
                        },
                        "rhs_output": output_refs,
                        "rhs_workspace_count": sum(
                            reference.domain == "workspace"
                            for reference in rhs
                        ),
                        "rhs_global_count": sum(
                            reference.domain not in {
                                "workspace",
                                "output_vector",
                            }
                            for reference in rhs
                        ),
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
        "assignments": assignments,
        "output_dependency_edges": [
            {
                "pivot_index": pivot,
                "destination_index": destination,
                "source_index": source,
            }
            for pivot, destination, source in sorted(edges)
        ],
        "ready": not errors,
        "errors": errors,
    }


def summarize_output_schedule(report: dict[str, Any]) -> dict[str, Any]:
    assignments = report.get("assignments") or []
    edges = report.get("output_dependency_edges") or []
    stage_counts = defaultdict(int)
    destination_counts = defaultdict(int)

    for assignment in assignments:
        stage_counts[str(assignment["stage"])] += 1
        destination_counts[int(assignment["destination"]["index"])] += 1

    return {
        "provider_id": report.get("provider_id"),
        "scalar_count": report.get("scalar_count"),
        "output_assignment_count": len(assignments),
        "output_dependency_edge_count": len(edges),
        "stage_counts": dict(sorted(stage_counts.items())),
        "destination_index_counts": dict(
            sorted(destination_counts.items())
        ),
        "ready": bool(report.get("ready")),
    }


def validate_output_schedule(report: dict[str, Any]) -> dict[str, Any]:
    errors = list(report.get("errors") or [])
    scalar_count = int(report.get("scalar_count", 0))

    for index, assignment in enumerate(report.get("assignments") or []):
        destination = assignment.get("destination") or {}
        destination_index = int(destination.get("index", -1))
        if destination_index < 0 or destination_index >= scalar_count:
            errors.append(
                f"assignment-{index}-output-index-out-of-range"
            )

        stage = str(assignment.get("stage"))
        pivot = int(assignment.get("pivot_index", -1))
        if stage == "terminal-output" and pivot != scalar_count - 1:
            errors.append(
                f"assignment-{index}-terminal-output-wrong-pivot"
            )
        if stage == "forward-output" and pivot == scalar_count - 1:
            errors.append(
                f"assignment-{index}-forward-output-on-terminal-pivot"
            )

        for reference in assignment.get("rhs_output") or []:
            source_index = int(reference.get("index", -1))
            if source_index < 0 or source_index >= scalar_count:
                errors.append(
                    f"assignment-{index}-rhs-output-index-out-of-range"
                )

    for edge in report.get("output_dependency_edges") or []:
        for key in ("destination_index", "source_index"):
            value = int(edge.get(key, -1))
            if value < 0 or value >= scalar_count:
                errors.append(
                    f"edge-{key}-out-of-range:{value}"
                )

    return {
        "format": "SHIFT.SpecializedProviderOutputScheduleValidation/1",
        "version": 1,
        "provider_id": report.get("provider_id"),
        "ready": not errors,
        "errors": errors,
        "assignments": len(report.get("assignments") or []),
        "edges": len(report.get("output_dependency_edges") or []),
    }


def build_output_schedule_contract(source: str) -> dict[str, Any]:
    providers: list[dict[str, Any]] = []
    for provider_id in (0, 1):
        report = extract_output_schedule(
            source,
            provider_id=provider_id,
        )
        report["summary"] = summarize_output_schedule(report)
        report["validation"] = validate_output_schedule(report)
        providers.append(report)

    return {
        "format": FORMAT,
        "version": 1,
        "source_file": "SHIFT.exe.c",
        "providers": providers,
        "scope": {
            "representation": "output-vector assignment and dependency schedule",
            "stage": "forward-output for non-terminal pivots; terminal-output for the final pivot block",
            "dependency": "ordered output-vector RHS references collapsed into deduplicated pivot/destination/source edges",
        },
        "limitations": [
            "Stage names describe source position and are not mathematical solver names.",
            "Output-vector dependencies are extracted from decompiler-visible address forms.",
            "The module does not infer whether an output index corresponds to a particular physical quantity.",
        ],
        "status": "source-backed-output-vector-schedule",
    }


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()

    contract = build_output_schedule_contract(
        args.source.read_text(encoding="utf-8")
    )
    print(json.dumps(contract, indent=2, sort_keys=True))
    ready = all(
        provider["validation"]["ready"]
        for provider in contract["providers"]
    )
    raise SystemExit(0 if ready else 2)
