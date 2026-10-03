#!/usr/bin/env python3
"""Find exact method-name candidates one direct-call hop beyond proven subsystem slices.

This is a target-selection layer only.  A namespace-only exact method anchor can
enter the frontier when its function directly calls into, or is directly called
from, an already established subsystem slice.  Frontier membership never
promotes the function into that subsystem and never renames it.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from build_subsystem_manifests import build as build_subsystem_manifests
from join_method_anchors_to_subsystems import (
    _subsystem_slice_addresses,
    join_method_anchors_to_subsystems,
)

FORMAT = "SHIFT.GhidraSubsystemMethodFrontier/1"


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


def _load_direct_edges(root: Path):
    path = root / "callgraph.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"missing required Ghidra file: {path.name}")
    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _read_jsonl(path):
        if row.get("indirect") is not False:
            continue
        source = row.get("from_function")
        target = row.get("to")
        if isinstance(source, str):
            outgoing[source].append(row)
        if isinstance(target, str):
            incoming[target].append(row)
    return outgoing, incoming


def _edge_record(row: dict[str, Any], direction: str) -> dict[str, Any]:
    return {
        "direction": direction,
        "from_function": row.get("from_function"),
        "from_name": row.get("from_name"),
        "instruction": row.get("instruction"),
        "to": row.get("to"),
        "to_name": row.get("to_name"),
    }


def _frontier_links(
    address: str,
    slice_addresses: set[str],
    outgoing: dict[str, list[dict[str, Any]]],
    incoming: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()

    for edge in outgoing.get(address, []):
        target = edge.get("to")
        if target not in slice_addresses:
            continue
        key = (edge.get("from_function"), edge.get("instruction"), target, "candidate-to-slice")
        if key in seen:
            continue
        seen.add(key)
        rows.append(_edge_record(edge, "candidate-to-slice"))

    for edge in incoming.get(address, []):
        source = edge.get("from_function")
        if source not in slice_addresses:
            continue
        key = (source, edge.get("instruction"), edge.get("to"), "slice-to-candidate")
        if key in seen:
            continue
        seen.add(key)
        rows.append(_edge_record(edge, "slice-to-candidate"))

    rows.sort(
        key=lambda row: (
            str(row.get("direction") or ""),
            str(row.get("from_function") or ""),
            str(row.get("instruction") or ""),
            str(row.get("to") or ""),
        )
    )
    return rows


def _connected_slice_addresses(
    address: str,
    links: list[dict[str, Any]],
) -> list[str]:
    connected: set[str] = set()
    for edge in links:
        if edge["direction"] == "candidate-to-slice":
            target = edge.get("to")
            if isinstance(target, str):
                connected.add(target)
        elif edge["direction"] == "slice-to-candidate":
            source = edge.get("from_function")
            if isinstance(source, str):
                connected.add(source)
    connected.discard(address)
    return sorted(connected)


def build_subsystem_method_frontier(root: Path) -> dict[str, Any]:
    subsystem_report = build_subsystem_manifests(root)
    joined = join_method_anchors_to_subsystems(root)
    outgoing, incoming = _load_direct_edges(root)

    subsystem_manifests = subsystem_report.get("subsystems") or {}
    slices = {
        subsystem: _subsystem_slice_addresses(manifest)
        for subsystem, manifest in subsystem_manifests.items()
    }

    rows: list[dict[str, Any]] = []
    for candidate in joined.get("unique_candidates") or []:
        subsystem = candidate.get("namespace_subsystem")
        address = candidate.get("address")
        if not isinstance(subsystem, str) or not isinstance(address, str):
            continue
        if candidate.get("promoted") is True:
            continue
        slice_addresses = slices.get(subsystem)
        if slice_addresses is None:
            continue
        links = _frontier_links(address, slice_addresses, outgoing, incoming)
        connected = _connected_slice_addresses(address, links)
        directions = sorted({str(edge["direction"]) for edge in links})
        frontier = bool(links)
        rows.append(
            {
                "address": address,
                "ghidra_name": candidate.get("ghidra_name"),
                "method_name": candidate.get("method_name"),
                "subsystem": subsystem,
                "slice_address_count": len(slice_addresses),
                "connected_slice_addresses": connected,
                "direct_link_directions": directions,
                "direct_links": links,
                "frontier_candidate": frontier,
                "promoted": False,
                "status": (
                    "one-hop-subsystem-frontier-candidate"
                    if frontier
                    else "namespace-only-no-one-hop-link"
                ),
                "calling_convention": candidate.get("calling_convention"),
                "size": candidate.get("size"),
                "mnemonic_sha256": candidate.get("mnemonic_sha256"),
                "anchor_string_addresses": candidate.get("anchor_string_addresses") or [],
            }
        )

    rows.sort(key=lambda row: (row["subsystem"], row["address"], str(row["method_name"])))
    frontier_rows = [row for row in rows if row["frontier_candidate"]]
    disconnected_rows = [row for row in rows if not row["frontier_candidate"]]

    per_subsystem: dict[str, dict[str, Any]] = {}
    for subsystem in sorted(slices):
        subsystem_rows = [row for row in rows if row["subsystem"] == subsystem]
        subsystem_frontier = [row for row in subsystem_rows if row["frontier_candidate"]]
        per_subsystem[subsystem] = {
            "slice_address_count": len(slices[subsystem]),
            "namespace_only_candidate_count": len(subsystem_rows),
            "one_hop_frontier_candidate_count": len(subsystem_frontier),
            "candidates": subsystem_rows,
        }

    ambiguous_near_slice: list[dict[str, Any]] = []
    for ambiguous in joined.get("ambiguous_functions") or []:
        address = ambiguous.get("address")
        if not isinstance(address, str):
            continue
        for subsystem in ambiguous.get("namespace_subsystems") or []:
            if subsystem not in slices:
                continue
            links = _frontier_links(address, slices[subsystem], outgoing, incoming)
            if not links:
                continue
            ambiguous_near_slice.append(
                {
                    "address": address,
                    "ghidra_name": ambiguous.get("ghidra_name"),
                    "method_anchors": ambiguous.get("method_anchors") or [],
                    "subsystem": subsystem,
                    "connected_slice_addresses": _connected_slice_addresses(address, links),
                    "direct_links": links,
                    "frontier_candidate": False,
                    "promoted": False,
                    "status": "ambiguous-method-anchor-near-subsystem-slice",
                }
            )
    ambiguous_near_slice.sort(key=lambda row: (row["subsystem"], row["address"]))

    return {
        "format": FORMAT,
        "ghidra_export": str(root),
        "source": subsystem_report.get("source"),
        "subsystem_method_anchor_format": joined.get("format"),
        "namespace_only_candidate_count": len(rows),
        "one_hop_frontier_candidate_count": len(frontier_rows),
        "namespace_only_no_one_hop_link_count": len(disconnected_rows),
        "ambiguous_near_slice_count": len(ambiguous_near_slice),
        "subsystems": per_subsystem,
        "frontier_candidates": frontier_rows,
        "namespace_only_without_one_hop_link": disconnected_rows,
        "ambiguous_near_slice": ambiguous_near_slice,
        "scope": {
            "direct_call_edges_only": True,
            "namespace_only_unique_method_candidates_only": True,
            "existing_subsystem_slice_required": True,
            "one_hop_link_is_semantic_promotion": False,
            "ambiguous_functions_promoted": False,
            "automatic_function_renaming_performed": False,
            "method_behavior_proven": False,
            "note": (
                "Frontier membership only prioritizes a namespace-compatible exact method-name "
                "candidate because it has a direct call edge to/from an independently established "
                "subsystem slice. It does not extend the slice or prove the named method."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = build_subsystem_method_frontier(args.ghidra_export)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"namespace-only candidates: {report['namespace_only_candidate_count']}")
    print(f"one-hop frontier candidates: {report['one_hop_frontier_candidate_count']}")
    print(f"ambiguous near slice: {report['ambiguous_near_slice_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
