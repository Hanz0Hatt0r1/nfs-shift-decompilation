"""Build a source-backed dependency graph from specialized-provider RHS stencils.

Phase 442 consumes the Phase 441 assignment stencils and collapses them into
address-level read-after-write relations. Workspace-to-workspace edges are kept
separate from output-vector and unresolved global references.

This is a data-dependency graph, not a semantic sparse-matrix graph. No numeric
RHS expression text, physical units, or undocumented class names are emitted.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from specialized_provider_rhs_stencil_runtime import build_rhs_stencil_contract
from specialized_provider_storage_runtime import get_storage_layout

FORMAT = "SHIFT.SpecializedProviderDependencyGraphRuntime/1"


def _node_key(reference: dict[str, Any]) -> tuple[Any, ...]:
    domain = reference.get("domain")
    if domain == "workspace":
        return (
            domain,
            int(reference["row"]),
            int(reference["column"]),
        )
    if domain == "output_vector":
        return (
            domain,
            int(reference["index"]),
        )
    return (
        domain,
        reference.get("address"),
    )


def _reference_copy(reference: dict[str, Any]) -> dict[str, Any]:
    return dict(reference)


def _classify_relation(
    pivot_index: int,
    destination: dict[str, Any],
    source: dict[str, Any],
) -> str:
    if source.get("domain") != "workspace":
        return str(source.get("domain", "unknown"))

    source_row = int(source["row"])
    destination_row = int(destination["row"])

    if source_row < pivot_index:
        return "prior-pivot"
    if source_row == pivot_index:
        return "current-pivot"
    if source_row == destination_row:
        return "destination-row"
    if source_row > destination_row:
        return "later-row"
    return "future-pivot"


def build_dependency_graph(
    source: str,
    *,
    provider_id: int,
) -> dict[str, Any]:
    layout = get_storage_layout(provider_id)
    rhs_contract = build_rhs_stencil_contract(source)
    provider_report = next(
        (
            report
            for report in rhs_contract.get("providers", [])
            if int(report.get("provider_id", -1)) == provider_id
        ),
        None,
    )
    if provider_report is None:
        raise ValueError(f"RHS contract missing provider {provider_id}")

    errors = list(provider_report.get("errors") or [])
    validation = provider_report.get("validation") or {}
    errors.extend(str(error) for error in validation.get("errors") or [])

    nodes: list[dict[str, Any]] = []
    edge_map: dict[tuple[Any, ...], dict[str, Any]] = {}
    pivot_summaries: dict[int, dict[str, Any]] = defaultdict(
        lambda: {
            "assignment_count": 0,
            "workspace_destination_count": 0,
            "output_destination_count": 0,
            "workspace_read_edges": set(),
            "output_read_indices": set(),
            "global_read_addresses": set(),
        }
    )

    for stencil in provider_report.get("stencils") or []:
        pivot = int(stencil["pivot_index"])
        destination = _reference_copy(stencil["destination"])
        rhs_refs = [
            _reference_copy(reference)
            for reference in stencil.get("rhs") or []
        ]

        summary = pivot_summaries[pivot]
        summary["assignment_count"] += 1

        destination_domain = destination.get("domain")
        if destination_domain == "workspace":
            summary["workspace_destination_count"] += 1
        elif destination_domain == "output_vector":
            summary["output_destination_count"] += 1

        workspace_reads: list[dict[str, Any]] = []
        output_reads: list[dict[str, Any]] = []
        global_reads: list[dict[str, Any]] = []

        for source_ref in rhs_refs:
            domain = source_ref.get("domain")
            if domain == "workspace":
                workspace_reads.append(source_ref)
                edge_key = (
                    pivot,
                    _node_key(source_ref),
                    _node_key(destination),
                )
                summary["workspace_read_edges"].add(edge_key)
                edge_map.setdefault(
                    edge_key,
                    {
                        "pivot_index": pivot,
                        "source": source_ref,
                        "destination": destination,
                        "relation": _classify_relation(
                            pivot,
                            destination,
                            source_ref,
                        ),
                    },
                )
            elif domain == "output_vector":
                output_reads.append(source_ref)
                summary["output_read_indices"].add(
                    int(source_ref["index"])
                )
            else:
                global_reads.append(source_ref)
                address = source_ref.get("address")
                if address is not None:
                    summary["global_read_addresses"].add(str(address))

        nodes.append(
            {
                "pivot_index": pivot,
                "source_line": int(stencil["source_line"]),
                "loop_index": stencil.get("loop_index"),
                "destination": destination,
                "workspace_reads": workspace_reads,
                "output_reads": output_reads,
                "global_reads": global_reads,
            }
        )

    for pivot, summary in pivot_summaries.items():
        summary["workspace_read_edges"] = len(summary["workspace_read_edges"])
        summary["output_read_indices"] = sorted(summary["output_read_indices"])
        summary["global_read_addresses"] = sorted(
            summary["global_read_addresses"]
        )

    edges = sorted(
        edge_map.values(),
        key=lambda edge: (
            int(edge["pivot_index"]),
            str(edge["relation"]),
            str(edge["source"]),
            str(edge["destination"]),
        ),
    )

    pivot_rows = [
        {
            "pivot_index": pivot,
            **summary,
        }
        for pivot, summary in sorted(pivot_summaries.items())
    ]

    if len(pivot_rows) != layout.scalar_count:
        errors.append(
            f"pivot-row-summary-count:expected={layout.scalar_count}:"
            f"actual={len(pivot_rows)}"
        )

    return {
        "format": FORMAT,
        "version": 1,
        "provider_id": provider_id,
        "scalar_count": layout.scalar_count,
        "function": provider_report.get("function"),
        "nodes": nodes,
        "edges": edges,
        "pivot_summaries": pivot_rows,
        "source_status": {
            "rhs_contract_ready": bool(provider_report.get("ready")),
            "rhs_validation_ready": bool(validation.get("ready", False)),
        },
        "ready": not errors,
        "errors": errors,
    }


def summarize_dependency_graph(report: dict[str, Any]) -> dict[str, Any]:
    edges = report.get("edges") or []
    nodes = report.get("nodes") or []
    return {
        "provider_id": report.get("provider_id"),
        "scalar_count": report.get("scalar_count"),
        "assignment_nodes": len(nodes),
        "unique_workspace_edges": len(edges),
        "edges_by_relation": {
            relation: sum(
                edge.get("relation") == relation
                for edge in edges
            )
            for relation in sorted(
                {str(edge.get("relation")) for edge in edges}
            )
        },
        "output_read_occurrences": sum(
            len(node.get("output_reads") or [])
            for node in nodes
        ),
        "global_read_occurrences": sum(
            len(node.get("global_reads") or [])
            for node in nodes
        ),
        "pivots": len(report.get("pivot_summaries") or []),
        "ready": bool(report.get("ready")),
    }


def validate_dependency_graph(report: dict[str, Any]) -> dict[str, Any]:
    errors = list(report.get("errors") or [])
    scalar_count = int(report.get("scalar_count", 0))

    if len(report.get("pivot_summaries") or []) != scalar_count:
        errors.append("pivot-summary-count-mismatch")

    for edge in report.get("edges") or []:
        pivot = int(edge["pivot_index"])
        source = edge["source"]
        destination = edge["destination"]
        if source.get("domain") != "workspace":
            errors.append(f"pivot-{pivot}-non-workspace-edge-source")
            continue
        if source.get("row") is None or source.get("column") is None:
            errors.append(f"pivot-{pivot}-workspace-edge-source-missing-coordinates")
        if destination.get("domain") == "workspace":
            if (
                destination.get("row") is None
                or destination.get("column") is None
            ):
                errors.append(
                    f"pivot-{pivot}-workspace-edge-destination-missing-coordinates"
                )

    for node in report.get("nodes") or []:
        pivot = int(node["pivot_index"])
        destination = node.get("destination") or {}
        if destination.get("domain") == "workspace":
            row = int(destination["row"])
            column = int(destination["column"])
            if row < 0 or row >= scalar_count:
                errors.append(f"pivot-{pivot}-destination-row-out-of-range")
            if column < 0:
                errors.append(f"pivot-{pivot}-destination-column-negative")

        for reference in node.get("workspace_reads") or []:
            if reference.get("row") is None or reference.get("column") is None:
                errors.append(
                    f"pivot-{pivot}-workspace-read-missing-coordinates"
                )
                continue
            row = int(reference["row"])
            column = int(reference["column"])
            if row < 0 or row >= scalar_count:
                errors.append(f"pivot-{pivot}-workspace-read-row-out-of-range")
            if column < 0:
                errors.append(f"pivot-{pivot}-workspace-read-column-negative")

    return {
        "format": "SHIFT.SpecializedProviderDependencyGraphValidation/1",
        "version": 1,
        "provider_id": report.get("provider_id"),
        "ready": not errors,
        "errors": errors,
        "nodes": len(report.get("nodes") or []),
        "edges": len(report.get("edges") or []),
    }


def build_dependency_contract(source: str) -> dict[str, Any]:
    providers: list[dict[str, Any]] = []
    for provider_id in (0, 1):
        report = build_dependency_graph(
            source,
            provider_id=provider_id,
        )
        report["summary"] = summarize_dependency_graph(report)
        report["validation"] = validate_dependency_graph(report)
        providers.append(report)

    return {
        "format": FORMAT,
        "version": 1,
        "source_file": "SHIFT.exe.c",
        "providers": providers,
        "scope": {
            "representation": "assignment-level address dependency graph",
            "workspace_edge": "RHS workspace reference -> assignment destination",
            "output_vector": "kept as output-vector index references",
            "global_data": "kept as direct address references",
        },
        "limitations": [
            "The graph captures address-level dependencies rather than semantic matrix entries.",
            "Numeric RHS operators and coefficients are intentionally omitted.",
            "An edge describes a source-level data reference; it does not establish a solver algorithmic role by itself.",
        ],
        "status": "source-backed-address-dependency-graph",
    }


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()

    contract = build_dependency_contract(
        args.source.read_text(encoding="utf-8")
    )
    print(json.dumps(contract, indent=2, sort_keys=True))
    ready = all(
        provider["validation"]["ready"]
        for provider in contract["providers"]
    )
    raise SystemExit(0 if ready else 2)
