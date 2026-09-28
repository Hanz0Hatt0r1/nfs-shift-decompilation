"""Assemble a neutral solver IR from the specialized-provider evidence layers.

Phase 444 joins pivot geometry, workspace write topology, RHS address references,
and operator signatures into one source-backed program representation. The IR
contains no retail RHS expression text and does not claim undocumented semantic
types or units.
"""
from __future__ import annotations

from typing import Any

from specialized_provider_dependency_graph_runtime import (
    build_dependency_graph,
)
from specialized_provider_operator_signature_runtime import (
    extract_operator_signatures,
)
from specialized_provider_rhs_stencil_runtime import (
    extract_rhs_stencils,
)
from specialized_provider_solver_runtime import (
    build_pivot_geometry,
    get_solver_spec,
)
from specialized_provider_storage_runtime import get_storage_layout

FORMAT = "SHIFT.SpecializedProviderSolverIRRuntime/1"


def _assignment_operator_map(
    operator_report: dict[str, Any],
) -> dict[tuple[int, int], str]:
    mapping: dict[tuple[int, int], str] = {}
    for item in operator_report.get("assignments") or []:
        key = (
            int(item["pivot_index"]),
            int(item["source_line"]),
        )
        operator = str(item["operator"])
        previous = mapping.get(key)
        if previous is not None and previous != operator:
            raise ValueError(
                f"conflicting operator signatures at {key}: "
                f"{previous!r} vs {operator!r}"
            )
        mapping[key] = operator
    return mapping


def build_solver_ir(
    source: str,
    *,
    provider_id: int,
) -> dict[str, Any]:
    layout = get_storage_layout(provider_id)
    spec = get_solver_spec(provider_id)
    pivots = build_pivot_geometry(provider_id)

    rhs_report = extract_rhs_stencils(
        source,
        provider_id=provider_id,
    )
    operator_report = extract_operator_signatures(
        source,
        provider_id=provider_id,
    )
    dependency_report = build_dependency_graph(
        source,
        provider_id=provider_id,
    )

    errors: list[str] = []
    errors.extend(str(value) for value in rhs_report.get("errors") or [])
    errors.extend(str(value) for value in operator_report.get("errors") or [])
    errors.extend(str(value) for value in dependency_report.get("errors") or [])

    operator_map = _assignment_operator_map(operator_report)

    dependency_by_key: dict[
        tuple[int, int, int | None, str],
        dict[str, Any],
    ] = {}
    for node in dependency_report.get("nodes") or []:
        key = (
            int(node["pivot_index"]),
            int(node["source_line"]),
            (
                None
                if node.get("loop_index") is None
                else int(node["loop_index"])
            ),
            str(node["destination"]),
        )
        dependency_by_key[key] = node

    program_assignments: list[dict[str, Any]] = []
    for stencil in rhs_report.get("stencils") or []:
        pivot = int(stencil["pivot_index"])
        source_line = int(stencil["source_line"])
        operator = operator_map.get((pivot, source_line))
        if operator is None:
            errors.append(
                f"missing-operator-signature:pivot={pivot}:"
                f"source-line={source_line}"
            )
            continue

        destination = dict(stencil["destination"])
        workspace_reads = [
            dict(reference)
            for reference in stencil.get("rhs") or []
            if reference.get("domain") == "workspace"
        ]
        output_reads = [
            dict(reference)
            for reference in stencil.get("rhs") or []
            if reference.get("domain") == "output_vector"
        ]
        global_reads = [
            dict(reference)
            for reference in stencil.get("rhs") or []
            if reference.get("domain") not in {
                "workspace",
                "output_vector",
            }
        ]

        program_assignments.append(
            {
                "pivot_index": pivot,
                "source_line": source_line,
                "loop_index": stencil.get("loop_index"),
                "operator": operator,
                "destination": destination,
                "workspace_reads": workspace_reads,
                "output_reads": output_reads,
                "global_reads": global_reads,
            }
        )

    stencil_keys = {
        (
            int(stencil["pivot_index"]),
            int(stencil["source_line"]),
        )
        for stencil in rhs_report.get("stencils") or []
    }
    for assignment in operator_report.get("assignments") or []:
        key = (
            int(assignment["pivot_index"]),
            int(assignment["source_line"]),
        )
        if key not in stencil_keys:
            errors.append(
                f"operator-without-stencil:pivot={key[0]}:"
                f"source-line={key[1]}"
            )

    blocks: list[dict[str, Any]] = []
    for pivot in pivots:
        pivot_index = int(pivot.index)
        blocks.append(
            {
                "pivot_index": pivot_index,
                "source_line": int(
                    next(
                        item["source_line"]
                        for item in rhs_report.get("stencils") or []
                        if int(item["pivot_index"]) == pivot_index
                    )
                    if any(
                        int(item["pivot_index"]) == pivot_index
                        for item in rhs_report.get("stencils") or []
                    )
                    else get_solver_spec(provider_id)["first_reciprocal_line"]
                ),
                "row_pointer": hex(pivot.row_pointer),
                "diagonal_address": hex(pivot.diagonal_address),
                "diagonal_offset": pivot.diagonal_offset,
            }
        )

    for block in blocks:
        pivot = int(block["pivot_index"])
        block["assignments"] = [
            assignment
            for assignment in program_assignments
            if int(assignment["pivot_index"]) == pivot
        ]

    if len(blocks) != layout.scalar_count:
        errors.append(
            f"block-count:expected={layout.scalar_count}:"
            f"actual={len(blocks)}"
        )

    return {
        "format": FORMAT,
        "version": 1,
        "provider_id": provider_id,
        "function": spec["function"],
        "scalar_count": layout.scalar_count,
        "pivot_count": len(pivots),
        "blocks": blocks,
        "source_layers": {
            "pivot_geometry": "SHIFT.SpecializedProviderSolverPivotRuntime/1",
            "write_graph": "SHIFT.SpecializedProviderUpdateGraph/1",
            "rhs_stencils": "SHIFT.SpecializedProviderRHSStencilRuntime/1",
            "dependency_graph": "SHIFT.SpecializedProviderDependencyGraphRuntime/1",
            "operator_signatures": "SHIFT.SpecializedProviderOperatorSignatureRuntime/1",
        },
        "ready": not errors,
        "errors": errors,
    }


def summarize_solver_ir(report: dict[str, Any]) -> dict[str, Any]:
    assignments = [
        assignment
        for block in report.get("blocks") or []
        for assignment in block.get("assignments") or []
    ]
    operator_counts: dict[str, int] = {}
    for assignment in assignments:
        key = str(assignment["operator"])
        operator_counts[key] = operator_counts.get(key, 0) + 1

    return {
        "provider_id": report.get("provider_id"),
        "scalar_count": report.get("scalar_count"),
        "blocks": len(report.get("blocks") or []),
        "assignments": len(assignments),
        "operator_counts": dict(sorted(operator_counts.items())),
        "workspace_reads": sum(
            len(assignment.get("workspace_reads") or [])
            for assignment in assignments
        ),
        "output_reads": sum(
            len(assignment.get("output_reads") or [])
            for assignment in assignments
        ),
        "global_reads": sum(
            len(assignment.get("global_reads") or [])
            for assignment in assignments
        ),
        "ready": bool(report.get("ready")),
    }


def validate_solver_ir(report: dict[str, Any]) -> dict[str, Any]:
    errors = list(report.get("errors") or [])
    scalar_count = int(report.get("scalar_count", 0))
    blocks = report.get("blocks") or []

    if len(blocks) != scalar_count:
        errors.append("block-count-does-not-equal-scalar-count")

    expected_pivots = list(range(scalar_count))
    actual_pivots = [int(block.get("pivot_index", -1)) for block in blocks]
    if actual_pivots != expected_pivots:
        errors.append("pivot-block-order-mismatch")

    for block in blocks:
        pivot = int(block.get("pivot_index", -1))
        if pivot < 0 or pivot >= scalar_count:
            errors.append(f"pivot-{pivot}-out-of-range")
        if not block.get("diagonal_address"):
            errors.append(f"pivot-{pivot}-missing-diagonal-address")

        for assignment in block.get("assignments") or []:
            if int(assignment.get("pivot_index", -1)) != pivot:
                errors.append(f"pivot-{pivot}-assignment-pivot-mismatch")
            destination = assignment.get("destination") or {}
            if destination.get("domain") == "workspace":
                if (
                    destination.get("row") is None
                    or destination.get("column") is None
                ):
                    errors.append(
                        f"pivot-{pivot}-workspace-assignment-missing-coordinate"
                    )

    return {
        "format": "SHIFT.SpecializedProviderSolverIRValidation/1",
        "version": 1,
        "provider_id": report.get("provider_id"),
        "ready": not errors,
        "errors": errors,
        "blocks": len(blocks),
        "assignments": sum(
            len(block.get("assignments") or [])
            for block in blocks
        ),
    }


def build_solver_ir_contract(source: str) -> dict[str, Any]:
    providers: list[dict[str, Any]] = []
    for provider_id in (0, 1):
        report = build_solver_ir(
            source,
            provider_id=provider_id,
        )
        report["summary"] = summarize_solver_ir(report)
        report["validation"] = validate_solver_ir(report)
        providers.append(report)

    return {
        "format": FORMAT,
        "version": 1,
        "source_file": "SHIFT.exe.c",
        "providers": providers,
        "scope": {
            "program_model": "pivot blocks with assignment-level destinations, address dependencies and operator signatures",
            "numeric_expressions": "omitted",
            "static_storage": "resolved through specialized-provider row topology",
        },
        "limitations": [
            "The IR is structural and address-based; it is not a drop-in numeric solver yet.",
            "Decompiler-visible operator classification does not replace full expression semantics.",
            "Provider acceptance and final runtime provider selection remain separate capture-gated boundaries.",
        ],
        "status": "source-backed-specialized-provider-solver-ir",
    }


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()

    contract = build_solver_ir_contract(
        args.source.read_text(encoding="utf-8")
    )
    print(json.dumps(contract, indent=2, sort_keys=True))
    ready = all(
        provider["validation"]["ready"]
        for provider in contract["providers"]
    )
    raise SystemExit(0 if ready else 2)
