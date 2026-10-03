#!/usr/bin/env python3
"""Compose Process 1 pointer provenance layers into one fail-closed graph.

The graph joins exact receiver callsites, local receiver/base origins, and zero or
more parent-call register-transfer reports.  It is a composition/audit layer:
it does not invent additional def-use facts and never promotes object, owner,
class, vptr, field, input, or scheduler semantics from graph connectivity.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.VehiclePointerValueClosure/1"
RECEIVER_FORMAT = "SHIFT.VehicleReceiverProvenance/1"
POINTER_FORMAT = "SHIFT.VehiclePointerOriginFrontier/1"
TRANSFER_FORMAT = "SHIFT.VehicleParentCallsiteTransfer/1"
UPPER_CALLER = "0x007155e9"

STATES = {"proven", "verified", "inferred", "ambiguous", "unknown"}
STATE_STRENGTH = {
    "unknown": 0,
    "ambiguous": 1,
    "inferred": 2,
    "verified": 3,
    "proven": 4,
}


def _load(path: Path, expected: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    if payload.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}, found {payload.get('format')}")
    return payload


def _require_state(value: Any, label: str) -> str:
    if value not in STATES:
        raise ValueError(f"{label}: invalid evidence state {value!r}")
    return str(value)


def _weakest_state(*values: str) -> str:
    if not values:
        return "unknown"
    for value in values:
        _require_state(value, "state merge")
    return min(values, key=lambda value: STATE_STRENGTH[value])


def _entry_node(function: str, register: str) -> tuple[str, dict[str, Any]]:
    node_id = f"entry:{function}:{register.upper()}"
    return node_id, {
        "id": node_id,
        "kind": "function-entry-register",
        "function": function,
        "register": register.upper(),
        "object_identity_proven": False,
    }


def _call_node(function: str, instruction: str, register: str) -> tuple[str, dict[str, Any]]:
    node_id = f"call-register:{function}:{instruction}:{register.upper()}"
    return node_id, {
        "id": node_id,
        "kind": "callsite-register",
        "function": function,
        "instruction": instruction,
        "register": register.upper(),
        "object_identity_proven": False,
    }


def _memory_node(function: str, source: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    instruction = source.get("instruction")
    base = source.get("base_register")
    displacement = source.get("displacement")
    kind = source.get("kind")
    if not isinstance(instruction, str) or not isinstance(base, str) or not isinstance(displacement, int):
        raise ValueError(f"{function}: malformed register-relative source")
    if kind not in {"register-relative-load", "register-relative-address"}:
        raise ValueError(f"{function}: unsupported memory source kind {kind!r}")
    node_id = f"memory-source:{function}:{instruction}:{base.upper()}:{displacement}"
    return node_id, {
        "id": node_id,
        "kind": kind,
        "function": function,
        "instruction": instruction,
        "base_register": base.upper(),
        "displacement": displacement,
        "displacement_hex": source.get("displacement_hex"),
        "object_identity_proven": False,
        "field_semantics_proven": False,
    }


def _source_node(function: str, source: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    kind = source.get("kind")
    if kind == "function-entry-register":
        register = source.get("register")
        if not isinstance(register, str):
            raise ValueError(f"{function}: entry source register missing")
        return _entry_node(function, register)
    if kind in {"register-relative-load", "register-relative-address"}:
        return _memory_node(function, source)
    return None


def _add_node(nodes: dict[str, dict[str, Any]], node: dict[str, Any]) -> None:
    node_id = node["id"]
    previous = nodes.get(node_id)
    if previous is not None and previous != node:
        raise ValueError(f"conflicting node definition for {node_id}")
    nodes[node_id] = node


def _edge_key(edge: dict[str, Any]) -> tuple[str, str, str]:
    return edge["from"], edge["to"], edge["relation"]


def _add_edge(edges: dict[tuple[str, str, str], dict[str, Any]], edge: dict[str, Any]) -> None:
    state = _require_state(edge.get("evidence_state"), "edge")
    edge["evidence_state"] = state
    key = _edge_key(edge)
    previous = edges.get(key)
    if previous is None:
        edges[key] = edge
        return
    previous["evidence_state"] = _weakest_state(previous["evidence_state"], state)
    previous_evidence = list(previous.get("evidence") or [])
    for item in edge.get("evidence") or []:
        if item not in previous_evidence:
            previous_evidence.append(item)
    previous["evidence"] = previous_evidence


def _receiver_index(receiver: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    if receiver.get("callee") != UPPER_CALLER:
        raise ValueError("receiver provenance callee anchor changed")
    rows = receiver.get("callsites")
    if not isinstance(rows, list) or not rows:
        raise ValueError("receiver provenance has no callsites")
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("receiver provenance contains invalid callsite")
        caller, instruction = row.get("caller"), row.get("call_instruction")
        if not isinstance(caller, str) or not isinstance(instruction, str):
            raise ValueError("receiver callsite identity missing")
        key = caller, instruction
        if key in result:
            raise ValueError(f"duplicate receiver callsite {caller}@{instruction}")
        result[key] = row
    return result


def _detect_cycles(nodes: dict[str, dict[str, Any]], edges: list[dict[str, Any]]) -> list[list[str]]:
    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        adjacency[edge["from"]].append(edge["to"])
    for values in adjacency.values():
        values.sort()

    color: dict[str, int] = {node_id: 0 for node_id in nodes}
    stack: list[str] = []
    stack_pos: dict[str, int] = {}
    cycles: set[tuple[str, ...]] = set()

    def visit(node: str) -> None:
        color[node] = 1
        stack_pos[node] = len(stack)
        stack.append(node)
        for target in adjacency.get(node, []):
            if target not in color:
                continue
            if color[target] == 0:
                visit(target)
            elif color[target] == 1:
                start = stack_pos[target]
                cycle = stack[start:] + [target]
                body = cycle[:-1]
                if body:
                    rotations = [tuple(body[i:] + body[:i]) for i in range(len(body))]
                    canonical = min(rotations)
                    cycles.add(canonical)
        stack.pop()
        stack_pos.pop(node, None)
        color[node] = 2

    for node_id in sorted(nodes):
        if color[node_id] == 0:
            visit(node_id)
    return [list(cycle) for cycle in sorted(cycles)]


def build_vehicle_pointer_value_closure(
    receiver_path: Path,
    pointer_path: Path,
    transfer_paths: list[Path],
) -> dict[str, Any]:
    receiver = _load(receiver_path, RECEIVER_FORMAT)
    pointer = _load(pointer_path, POINTER_FORMAT)
    transfers = [_load(path, TRANSFER_FORMAT) for path in transfer_paths]
    if pointer.get("upper_caller") != UPPER_CALLER:
        raise ValueError("pointer-origin upper-caller anchor changed")

    receiver_by_call = _receiver_index(receiver)
    pointer_origins = pointer.get("origins")
    if not isinstance(pointer_origins, list) or not pointer_origins:
        raise ValueError("pointer-origin report has no origins")

    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[tuple[str, str, str], dict[str, Any]] = {}
    blockers: list[dict[str, Any]] = []
    analyzed_parent_functions: set[str] = set()
    requested_targets: dict[str, set[str]] = defaultdict(set)

    for address in pointer.get("next_instruction_export_addresses") or []:
        if not isinstance(address, str):
            raise ValueError("pointer-origin target address must be a string")
        requested_targets[address].add("pointer-origin frontier")

    for origin in pointer_origins:
        if not isinstance(origin, dict):
            raise ValueError("pointer-origin report contains invalid origin")
        function = origin.get("caller")
        call_instruction = origin.get("call_instruction")
        if not isinstance(function, str) or not isinstance(call_instruction, str):
            raise ValueError("pointer-origin identity missing")
        receiver_row = receiver_by_call.get((function, call_instruction))
        if receiver_row is None:
            raise ValueError(
                f"pointer-origin callsite absent from receiver provenance: {function}@{call_instruction}"
            )

        abi_register = receiver_row.get("abi_receiver_register_candidate")
        if not isinstance(abi_register, str):
            blockers.append(
                {
                    "id": "receiver-register-unknown",
                    "function": function,
                    "instruction": call_instruction,
                    "evidence_state": "unknown",
                }
            )
            continue
        call_node_id, call_node = _call_node(function, call_instruction, abi_register)
        _add_node(nodes, call_node)

        receiver_source = origin.get("receiver_source")
        if isinstance(receiver_source, dict):
            receiver_source_pair = _source_node(function, receiver_source)
            if receiver_source_pair is not None:
                source_id, source_node = receiver_source_pair
                _add_node(nodes, source_node)
                receiver_state = _require_state(
                    (receiver_row.get("receiver_definition_trace") or {}).get("evidence_state", "unknown"),
                    f"{function}: receiver trace",
                )
                _add_edge(
                    edges,
                    {
                        "from": source_id,
                        "to": call_node_id,
                        "relation": "receiver-source-to-callsite-register",
                        "evidence_state": receiver_state,
                        "evidence": [f"receiver provenance {function}@{call_instruction}"],
                        "object_identity_proven": False,
                    },
                )

                base_trace = origin.get("base_origin_trace")
                if isinstance(base_trace, dict):
                    terminal = base_trace.get("source")
                    if isinstance(terminal, dict):
                        terminal_pair = _source_node(function, terminal)
                        if terminal_pair is not None:
                            terminal_id, terminal_node = terminal_pair
                            _add_node(nodes, terminal_node)
                            base_state = _require_state(
                                base_trace.get("evidence_state", "unknown"),
                                f"{function}: base origin trace",
                            )
                            if terminal_id != source_id:
                                _add_edge(
                                    edges,
                                    {
                                        "from": terminal_id,
                                        "to": source_id,
                                        "relation": "base-origin-to-receiver-source",
                                        "evidence_state": base_state,
                                        "evidence": [
                                            f"pointer-origin trace in {function}"
                                        ],
                                        "object_identity_proven": False,
                                    },
                                )
                    else:
                        blockers.append(
                            {
                                "id": "base-origin-terminal-missing",
                                "function": function,
                                "instruction": call_instruction,
                                "evidence_state": _require_state(
                                    base_trace.get("evidence_state", "unknown"),
                                    f"{function}: missing terminal",
                                ),
                            }
                        )
        else:
            blockers.append(
                {
                    "id": "receiver-source-missing",
                    "function": function,
                    "instruction": call_instruction,
                    "evidence_state": "unknown",
                }
            )

        for overlap in origin.get("vtable_store_overlaps") or []:
            if isinstance(overlap, dict):
                blockers.append(
                    {
                        "id": "heuristic-vtable-overlap",
                        "function": function,
                        "instruction": overlap.get("vtable_store_instruction"),
                        "base_register": overlap.get("base_register"),
                        "evidence_state": "ambiguous",
                        "pointer_alias_proven": False,
                    }
                )

    transfer_identity: set[tuple[str, str, str, str]] = set()
    for report_index, transfer_report in enumerate(transfers):
        report_path = transfer_paths[report_index]
        for address in transfer_report.get("next_instruction_export_addresses") or []:
            if not isinstance(address, str):
                raise ValueError(f"{report_path}: target address must be a string")
            requested_targets[address].add(f"parent-transfer:{report_path.name}")
        rows = transfer_report.get("transfers")
        if not isinstance(rows, list) or not rows:
            raise ValueError(f"{report_path}: transfer report has no transfers")
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError(f"{report_path}: invalid transfer row")
            parent = row.get("parent")
            child = row.get("child")
            instruction = row.get("call_instruction")
            register = row.get("entry_register")
            if not all(isinstance(value, str) for value in (parent, child, instruction, register)):
                raise ValueError(f"{report_path}: transfer identity missing")
            identity = parent, child, instruction, register.upper()
            transfer_identity.add(identity)
            analyzed_parent_functions.add(parent)

            parent_call_id, parent_call = _call_node(parent, instruction, register)
            child_entry_id, child_entry = _entry_node(child, register)
            _add_node(nodes, parent_call)
            _add_node(nodes, child_entry)
            transfer_state = _require_state(
                row.get("register_transfer_state", "unknown"),
                f"{parent}->{child}: transfer",
            )
            _add_edge(
                edges,
                {
                    "from": parent_call_id,
                    "to": child_entry_id,
                    "relation": "call-boundary-register-transfer",
                    "evidence_state": transfer_state,
                    "evidence": [f"{report_path.name}:{instruction}"],
                    "object_identity_proven": False,
                },
            )

            source_trace = row.get("parent_register_source_trace")
            if isinstance(source_trace, dict):
                terminal = source_trace.get("source")
                if isinstance(terminal, dict):
                    pair = _source_node(parent, terminal)
                    if pair is not None:
                        source_id, source_node = pair
                        _add_node(nodes, source_node)
                        source_state = _require_state(
                            source_trace.get("evidence_state", "unknown"),
                            f"{parent}: source trace",
                        )
                        if source_id != parent_call_id:
                            _add_edge(
                                edges,
                                {
                                    "from": source_id,
                                    "to": parent_call_id,
                                    "relation": "parent-source-to-callsite-register",
                                    "evidence_state": source_state,
                                    "evidence": [f"{report_path.name}:{parent}"],
                                    "object_identity_proven": False,
                                },
                            )
                elif source_trace.get("evidence_state") in {"ambiguous", "unknown"}:
                    blockers.append(
                        {
                            "id": "parent-source-terminal-unresolved",
                            "parent": parent,
                            "child": child,
                            "instruction": instruction,
                            "evidence_state": _require_state(
                                source_trace.get("evidence_state"),
                                f"{parent}: unresolved parent source",
                            ),
                        }
                    )

    current_frontier = {
        address: reasons
        for address, reasons in requested_targets.items()
        if address not in analyzed_parent_functions
    }

    edge_rows = sorted(
        edges.values(), key=lambda edge: (edge["from"], edge["to"], edge["relation"])
    )
    cycles = _detect_cycles(nodes, edge_rows)

    incoming_count: dict[str, int] = {node_id: 0 for node_id in nodes}
    outgoing_count: dict[str, int] = {node_id: 0 for node_id in nodes}
    for edge in edge_rows:
        incoming_count[edge["to"]] = incoming_count.get(edge["to"], 0) + 1
        outgoing_count[edge["from"]] = outgoing_count.get(edge["from"], 0) + 1
    static_endpoints = [
        {
            **nodes[node_id],
            "incoming_edge_count": incoming_count.get(node_id, 0),
            "outgoing_edge_count": outgoing_count.get(node_id, 0),
            "semantic_identity_proven": False,
        }
        for node_id in sorted(nodes)
        if incoming_count.get(node_id, 0) == 0 and outgoing_count.get(node_id, 0) > 0
    ]

    conflicts: list[dict[str, Any]] = []
    incoming_sources: dict[str, set[str]] = defaultdict(set)
    for edge in edge_rows:
        if edge["relation"] in {
            "receiver-source-to-callsite-register",
            "parent-source-to-callsite-register",
        }:
            incoming_sources[edge["to"]].add(edge["from"])
    for target, sources in sorted(incoming_sources.items()):
        if len(sources) > 1:
            conflicts.append(
                {
                    "id": "multiple-static-sources-for-one-callsite-register",
                    "target": target,
                    "sources": sorted(sources),
                    "evidence_state": "ambiguous",
                }
            )

    all_blockers = blockers + conflicts
    if cycles:
        all_blockers.append(
            {
                "id": "pointer-provenance-cycle",
                "evidence_state": "ambiguous",
                "cycle_count": len(cycles),
            }
        )

    weakest_graph_state = "proven"
    for edge in edge_rows:
        weakest_graph_state = _weakest_state(weakest_graph_state, edge["evidence_state"])
    if not edge_rows:
        weakest_graph_state = "unknown"

    frontier_rows = [
        {"address": address, "reasons": sorted(reasons), "promoted": False}
        for address, reasons in sorted(current_frontier.items())
    ]
    return {
        "format": FORMAT,
        "receiver_provenance": str(receiver_path),
        "pointer_origin_frontier": str(pointer_path),
        "parent_transfer_reports": [str(path) for path in transfer_paths],
        "upper_caller": UPPER_CALLER,
        "node_count": len(nodes),
        "edge_count": len(edge_rows),
        "nodes": [nodes[node_id] for node_id in sorted(nodes)],
        "edges": edge_rows,
        "cycle_count": len(cycles),
        "cycles": cycles,
        "source_conflict_count": len(conflicts),
        "source_conflicts": conflicts,
        "static_endpoint_count": len(static_endpoints),
        "static_endpoints": static_endpoints,
        "weakest_graph_evidence_state": weakest_graph_state,
        "analyzed_parent_functions": sorted(analyzed_parent_functions),
        "current_frontier_targets": frontier_rows,
        "current_frontier_addresses": [row["address"] for row in frontier_rows],
        "blocker_count": len(all_blockers),
        "blockers": all_blockers,
        "scope": {
            "composition_only_no_new_def_use_facts": True,
            "exact_callsite_register_nodes_used": True,
            "call_boundary_edges_import_existing_verified_transfer": True,
            "cycles_are_not_silently_collapsed": True,
            "multiple_sources_are_not_silently_chosen": True,
            "graph_connectivity_is_object_identity_proof": False,
            "static_endpoint_is_owner_identity_proof": False,
            "heuristic_vtable_overlap_is_alias_proof": False,
            "object_identity_proven": False,
            "owner_identity_proven": False,
            "class_identity_proven": False,
            "field_semantics_proven": False,
            "automatic_function_renaming_performed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receiver_provenance", type=Path)
    parser.add_argument("pointer_origin_frontier", type=Path)
    parser.add_argument("parent_transfers", type=Path, nargs="*")
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--targets-out", type=Path)
    parser.add_argument("--fail-on-cycle", action="store_true")
    parser.add_argument("--fail-on-source-conflict", action="store_true")
    args = parser.parse_args()
    report = build_vehicle_pointer_value_closure(
        args.receiver_provenance,
        args.pointer_origin_frontier,
        list(args.parent_transfers),
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    if args.targets_out:
        args.targets_out.parent.mkdir(parents=True, exist_ok=True)
        args.targets_out.write_text(
            "".join(address + "\n" for address in report["current_frontier_addresses"]),
            encoding="utf-8",
        )
    print(f"format: {report['format']}")
    print(f"nodes: {report['node_count']}")
    print(f"edges: {report['edge_count']}")
    print(f"cycles: {report['cycle_count']}")
    print(f"source conflicts: {report['source_conflict_count']}")
    print(f"frontier targets: {len(report['current_frontier_addresses'])}")
    if args.json_out:
        print(f"output: {args.json_out}")
    if args.targets_out:
        print(f"targets: {args.targets_out}")
    if args.fail_on_cycle and report["cycle_count"]:
        return 1
    if args.fail_on_source_conflict and report["source_conflict_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
