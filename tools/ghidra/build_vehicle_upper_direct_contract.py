#!/usr/bin/env python3
"""Promote only exact direct-call facts above the outer-update caller frontier.

Input is a `SHIFT.GhidraVehicleOuterUpdateCallerFrontier/1` report generated with
`--upstream-depth 3` or greater.  The tool verifies the currently known direct
chain above FUN_00794a30 and keeps ownership, scheduling, object identity and
offset semantics explicitly unresolved.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.VehicleUpperDirectContract/1"
CALLER_FRONTIER_FORMAT = "SHIFT.GhidraVehicleOuterUpdateCallerFrontier/1"

OUTER_UPDATE = "0x00770e80"
PRIMARY_CALLER = "0x00794a30"
ALTERNATE_CALLER = "0x0079b2d0"
BATCH = "0x00713050"
OWNER_FRONTIER = "0x00715380"
UPPER_CALLER = "0x007155e9"

EXPECTED_CHAIN = (
    (UPPER_CALLER, OWNER_FRONTIER, 1),
    (OWNER_FRONTIER, BATCH, 1),
    (BATCH, PRIMARY_CALLER, 3),
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _load(path: Path) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        raise ValueError(f"{path}: expected JSON object")
    if report.get("format") != CALLER_FRONTIER_FORMAT:
        raise ValueError(
            f"{path}: expected {CALLER_FRONTIER_FORMAT}, found {report.get('format')}"
        )
    return report


def _row_by_address(rows: list[dict[str, Any]], address: str, label: str) -> dict[str, Any]:
    matches = [row for row in rows if row.get("address") == address]
    if len(matches) != 1:
        raise ValueError(f"{label}: expected one row for {address}; found {len(matches)}")
    return matches[0]


def _edges_to(row: dict[str, Any], target: str) -> list[dict[str, Any]]:
    result = []
    for edge in row.get("ordered_direct_calls") or []:
        if edge.get("indirect") is False and edge.get("to") == target:
            result.append(
                {
                    "from_function": edge.get("from_function"),
                    "from_name": edge.get("from_name"),
                    "instruction": edge.get("instruction"),
                    "to": edge.get("to"),
                    "to_name": edge.get("to_name"),
                    "indirect": False,
                }
            )
    return result


def _ordered_targets(row: dict[str, Any]) -> list[str]:
    return [
        edge["to"]
        for edge in row.get("ordered_direct_calls") or []
        if edge.get("indirect") is False and isinstance(edge.get("to"), str)
    ]


def build_vehicle_upper_direct_contract(frontier_path: Path) -> dict[str, Any]:
    frontier = _load(frontier_path)
    _require(frontier.get("outer_update_anchor") == OUTER_UPDATE, "outer-update anchor changed")
    depth = frontier.get("upstream_depth")
    _require(isinstance(depth, int) and depth >= 3, "caller frontier must use --upstream-depth >= 3")

    direct_rows = frontier.get("direct_callers") or []
    direct_addresses = sorted(
        [row.get("address") for row in direct_rows if isinstance(row.get("address"), str)]
    )
    _require(
        direct_addresses == sorted([PRIMARY_CALLER, ALTERNATE_CALLER]),
        f"outer-update direct caller set changed: {direct_addresses}",
    )
    primary = _row_by_address(direct_rows, PRIMARY_CALLER, "direct callers")
    alternate = _row_by_address(direct_rows, ALTERNATE_CALLER, "direct callers")
    _require(
        alternate.get("direct_incoming_count") == 0,
        "alternate caller acquired a direct incoming owner; split frontier must be re-audited",
    )

    upstream_rows = frontier.get("upstream_candidates") or []
    expected_depth = {BATCH: 1, OWNER_FRONTIER: 2, UPPER_CALLER: 3}
    upstream = {
        address: _row_by_address(upstream_rows, address, "upstream candidates")
        for address in expected_depth
    }
    for address, wanted_depth in expected_depth.items():
        _require(
            upstream[address].get("upstream_depth") == wanted_depth,
            f"{address}: expected upstream depth {wanted_depth}, found {upstream[address].get('upstream_depth')}",
        )
        _require(
            upstream[address].get("function_metadata_present") is True,
            f"{address}: function metadata missing",
        )
        _require(
            upstream[address].get("external") is not True,
            f"{address}: unexpectedly external",
        )

    expected_incoming_counts = {
        PRIMARY_CALLER: 3,
        BATCH: 1,
        OWNER_FRONTIER: 1,
    }
    rows_by_address = {PRIMARY_CALLER: primary, **upstream}
    for address, expected_count in expected_incoming_counts.items():
        _require(
            rows_by_address[address].get("direct_incoming_count") == expected_count,
            f"{address}: expected {expected_count} direct incoming call(s); "
            f"found {rows_by_address[address].get('direct_incoming_count')}",
        )

    chain_edges: list[dict[str, Any]] = []
    for parent, child, expected_count in EXPECTED_CHAIN:
        matches = _edges_to(rows_by_address[parent], child)
        _require(
            len(matches) == expected_count,
            f"{parent}: expected {expected_count} direct call(s) to {child}; found {len(matches)}",
        )
        chain_edges.append(
            {
                "parent": parent,
                "child": child,
                "direct_call_count": len(matches),
                "calls": matches,
                "evidence_state": "verified",
                "semantic_role_proven": False,
            }
        )

    known_callers = {
        UPPER_CALLER: [],
        OWNER_FRONTIER: [UPPER_CALLER],
        BATCH: [OWNER_FRONTIER],
        PRIMARY_CALLER: [BATCH],
    }
    candidates = []
    for address in (UPPER_CALLER, OWNER_FRONTIER, BATCH, PRIMARY_CALLER):
        row = rows_by_address[address]
        candidates.append(
            {
                "address": address,
                "name": row.get("name"),
                "callers": known_callers[address],
                "caller_identities_complete": address != UPPER_CALLER,
                "direct_incoming_count": row.get("direct_incoming_count"),
                "callees": _ordered_targets(row),
                "read_offsets": [],
                "write_offsets": [],
                "pointer_base_register_evidence": "not available in the caller-frontier report; requires instruction/p-code evidence",
                "exact_instruction_or_pcode_evidence": [
                    edge["instruction"]
                    for edge in sum(
                        [item["calls"] for item in chain_edges if item["parent"] == address],
                        [],
                    )
                    if isinstance(edge.get("instruction"), str)
                ],
                "subsystem": "upper vehicle-update direct-call frontier",
                "evidence_state": "verified" if address != UPPER_CALLER else "inferred",
                "unresolved_blockers": [
                    "object/class identity",
                    "pointer ownership",
                    "input/control provenance",
                    "rendered-frame cadence",
                    "read/write offsets until p-code export is joined",
                ],
                "promoted_semantic_name": False,
            }
        )

    upper = upstream[UPPER_CALLER]
    instruction_targets = [UPPER_CALLER]
    blockers = [
        {
            "id": "upper-caller-owner",
            "address": UPPER_CALLER,
            "evidence_state": "unknown",
            "direct_incoming_count": upper.get("direct_incoming_count"),
            "required_evidence": (
                "one level deeper caller export and exact instruction/pointer provenance; "
                "the current contract intentionally does not infer an owner from count alone"
            ),
        },
        {
            "id": "upper-caller-object-identity",
            "address": UPPER_CALLER,
            "evidence_state": "unknown",
            "required_evidence": "constructor/vtable/destructor or registration evidence joined to exact pointer flow",
        },
        {
            "id": "input-control-provenance",
            "address": UPPER_CALLER,
            "evidence_state": "unknown",
            "required_evidence": "static argument/dataflow proof from an identified input/control source",
        },
        {
            "id": "rendered-frame-cadence",
            "address": UPPER_CALLER,
            "evidence_state": "unknown",
            "required_evidence": "static scheduler path proving invocation cadence",
        },
    ]

    return {
        "format": FORMAT,
        "input": str(frontier_path),
        "source_format": CALLER_FRONTIER_FORMAT,
        "source_upstream_depth": depth,
        "anchors": {
            "outer_update": OUTER_UPDATE,
            "primary_caller": PRIMARY_CALLER,
            "alternate_caller": ALTERNATE_CALLER,
            "batch": BATCH,
            "owner_frontier": OWNER_FRONTIER,
            "upper_caller": UPPER_CALLER,
        },
        "closure": {
            "upper_direct_path": "verified",
            "path": [UPPER_CALLER, OWNER_FRONTIER, BATCH, PRIMARY_CALLER, OUTER_UPDATE],
            "alternate_direct_caller_still_ownerless": True,
            "upper_object_identity": "unknown",
            "input_control_ownership": "unknown",
            "rendered_frame_cadence": "unknown",
        },
        "chain_edges": chain_edges,
        "candidates": candidates,
        "blockers": blockers,
        "instruction_export_addresses": instruction_targets,
        "scope": {
            "direct_call_edges_are_execution_evidence": True,
            "direct_call_edges_are_ownership_proof": False,
            "callgraph_depth_is_scheduler_proof": False,
            "callgraph_depth_is_class_identity_proof": False,
            "unknown_offsets_renamed": False,
            "physical_units_inferred": False,
            "automatic_function_renaming_performed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("caller_frontier", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--targets-out", type=Path)
    args = parser.parse_args()

    report = build_vehicle_upper_direct_contract(args.caller_frontier)
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
    print("upper direct path: " + " -> ".join(report["closure"]["path"]))
    print(f"remaining blockers: {len(report['blockers'])}")
    if args.json_out:
        print(f"output: {args.json_out}")
    if args.targets_out:
        print(f"targets: {args.targets_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
