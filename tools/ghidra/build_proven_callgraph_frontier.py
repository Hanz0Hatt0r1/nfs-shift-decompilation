#!/usr/bin/env python3
"""Expand proven subsystem slices through direct Ghidra callgraph evidence.

Unlike the method-name frontier, this tool does not require a string-derived
method identity.  It starts from already established subsystem slices and keeps
anonymous FUN_* neighbours visible so callers/callees, orchestration candidates
and unresolved indirect calls can be selected for targeted instruction export.

Frontier membership is target-selection evidence only.  It never promotes a
function into a subsystem and never assigns field, object or physical semantics.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Iterable

from build_subsystem_manifests import build as build_subsystem_manifests
from join_method_anchors_to_subsystems import _subsystem_slice_addresses

FORMAT = "SHIFT.GhidraProvenCallgraphFrontier/1"
DEFAULT_SUBSYSTEMS = ("physics", "vehicle")


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            yield row


def _load_functions(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "functions.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"missing required Ghidra file: {path.name}")
    functions: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(path):
        address = row.get("address")
        if not isinstance(address, str):
            continue
        if address in functions:
            raise ValueError(f"{path}: duplicate function address {address}")
        functions[address] = row
    return functions


def _load_callgraph(root: Path):
    path = root / "callgraph.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"missing required Ghidra file: {path.name}")

    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    indirect: dict[str, list[dict[str, Any]]] = defaultdict(list)
    direct_rows: list[dict[str, Any]] = []

    for row in _read_jsonl(path):
        source = row.get("from_function")
        if row.get("indirect") is True:
            if isinstance(source, str):
                indirect[source].append(row)
            continue
        if row.get("indirect") is not False:
            continue
        target = row.get("to")
        if not isinstance(source, str) or not isinstance(target, str):
            continue
        outgoing[source].append(row)
        incoming[target].append(row)
        direct_rows.append(row)

    return outgoing, incoming, indirect, direct_rows


def _edge_record(row: dict[str, Any], direction: str | None = None) -> dict[str, Any]:
    result = {
        "from_function": row.get("from_function"),
        "from_name": row.get("from_name"),
        "instruction": row.get("instruction"),
        "to": row.get("to"),
        "to_name": row.get("to_name"),
        "indirect": row.get("indirect"),
    }
    if direction is not None:
        result["direction"] = direction
    return result


def _instruction_sort_key(row: dict[str, Any]) -> tuple[int, str]:
    value = row.get("instruction")
    if isinstance(value, str):
        try:
            return int(value, 16), value
        except ValueError:
            pass
    return (1 << 63), str(value or "")


def _build_adjacency(direct_rows: list[dict[str, Any]]) -> dict[str, set[str]]:
    adjacency: dict[str, set[str]] = defaultdict(set)
    for row in direct_rows:
        source = row["from_function"]
        target = row["to"]
        adjacency[source].add(target)
        adjacency[target].add(source)
    return adjacency


def _distances(
    roots: set[str],
    adjacency: dict[str, set[str]],
    max_depth: int,
) -> dict[str, int]:
    distance = {address: 0 for address in roots}
    queue = deque(sorted(roots))
    while queue:
        current = queue.popleft()
        depth = distance[current]
        if depth >= max_depth:
            continue
        for neighbour in sorted(adjacency.get(current, ())):
            if neighbour in distance:
                continue
            distance[neighbour] = depth + 1
            queue.append(neighbour)
    return distance


def _candidate_sort_key(row: dict[str, Any]):
    return (
        int(row["min_depth"]),
        0 if row["multi_anchor_caller_candidate"] else 1,
        -len(row["adjacent_proven_slice_addresses"]),
        -len(row["ordered_slice_calls"]),
        row["address"],
    )


def build_proven_callgraph_frontier(
    root: Path,
    subsystems: Iterable[str] = DEFAULT_SUBSYSTEMS,
    max_depth: int = 2,
    max_targets: int = 64,
) -> dict[str, Any]:
    if max_depth < 1:
        raise ValueError("max_depth must be >= 1")
    if max_targets < 1:
        raise ValueError("max_targets must be >= 1")

    subsystem_report = build_subsystem_manifests(root)
    manifests = subsystem_report.get("subsystems") or {}
    selected = tuple(dict.fromkeys(subsystems))
    if not selected:
        raise ValueError("at least one subsystem is required")
    missing = [name for name in selected if name not in manifests]
    if missing:
        raise ValueError(
            "unknown subsystem(s): " + ", ".join(missing) +
            "; available: " + ", ".join(sorted(manifests))
        )

    functions = _load_functions(root)
    outgoing, incoming, indirect, direct_rows = _load_callgraph(root)
    adjacency = _build_adjacency(direct_rows)

    slices = {
        subsystem: _subsystem_slice_addresses(manifests[subsystem])
        for subsystem in selected
    }
    empty = [subsystem for subsystem, addresses in slices.items() if not addresses]
    if empty:
        raise ValueError("selected subsystem has empty proven slice: " + ", ".join(empty))

    root_addresses = set().union(*slices.values())
    distances_by_subsystem = {
        subsystem: _distances(addresses, adjacency, max_depth)
        for subsystem, addresses in slices.items()
    }

    frontier_addresses: set[str] = set()
    for distances in distances_by_subsystem.values():
        frontier_addresses.update(
            address
            for address, depth in distances.items()
            if 0 < depth <= max_depth and address not in root_addresses
        )

    rows: list[dict[str, Any]] = []
    for address in sorted(frontier_addresses):
        subsystem_distances = {
            subsystem: distances[address]
            for subsystem, distances in distances_by_subsystem.items()
            if address in distances and distances[address] > 0
        }
        min_depth = min(subsystem_distances.values())

        ordered_slice_calls = sorted(
            [
                _edge_record(edge, "candidate-to-slice")
                for edge in outgoing.get(address, [])
                if edge.get("to") in root_addresses
            ],
            key=_instruction_sort_key,
        )
        slice_callers = sorted(
            [
                _edge_record(edge, "slice-to-candidate")
                for edge in incoming.get(address, [])
                if edge.get("from_function") in root_addresses
            ],
            key=_instruction_sort_key,
        )
        adjacent = sorted(
            {
                edge["to"]
                for edge in ordered_slice_calls
                if isinstance(edge.get("to"), str)
            }
            | {
                edge["from_function"]
                for edge in slice_callers
                if isinstance(edge.get("from_function"), str)
            }
        )
        distinct_slice_callees = {
            edge["to"]
            for edge in ordered_slice_calls
            if isinstance(edge.get("to"), str)
        }
        multi_anchor_caller = len(distinct_slice_callees) >= 2

        function = functions.get(address)
        indirect_sites = sorted(
            [_edge_record(edge, "unresolved-indirect-call") for edge in indirect.get(address, [])],
            key=_instruction_sort_key,
        )
        if min_depth == 1 and multi_anchor_caller:
            status = "direct-proven-slice-multi-call-frontier"
        elif min_depth == 1:
            status = "direct-proven-slice-frontier"
        else:
            status = "transitive-direct-callgraph-frontier"

        rows.append(
            {
                "address": address,
                "name": function.get("name") if function else None,
                "function_metadata_present": function is not None,
                "external": function.get("external") if function else None,
                "thunk": function.get("thunk") if function else None,
                "calling_convention": function.get("calling_convention") if function else None,
                "signature": function.get("signature") if function else None,
                "size": function.get("size") if function else None,
                "mnemonic_sha256": function.get("mnemonic_sha256") if function else None,
                "min_depth": min_depth,
                "subsystem_distances": dict(sorted(subsystem_distances.items())),
                "connected_subsystems": sorted(subsystem_distances),
                "adjacent_proven_slice_addresses": adjacent,
                "ordered_slice_calls": ordered_slice_calls,
                "slice_callers": slice_callers,
                "multi_anchor_caller_candidate": multi_anchor_caller,
                "indirect_call_sites": indirect_sites,
                "direct_outgoing_count": len(outgoing.get(address, [])),
                "direct_incoming_count": len(incoming.get(address, [])),
                "frontier_candidate": True,
                "promoted": False,
                "status": status,
            }
        )

    rows.sort(key=_candidate_sort_key)
    exportable = [
        row
        for row in rows
        if row["function_metadata_present"] and row["external"] is not True
    ]
    selected_targets = exportable[:max_targets]

    multi_anchor_callers = [
        row for row in rows if row["multi_anchor_caller_candidate"]
    ]

    observed_addresses = root_addresses | frontier_addresses
    indirect_blockers: list[dict[str, Any]] = []
    for source in sorted(observed_addresses):
        for edge in sorted(indirect.get(source, []), key=_instruction_sort_key):
            if source in root_addresses:
                depth = 0
            else:
                depth = next(
                    row["min_depth"] for row in rows if row["address"] == source
                )
            indirect_blockers.append(
                {
                    "from_function": source,
                    "from_name": edge.get("from_name"),
                    "instruction": edge.get("instruction"),
                    "frontier_depth": depth,
                    "status": "unresolved-indirect-call-target",
                    "promoted": False,
                }
            )

    slice_summary = {
        subsystem: {
            "proven_slice_address_count": len(addresses),
            "proven_slice_addresses": sorted(addresses),
        }
        for subsystem, addresses in slices.items()
    }

    return {
        "format": FORMAT,
        "ghidra_export": str(root),
        "source": subsystem_report.get("source"),
        "selected_subsystems": list(selected),
        "max_depth": max_depth,
        "max_targets": max_targets,
        "proven_slice_address_count": len(root_addresses),
        "frontier_candidate_count": len(rows),
        "direct_frontier_candidate_count": sum(row["min_depth"] == 1 for row in rows),
        "transitive_frontier_candidate_count": sum(row["min_depth"] > 1 for row in rows),
        "multi_anchor_caller_candidate_count": len(multi_anchor_callers),
        "indirect_blocker_count": len(indirect_blockers),
        "instruction_export_target_count": len(selected_targets),
        "subsystems": slice_summary,
        "frontier_candidates": rows,
        "multi_anchor_callers": multi_anchor_callers,
        "indirect_blockers": indirect_blockers,
        "instruction_export_targets": [
            {
                "address": row["address"],
                "name": row["name"],
                "min_depth": row["min_depth"],
                "connected_subsystems": row["connected_subsystems"],
                "multi_anchor_caller_candidate": row["multi_anchor_caller_candidate"],
                "status": row["status"],
            }
            for row in selected_targets
        ],
        "instruction_export_addresses": [row["address"] for row in selected_targets],
        "scope": {
            "direct_call_edges_only": True,
            "callgraph_traversal_is_bidirectional_for_target_selection": True,
            "proven_subsystem_slices_are_roots": True,
            "anonymous_functions_are_allowed": True,
            "frontier_membership_is_semantic_promotion": False,
            "multi_anchor_caller_is_update_loop_proof": False,
            "indirect_targets_resolved": False,
            "automatic_function_renaming_performed": False,
            "object_layout_proven": False,
            "field_semantics_proven": False,
            "note": (
                "The frontier preserves only direct-call adjacency and shortest direct-callgraph "
                "distance from already established subsystem slices. A function calling multiple "
                "slice members is an instruction-export/orchestration candidate only; call order "
                "or subsystem membership must be established separately from its instructions."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument(
        "--subsystem",
        dest="subsystems",
        action="append",
        help="subsystem root to expand; repeatable (default: physics, vehicle)",
    )
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--max-targets", type=int, default=64)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument(
        "--targets-out",
        type=Path,
        help="write instruction-export target addresses, one per line",
    )
    args = parser.parse_args()

    report = build_proven_callgraph_frontier(
        args.ghidra_export,
        subsystems=args.subsystems or DEFAULT_SUBSYSTEMS,
        max_depth=args.max_depth,
        max_targets=args.max_targets,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    if args.targets_out:
        args.targets_out.parent.mkdir(parents=True, exist_ok=True)
        args.targets_out.write_text(
            "".join(address + "\n" for address in report["instruction_export_addresses"]),
            encoding="utf-8",
        )

    print(f"format: {report['format']}")
    print(f"proven slice addresses: {report['proven_slice_address_count']}")
    print(f"frontier candidates: {report['frontier_candidate_count']}")
    print(f"multi-anchor callers: {report['multi_anchor_caller_candidate_count']}")
    print(f"indirect blockers: {report['indirect_blocker_count']}")
    print(f"instruction-export targets: {report['instruction_export_target_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    if args.targets_out:
        print(f"targets: {args.targets_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
