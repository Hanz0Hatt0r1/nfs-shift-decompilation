#!/usr/bin/env python3
"""Join heuristic vtable xrefs to proven subsystem callgraph slices.

The Ghidra database intentionally labels `vtables.json` and `constructors.jsonl`
as heuristic candidates. This tool does not upgrade those identities. It uses
proven physics/vehicle slices only to select which vtable-xref functions and
heuristic table slot targets deserve targeted instruction review next.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Iterable

from build_subsystem_manifests import build as build_subsystem_manifests
from join_method_anchors_to_subsystems import _subsystem_slice_addresses

FORMAT = "SHIFT.GhidraConstructionFrontier/1"
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


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected object")
    return payload


def _load_functions(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "functions.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"missing required Ghidra file: {path.name}")
    result: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(path):
        address = row.get("address")
        if not isinstance(address, str):
            continue
        if address in result:
            raise ValueError(f"{path}: duplicate function address {address}")
        result[address] = row
    return result


def _load_callgraph(root: Path):
    path = root / "callgraph.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"missing required Ghidra file: {path.name}")
    adjacency: dict[str, set[str]] = defaultdict(set)
    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _read_jsonl(path):
        if row.get("indirect") is not False:
            continue
        source = row.get("from_function")
        target = row.get("to")
        if not isinstance(source, str) or not isinstance(target, str):
            continue
        adjacency[source].add(target)
        adjacency[target].add(source)
        outgoing[source].append(row)
        incoming[target].append(row)
    return adjacency, outgoing, incoming


def _load_vtables(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "vtables.json"
    if not path.is_file():
        raise FileNotFoundError(f"missing required Ghidra file: {path.name}")
    payload = _read_json(path)
    if payload.get("format") != "SHIFT.GhidraVtableCandidates/1":
        raise ValueError(f"{path}: unsupported vtable candidate format")
    if payload.get("status") != "heuristic-candidates":
        raise ValueError(f"{path}: expected heuristic-candidates status")
    rows = payload.get("vtables")
    if not isinstance(rows, list):
        raise ValueError(f"{path}: vtables must be a list")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"{path}: invalid vtable row")
        address = row.get("address")
        if not isinstance(address, str):
            raise ValueError(f"{path}: vtable row missing address")
        if address in result:
            raise ValueError(f"{path}: duplicate vtable candidate {address}")
        slots = row.get("slots")
        if not isinstance(slots, list):
            raise ValueError(f"{path}: {address} slots must be a list")
        if row.get("slot_count") != len(slots):
            raise ValueError(f"{path}: {address} slot_count mismatch")
        result[address] = row
    return result


def _load_constructor_candidates(root: Path) -> list[dict[str, Any]]:
    path = root / "constructors.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"missing required Ghidra file: {path.name}")
    rows = list(_read_jsonl(path))
    seen: set[str] = set()
    for row in rows:
        if row.get("status") != "vtable-xref-candidate":
            raise ValueError(f"{path}: unexpected candidate status {row.get('status')!r}")
        function = row.get("function")
        if not isinstance(function, str):
            raise ValueError(f"{path}: candidate missing function")
        if function in seen:
            raise ValueError(f"{path}: duplicate constructor candidate {function}")
        seen.add(function)
        vtables = row.get("vtables")
        if not isinstance(vtables, list) or any(not isinstance(value, str) for value in vtables):
            raise ValueError(f"{path}: {function} vtables must be a string list")
    return rows


def _distances(roots: set[str], adjacency: dict[str, set[str]], max_depth: int) -> dict[str, int]:
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


def _edge_record(row: dict[str, Any], direction: str) -> dict[str, Any]:
    return {
        "direction": direction,
        "from_function": row.get("from_function"),
        "from_name": row.get("from_name"),
        "instruction": row.get("instruction"),
        "to": row.get("to"),
        "to_name": row.get("to_name"),
        "indirect": row.get("indirect"),
    }


def _instruction_key(row: dict[str, Any]) -> tuple[int, str]:
    value = row.get("instruction")
    if isinstance(value, str):
        try:
            return int(value, 16), value
        except ValueError:
            pass
    return (1 << 63), str(value or "")


def _candidate_sort_key(row: dict[str, Any]):
    depth = row["min_callgraph_depth"]
    return (
        0 if row["has_proven_slice_slot_target"] else 1,
        depth if isinstance(depth, int) else 1 << 30,
        -len(row["proven_slice_slot_targets"]),
        -len(row["referenced_vtables"]),
        row["function"],
    )


def build_construction_frontier(
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
    adjacency, outgoing, incoming = _load_callgraph(root)
    vtables = _load_vtables(root)
    constructor_candidates = _load_constructor_candidates(root)

    slices = {
        subsystem: _subsystem_slice_addresses(manifests[subsystem])
        for subsystem in selected
    }
    empty = [name for name, addresses in slices.items() if not addresses]
    if empty:
        raise ValueError("selected subsystem has empty proven slice: " + ", ".join(empty))
    root_addresses = set().union(*slices.values())
    distances = {
        subsystem: _distances(addresses, adjacency, max_depth)
        for subsystem, addresses in slices.items()
    }

    rows: list[dict[str, Any]] = []
    unlinked: list[dict[str, Any]] = []
    for candidate in constructor_candidates:
        function_address = candidate["function"]
        referenced_vtable_addresses = list(candidate["vtables"])
        missing_vtables = [address for address in referenced_vtable_addresses if address not in vtables]
        if missing_vtables:
            raise ValueError(
                f"constructors.jsonl: {function_address} references unknown vtable candidates: "
                + ", ".join(missing_vtables)
            )

        referenced_vtables: list[dict[str, Any]] = []
        proven_slot_targets: list[dict[str, Any]] = []
        for vtable_address in referenced_vtable_addresses:
            vtable = vtables[vtable_address]
            function_xrefs = vtable.get("function_xrefs")
            if not isinstance(function_xrefs, list) or any(
                not isinstance(value, str) for value in function_xrefs
            ):
                raise ValueError(f"vtables.json: {vtable_address} function_xrefs must be a string list")
            if function_address not in function_xrefs:
                raise ValueError(
                    f"cross-file vtable xref mismatch: {function_address} -> {vtable_address} "
                    "is absent from vtables.json function_xrefs"
                )

            matched_slots: list[dict[str, Any]] = []
            for slot in vtable["slots"]:
                if not isinstance(slot, dict):
                    raise ValueError(f"vtables.json: {vtable_address} invalid slot row")
                target = slot.get("target")
                if not isinstance(target, str):
                    continue
                matched_subsystems = sorted(
                    name for name, addresses in slices.items() if target in addresses
                )
                if not matched_subsystems:
                    continue
                record = {
                    "vtable": vtable_address,
                    "slot": slot.get("slot"),
                    "target": target,
                    "name": slot.get("name"),
                    "proven_subsystems": matched_subsystems,
                    "status": "heuristic-vtable-slot-targets-proven-slice-function",
                    "promoted": False,
                }
                matched_slots.append(record)
                proven_slot_targets.append(record)

            referenced_vtables.append(
                {
                    "address": vtable_address,
                    "block": vtable.get("block"),
                    "slot_count": vtable.get("slot_count"),
                    "function_xrefs": sorted(function_xrefs),
                    "proven_slice_slot_targets": matched_slots,
                    "status": "heuristic-vtable-candidate",
                    "promoted": False,
                }
            )

        subsystem_distances = {
            subsystem: values[function_address]
            for subsystem, values in distances.items()
            if function_address in values and values[function_address] > 0
        }
        min_depth = min(subsystem_distances.values()) if subsystem_distances else None

        direct_slice_edges = sorted(
            [
                _edge_record(edge, "candidate-to-slice")
                for edge in outgoing.get(function_address, [])
                if edge.get("to") in root_addresses
            ]
            + [
                _edge_record(edge, "slice-to-candidate")
                for edge in incoming.get(function_address, [])
                if edge.get("from_function") in root_addresses
            ],
            key=_instruction_key,
        )

        function = functions.get(function_address)
        if function is None:
            raise ValueError(
                f"constructors.jsonl: function metadata missing for {function_address}"
            )

        has_slot_target = bool(proven_slot_targets)
        selected_for_frontier = min_depth is not None or has_slot_target
        if min_depth == 1:
            status = "vtable-xref-direct-proven-slice-frontier"
        elif isinstance(min_depth, int):
            status = "vtable-xref-transitive-proven-slice-frontier"
        elif has_slot_target:
            status = "vtable-xref-with-proven-slice-slot-target"
        else:
            status = "vtable-xref-outside-selected-frontier"

        row = {
            "function": function_address,
            "name": function.get("name"),
            "calling_convention": function.get("calling_convention"),
            "signature": function.get("signature"),
            "size": function.get("size"),
            "external": function.get("external"),
            "thunk": function.get("thunk"),
            "candidate_source_status": candidate.get("status"),
            "instruction_preview": candidate.get("instruction_preview"),
            "referenced_vtables": referenced_vtables,
            "referenced_vtable_addresses": sorted(referenced_vtable_addresses),
            "proven_slice_slot_targets": sorted(
                proven_slot_targets,
                key=lambda item: (item["vtable"], item.get("slot") if isinstance(item.get("slot"), int) else 1 << 30),
            ),
            "has_proven_slice_slot_target": has_slot_target,
            "subsystem_distances": dict(sorted(subsystem_distances.items())),
            "connected_subsystems": sorted(subsystem_distances),
            "min_callgraph_depth": min_depth,
            "direct_proven_slice_edges": direct_slice_edges,
            "selected_for_frontier": selected_for_frontier,
            "promoted": False,
            "status": status,
        }
        if selected_for_frontier:
            rows.append(row)
        else:
            unlinked.append(row)

    rows.sort(key=_candidate_sort_key)
    unlinked.sort(key=lambda row: row["function"])
    exportable = [
        row for row in rows
        if row["external"] is not True and row["thunk"] is not True
    ]
    selected_targets = exportable[:max_targets]

    return {
        "format": FORMAT,
        "ghidra_export": str(root),
        "source": subsystem_report.get("source"),
        "selected_subsystems": list(selected),
        "max_depth": max_depth,
        "max_targets": max_targets,
        "heuristic_vtable_candidate_count": len(vtables),
        "heuristic_constructor_candidate_count": len(constructor_candidates),
        "frontier_candidate_count": len(rows),
        "unlinked_candidate_count": len(unlinked),
        "slot_linked_candidate_count": sum(row["has_proven_slice_slot_target"] for row in rows),
        "instruction_export_target_count": len(selected_targets),
        "subsystems": {
            name: {
                "proven_slice_address_count": len(addresses),
                "proven_slice_addresses": sorted(addresses),
            }
            for name, addresses in slices.items()
        },
        "frontier_candidates": rows,
        "unlinked_candidates": unlinked,
        "instruction_export_targets": [
            {
                "address": row["function"],
                "name": row["name"],
                "status": row["status"],
                "min_callgraph_depth": row["min_callgraph_depth"],
                "connected_subsystems": row["connected_subsystems"],
                "referenced_vtable_addresses": row["referenced_vtable_addresses"],
                "has_proven_slice_slot_target": row["has_proven_slice_slot_target"],
            }
            for row in selected_targets
        ],
        "instruction_export_addresses": [row["function"] for row in selected_targets],
        "scope": {
            "vtable_candidates_are_heuristic": True,
            "constructor_candidates_are_vtable_xref_candidates_only": True,
            "callgraph_edges_are_direct_only": True,
            "callgraph_traversal_is_bidirectional_for_target_selection": True,
            "vtable_slot_target_function_identity_is_static": True,
            "vtable_class_identity_proven": False,
            "constructor_identity_proven": False,
            "destructor_identity_proven": False,
            "vptr_store_proven": False,
            "virtual_dispatch_target_proven": False,
            "object_layout_proven": False,
            "automatic_function_renaming_performed": False,
            "note": (
                "This report cross-checks existing heuristic vtable/function xrefs against proven "
                "subsystem slices. A slot pointing at a proven slice function proves only the static "
                "pointer value in a heuristic table candidate. Targeted p-code/instruction evidence "
                "is still required to distinguish a vptr store from a read/compare and to establish "
                "constructor/destructor or virtual-dispatch semantics."
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
        help="subsystem root to join; repeatable (default: physics, vehicle)",
    )
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--max-targets", type=int, default=64)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument(
        "--targets-out",
        type=Path,
        help="write targeted instruction-export addresses, one per line",
    )
    args = parser.parse_args()

    report = build_construction_frontier(
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
    print(f"heuristic vtables: {report['heuristic_vtable_candidate_count']}")
    print(f"heuristic constructor candidates: {report['heuristic_constructor_candidate_count']}")
    print(f"construction frontier: {report['frontier_candidate_count']}")
    print(f"slot-linked candidates: {report['slot_linked_candidate_count']}")
    print(f"instruction-export targets: {report['instruction_export_target_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    if args.targets_out:
        print(f"targets: {args.targets_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
