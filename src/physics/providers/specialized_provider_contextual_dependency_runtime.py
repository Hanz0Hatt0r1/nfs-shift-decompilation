"""Attach source-context resolution to specialized-provider assignment dependencies.

Phase 450 consumes the Phase 441 assignment stream and Phase 449 source-context
resolver. Explicit row-pointer/array forms are resolved from their registered
row-pointer base plus local_10. Bare absolute workspace addresses retain every
known alias candidate.

No proprietary RHS expressions, semantic matrix names, or physical units are
emitted.
"""
from __future__ import annotations

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
from specialized_provider_source_context_resolver_runtime import (
    resolve_contextual_cell,
    resolve_direct_address,
    row_for_pointer,
)
from specialized_provider_storage_runtime import get_storage_layout

FORMAT = "SHIFT.SpecializedProviderContextualDependencyRuntime/1"


def _function_spec(provider_id: int) -> dict[str, Any]:
    try:
        return dict(SOLVER_SPECS[provider_id])
    except KeyError as exc:
        raise ValueError(f"unsupported provider id: {provider_id}") from exc


def _destination_base(
    statement: str,
) -> tuple[str, int] | None:
    match = LOOP_PTR_LHS_RE.search(statement)
    if match:
        return "loop-pointer", int(match.group(1), 16)

    match = ARRAY_LHS_RE.search(statement)
    if match:
        return "loop-array", int(match.group(1), 16)

    match = DIRECT_LHS_RE.match(statement)
    if match:
        return "direct", int(match.group(1), 16)

    return None


def _resolve_destination(
    statement: str,
    *,
    provider_id: int,
    loop_index: int | None,
) -> dict[str, Any]:
    destination = _destination_base(statement)
    if destination is None:
        raise ValueError("unsupported assignment destination")

    form, base = destination
    if form in {"loop-pointer", "loop-array"}:
        if loop_index is None:
            raise ValueError("loop destination without local_10")
        try:
            resolved = resolve_contextual_cell(
                provider_id,
                row_pointer=base,
                local_index=int(loop_index),
            )
        except ValueError:
            address = base + int(loop_index) * 8
            resolved = resolve_direct_address(
                provider_id,
                address=address,
            )
            resolved["form"] = form
            resolved["resolution_basis"] = "absolute-address-fallback"
            resolved["source_row_pointer"] = hex(base)
            resolved["local_index"] = int(loop_index)
            return resolved

        resolved["form"] = form
        return resolved

    return resolve_direct_address(
        provider_id,
        address=base,
    )


def _contextualize_rhs_reference(
    reference: dict[str, Any],
    *,
    provider_id: int,
) -> dict[str, Any]:
    result = dict(reference)
    if reference.get("domain") != "workspace":
        return result

    address_text = reference.get("address")
    if address_text is None:
        result["resolution_basis"] = "workspace-reference-without-address"
        return result

    address = int(str(address_text), 16)
    form = str(reference.get("form"))

    if form in {"row-pointer-offset", "row-pointer-base"}:
        if reference.get("row") is not None and reference.get("column") is not None:
            result["resolution_basis"] = "explicit-row-pointer-context"
            result["contextual_cell"] = {
                "row": int(reference["row"]),
                "column": int(reference["column"]),
            }
            result["contextual_unique"] = True
            return result

    resolved = resolve_direct_address(
        provider_id,
        address=address,
    )
    result["alias_candidates"] = resolved.get("candidates") or []
    result["alias_candidate_count"] = int(
        resolved.get("candidate_count", 0)
    )
    result["alias_unique"] = bool(resolved.get("unique", False))
    result["resolution_basis"] = "absolute-address-alias-map"
    return result


def extract_contextual_dependencies(
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

        for local_line, statement, loop_range in _assignment_statements(block):
            absolute_line = pivot.source_line + local_line
            lhs_match = _find_lhs_match(statement)
            rhs_text = statement[lhs_match.end():]

            loop_values = (
                tuple(range(*loop_range))
                if loop_range is not None
                else (None,)
            )

            for loop_index in loop_values:
                try:
                    destination = _resolve_destination(
                        statement,
                        provider_id=provider_id,
                        loop_index=(
                            None
                            if loop_index is None
                            else int(loop_index)
                        ),
                    )
                    rhs = _rhs_references(
                        rhs_text,
                        provider_id=provider_id,
                        loop_index=(
                            0
                            if loop_index is None
                            else int(loop_index)
                        ),
                    )
                except ValueError as exc:
                    errors.append(
                        f"pivot-{pivot_index}-line-{absolute_line}:{exc}"
                    )
                    continue

                assignments.append(
                    {
                        "pivot_index": pivot_index,
                        "source_line": absolute_line,
                        "loop_index": (
                            None
                            if loop_index is None
                            else int(loop_index)
                        ),
                        "destination": destination,
                        "rhs": [
                            _contextualize_rhs_reference(
                                reference.as_dict(),
                                provider_id=provider_id,
                            )
                            for reference in rhs
                        ],
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
        "ready": not errors,
        "errors": errors,
    }


def summarize_contextual_dependencies(report: dict[str, Any]) -> dict[str, Any]:
    assignments = report.get("assignments") or []
    destinations_unique = sum(
        bool((assignment.get("destination") or {}).get("unique"))
        for assignment in assignments
    )
    destinations_ambiguous = sum(
        (assignment.get("destination") or {}).get("domain") == "workspace"
        and not bool((assignment.get("destination") or {}).get("unique"))
        for assignment in assignments
    )

    rhs_workspace = 0
    rhs_contextual_unique = 0
    rhs_alias_ambiguous = 0
    for assignment in assignments:
        for reference in assignment.get("rhs") or []:
            if reference.get("domain") != "workspace":
                continue
            rhs_workspace += 1
            if reference.get("contextual_unique"):
                rhs_contextual_unique += 1
            elif not reference.get("alias_unique", True):
                rhs_alias_ambiguous += 1

    return {
        "provider_id": report.get("provider_id"),
        "scalar_count": report.get("scalar_count"),
        "assignments": len(assignments),
        "unique_destination_resolutions": destinations_unique,
        "ambiguous_workspace_destinations": destinations_ambiguous,
        "workspace_rhs_references": rhs_workspace,
        "contextual_unique_rhs_references": rhs_contextual_unique,
        "ambiguous_rhs_workspace_references": rhs_alias_ambiguous,
        "ready": bool(report.get("ready")),
    }


def validate_contextual_dependencies(report: dict[str, Any]) -> dict[str, Any]:
    errors = list(report.get("errors") or [])
    scalar_count = int(report.get("scalar_count", 0))

    for index, assignment in enumerate(report.get("assignments") or []):
        pivot = int(assignment["pivot_index"])
        if pivot < 0 or pivot >= scalar_count:
            errors.append(f"assignment-{index}-pivot-out-of-range")

        destination = assignment.get("destination") or {}
        if destination.get("domain") == "workspace":
            if destination.get("unique"):
                row = destination.get("row")
                column = destination.get("column")
                if row is None or column is None:
                    errors.append(
                        f"assignment-{index}-unique-destination-missing-coordinate"
                    )
            else:
                candidates = destination.get("candidates") or []
                if not candidates:
                    errors.append(
                        f"assignment-{index}-ambiguous-destination-without-candidates"
                    )

        for reference in assignment.get("rhs") or []:
            if reference.get("domain") != "workspace":
                continue
            if reference.get("contextual_unique"):
                if (
                    reference.get("contextual_cell", {}).get("row") is None
                    or reference.get("contextual_cell", {}).get("column") is None
                ):
                    errors.append(
                        f"assignment-{index}-contextual-rhs-missing-coordinate"
                    )
            elif reference.get("alias_unique") is False:
                if not reference.get("alias_candidates"):
                    errors.append(
                        f"assignment-{index}-ambiguous-rhs-without-aliases"
                    )

    return {
        "format": "SHIFT.SpecializedProviderContextualDependencyValidation/1",
        "version": 1,
        "provider_id": report.get("provider_id"),
        "ready": not errors,
        "errors": errors,
        "assignments": len(report.get("assignments") or []),
    }


def build_contextual_dependency_contract(source: str) -> dict[str, Any]:
    providers: list[dict[str, Any]] = []
    for provider_id in (0, 1):
        report = extract_contextual_dependencies(
            source,
            provider_id=provider_id,
        )
        report["summary"] = summarize_contextual_dependencies(report)
        report["validation"] = validate_contextual_dependencies(report)
        providers.append(report)

    return {
        "format": FORMAT,
        "version": 1,
        "source_file": "SHIFT.exe.c",
        "providers": providers,
        "resolution": {
            "destination": "explicit loop/array row-pointer forms resolve uniquely; direct addresses expose alias candidates",
            "rhs_workspace": "explicit row-pointer forms remain contextual; bare workspace addresses use alias classes",
        },
        "limitations": [
            "This phase does not infer matrix semantics from address reuse.",
            "Direct packed-workspace addresses may remain ambiguous by design.",
            "Numeric RHS coefficients and expression text are omitted.",
        ],
        "status": "source-backed-contextual-dependency-graph",
    }


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()

    contract = build_contextual_dependency_contract(
        args.source.read_text(encoding="utf-8")
    )
    print(json.dumps(contract, indent=2, sort_keys=True))
    ready = all(
        provider["validation"]["ready"]
        for provider in contract["providers"]
    )
    raise SystemExit(0 if ready else 2)
