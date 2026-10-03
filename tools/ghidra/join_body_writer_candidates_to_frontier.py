#!/usr/bin/env python3
"""Join BODY bridge candidates to the proven physics/vehicle callgraph frontier.

The join adds callgraph proximity/context only. It never promotes a bridge
candidate to a BODY writer, integrator or subsystem member.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.BodyWriterBridgeFrontierJoin/1"
BRIDGE_FORMAT = "SHIFT.BodyWriterBridgeCandidates/1"
FRONTIER_FORMAT = "SHIFT.GhidraProvenCallgraphFrontier/1"


def _load(path: Path, expected: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}")
    return value


def join_body_writer_candidates_to_frontier(
    bridge_report: dict[str, Any],
    frontier_report: dict[str, Any],
) -> dict[str, Any]:
    if bridge_report.get("format") != BRIDGE_FORMAT:
        raise ValueError(f"expected {BRIDGE_FORMAT}")
    if frontier_report.get("format") != FRONTIER_FORMAT:
        raise ValueError(f"expected {FRONTIER_FORMAT}")

    raw_candidates = bridge_report.get("candidates")
    raw_frontier = frontier_report.get("frontier_candidates")
    subsystems = frontier_report.get("subsystems")
    if not isinstance(raw_candidates, list):
        raise ValueError("bridge candidates must be a list")
    if not isinstance(raw_frontier, list):
        raise ValueError("frontier candidates must be a list")
    if not isinstance(subsystems, dict):
        raise ValueError("frontier subsystems must be an object")

    slice_membership: dict[str, set[str]] = defaultdict(set)
    for subsystem, entry in subsystems.items():
        if not isinstance(subsystem, str) or not isinstance(entry, dict):
            continue
        addresses = entry.get("proven_slice_addresses")
        if not isinstance(addresses, list):
            continue
        for address in addresses:
            if isinstance(address, str):
                slice_membership[address].add(subsystem)

    frontier_by_address: dict[str, dict[str, Any]] = {}
    duplicate_frontier_addresses: list[str] = []
    for row in raw_frontier:
        if not isinstance(row, dict) or not isinstance(row.get("address"), str):
            continue
        address = row["address"]
        if address in frontier_by_address:
            duplicate_frontier_addresses.append(address)
            continue
        frontier_by_address[address] = row

    indirect_by_function: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in frontier_report.get("indirect_blockers") or []:
        if not isinstance(row, dict):
            continue
        function = row.get("from_function")
        if isinstance(function, str):
            indirect_by_function[function].append(dict(row))

    joined: list[dict[str, Any]] = []
    malformed_candidates: list[dict[str, Any]] = []
    for index, candidate in enumerate(raw_candidates):
        if not isinstance(candidate, dict):
            malformed_candidates.append({"index": index, "reason": "candidate is not an object"})
            continue
        function = candidate.get("function")
        base_register = candidate.get("base_register")
        kind = candidate.get("kind")
        if not all(isinstance(value, str) and value for value in (function, base_register, kind)):
            malformed_candidates.append(
                {
                    "index": index,
                    "function": function,
                    "base_register": base_register,
                    "kind": kind,
                    "reason": "candidate function/base_register/kind missing",
                }
            )
            continue

        root_subsystems = sorted(slice_membership.get(function, set()))
        frontier = frontier_by_address.get(function)
        if root_subsystems:
            relation = "proven-slice-root"
            min_depth = 0
            connected_subsystems = root_subsystems
        elif frontier is not None:
            relation = "callgraph-frontier"
            min_depth = frontier.get("min_depth")
            connected_subsystems = list(frontier.get("connected_subsystems") or [])
        else:
            relation = "outside-selected-frontier"
            min_depth = None
            connected_subsystems = []

        row = {
            "kind": kind,
            "function": function,
            "function_name": candidate.get("function_name"),
            "base_register": base_register,
            "read_offsets": list(candidate.get("read_offsets") or []),
            "write_offsets": list(candidate.get("write_offsets") or []),
            "frontier_relation": relation,
            "min_depth": min_depth,
            "connected_subsystems": connected_subsystems,
            "proven_slice_root": bool(root_subsystems),
            "frontier_candidate": frontier is not None,
            "adjacent_proven_slice_addresses": (
                list(frontier.get("adjacent_proven_slice_addresses") or [])
                if frontier is not None
                else []
            ),
            "ordered_slice_calls": (
                list(frontier.get("ordered_slice_calls") or [])
                if frontier is not None
                else []
            ),
            "slice_callers": (
                list(frontier.get("slice_callers") or [])
                if frontier is not None
                else []
            ),
            "multi_anchor_caller_candidate": (
                frontier.get("multi_anchor_caller_candidate") is True
                if frontier is not None
                else False
            ),
            "direct_outgoing_count": frontier.get("direct_outgoing_count") if frontier else None,
            "direct_incoming_count": frontier.get("direct_incoming_count") if frontier else None,
            "indirect_call_sites": list(indirect_by_function.get(function, [])),
            "pointer_provenance_required": True,
            "body_writer_proven": False,
            "promoted": False,
        }
        joined.append(row)

    relation_order = {
        "proven-slice-root": 0,
        "callgraph-frontier": 1,
        "outside-selected-frontier": 2,
    }
    joined.sort(
        key=lambda row: (
            relation_order[row["frontier_relation"]],
            int(row["min_depth"]) if isinstance(row["min_depth"], int) else 1 << 30,
            row["function"],
            row["base_register"],
            row["kind"],
        )
    )

    return {
        "format": FORMAT,
        "bridge_candidate_format": BRIDGE_FORMAT,
        "frontier_format": FRONTIER_FORMAT,
        "selected_subsystems": list(frontier_report.get("selected_subsystems") or []),
        "candidate_count": len(raw_candidates),
        "joined_candidate_count": len(joined),
        "malformed_candidate_count": len(malformed_candidates),
        "duplicate_frontier_address_count": len(set(duplicate_frontier_addresses)),
        "proven_slice_root_candidate_count": sum(row["proven_slice_root"] for row in joined),
        "frontier_candidate_count": sum(row["frontier_candidate"] for row in joined),
        "outside_frontier_candidate_count": sum(
            row["frontier_relation"] == "outside-selected-frontier" for row in joined
        ),
        "direct_frontier_candidate_count": sum(
            row["frontier_relation"] == "callgraph-frontier" and row["min_depth"] == 1
            for row in joined
        ),
        "multi_anchor_bridge_candidate_count": sum(
            row["multi_anchor_caller_candidate"] for row in joined
        ),
        "candidates": joined,
        "malformed_candidates": malformed_candidates,
        "duplicate_frontier_addresses": sorted(set(duplicate_frontier_addresses)),
        "scope": {
            "callgraph_context_only": True,
            "proven_slice_membership_is_writer_proof": False,
            "frontier_membership_is_writer_proof": False,
            "callgraph_distance_is_semantic_ranking": False,
            "multi_anchor_caller_is_integrator_proof": False,
            "pointer_provenance_resolved": False,
            "body_or_vehicle_identity_proven": False,
            "persistent_state_writer_proven": False,
            "note": (
                "This join only reports whether a p-code access-pattern candidate is already a "
                "proven-slice root, a direct/transitive callgraph frontier member, or outside the "
                "selected frontier. Pointer provenance and exact update ordering remain required."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bridge_candidates", type=Path)
    parser.add_argument("--frontier", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--fail-on-outside", action="store_true")
    parser.add_argument("--fail-on-malformed", action="store_true")
    args = parser.parse_args()

    bridge = _load(args.bridge_candidates, BRIDGE_FORMAT)
    frontier = _load(args.frontier, FRONTIER_FORMAT)
    report = join_body_writer_candidates_to_frontier(bridge, frontier)

    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")

    print(f"format: {report['format']}")
    print(f"joined candidates: {report['joined_candidate_count']}")
    print(f"proven-slice roots: {report['proven_slice_root_candidate_count']}")
    print(f"frontier candidates: {report['frontier_candidate_count']}")
    print(f"outside frontier: {report['outside_frontier_candidate_count']}")
    print(f"multi-anchor bridge candidates: {report['multi_anchor_bridge_candidate_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")

    if args.fail_on_malformed and report["malformed_candidate_count"]:
        return 2
    if args.fail_on_outside and report["outside_frontier_candidate_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
