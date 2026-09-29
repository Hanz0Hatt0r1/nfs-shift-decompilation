#!/usr/bin/env python3
"""Build a fail-closed AIW -> Path -> AIPolylinePath runtime instance graph."""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

FORMAT = "SHIFT-LIVE-MEMORY-TRACK-PATH-INSTANCE-GRAPH/1"
NODE_STRIDE = 0x24


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise SystemExit(f"missing input: {path}")
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def as_int(row: dict, key: str) -> int:
    try:
        value = row[key]
    except KeyError as exc:
        raise ValueError(f"invalid integer field {key!r}: {row!r}") from exc
    if isinstance(value, int):
        return value
    try:
        return int(value, 0)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid integer field {key!r}: {row!r}") from exc


def as_float(row: dict[str, str], key: str, default: float = 0.0) -> float:
    value = row.get(key)
    if value in (None, ""):
        return default
    try:
        number = float(value)
    except ValueError as exc:
        raise ValueError(f"invalid float field {key!r}: {row!r}") from exc
    if not math.isfinite(number):
        raise ValueError(f"non-finite float field {key!r}: {row!r}")
    return number


def edge_key(row: dict[str, str]) -> tuple[str, int, int]:
    return (
        row["aiw_source"],
        as_int(row, "from_waypoint"),
        as_int(row, "to_waypoint"),
    )


def node_address_index(nodes: list[dict[str, str]]) -> dict[int, list[dict[str, str]]]:
    by_address: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in nodes:
        address = as_int(row, "address")
        by_address[address].append(row)
    return by_address


def match_endpoint(
    match_rows: list[dict[str, str]],
    node_by_address: dict[int, list[dict[str, str]]],
) -> dict[tuple[str, int], list[dict]]:
    """Map AIW waypoint matches to every validated runtime node owner."""
    out: dict[tuple[str, int], list[dict]] = defaultdict(list)
    seen: set[tuple[str, int, int, int]] = set()
    for row in match_rows:
        source = row.get("aiw_source", "")
        waypoint = as_int(row, "waypoint_index")
        address = as_int(row, "runtime_address")
        for node in node_by_address.get(address, ()):
            ident = (
                source,
                waypoint,
                as_int(node, "path_address"),
                as_int(node, "index"),
            )
            if ident in seen:
                continue
            seen.add(ident)
            out[(source, waypoint)].append({
                "runtime_address": address,
                "path_address": as_int(node, "path_address"),
                "array_address": as_int(node, "array_address"),
                "node_index": as_int(node, "index"),
                "node_x": as_float(node, "x"),
                "node_y": as_float(node, "y"),
                "node_distance": as_float(node, "distance"),
                "match_distance": as_float(row, "distance"),
            })
    return out


def build_instance_edges(
    runtime_edges: list[dict[str, str]],
    endpoint_nodes: dict[tuple[str, int], list[dict]],
    path_polyline_links: list[dict[str, str]],
) -> list[dict]:
    polyline_by_array: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in path_polyline_links:
        polyline_by_array[as_int(row, "polyline_array")].append(row)

    out: list[dict] = []
    for edge in runtime_edges:
        source = edge["aiw_source"]
        from_wp = as_int(edge, "from_waypoint")
        to_wp = as_int(edge, "to_waypoint")
        sources = endpoint_nodes.get((source, from_wp), ())
        targets = endpoint_nodes.get((source, to_wp), ())
        for src in sources:
            for dst in targets:
                same_array = src["array_address"] == dst["array_address"]
                same_path = src["path_address"] == dst["path_address"]
                node_index_delta = dst["node_index"] - src["node_index"]
                runtime_delta = as_int(edge, "runtime_delta")
                expected_runtime_delta = node_index_delta * NODE_STRIDE
                runtime_stride_match = (
                    runtime_delta == expected_runtime_delta
                )
                owners = polyline_by_array.get(src["array_address"], ())
                path_join_count = sum(
                    1 for row in owners
                    if as_int(row, "path_address") == src["path_address"]
                )
                path_join_present = path_join_count > 0
                out.append({
                    "aiw_source": source,
                    "from_waypoint": from_wp,
                    "to_waypoint": to_wp,
                    "from_runtime_address": as_int(edge, "from_runtime_address"),
                    "to_runtime_address": as_int(edge, "to_runtime_address"),
                    "runtime_delta": runtime_delta,
                    "from_path_address": src["path_address"],
                    "to_path_address": dst["path_address"],
                    "from_array_address": src["array_address"],
                    "to_array_address": dst["array_address"],
                    "from_node_index": src["node_index"],
                    "to_node_index": dst["node_index"],
                    "node_index_delta": node_index_delta,
                    "expected_runtime_delta": expected_runtime_delta,
                    "runtime_stride_match": runtime_stride_match,
                    "same_array": same_array,
                    "same_path": same_path,
                    "path_polyline_join_count": path_join_count,
                    "path_polyline_join_present": path_join_present,
                    "from_match_distance": src["match_distance"],
                    "to_match_distance": dst["match_distance"],
                    "position_match_error": as_float(edge, "position_match_error"),
                    "graph_evidence": (
                        "runtime-node+same-array+stride"
                        if same_array and runtime_stride_match
                        else "runtime-node+same-array"
                        if same_array
                        else "runtime-node"
                    ),
                })
    out.sort(key=lambda row: (
        row["aiw_source"],
        row["from_waypoint"],
        row["to_waypoint"],
        row["from_path_address"],
        row["to_path_address"],
        row["from_node_index"],
        row["to_node_index"],
    ))
    return out


def summarize(
    runtime_edges: list[dict[str, str]],
    instance_edges: list[dict],
    path_polyline_links: list[dict[str, str]],
    runtime_matches: list[dict[str, str]],
) -> dict:
    normalized_keys = {edge_key(row) for row in runtime_edges}
    grouped: dict[tuple[str, int, int], list[dict]] = defaultdict(list)
    for row in instance_edges:
        grouped[edge_key(row)].append(row)

    fully_joined = {
        key for key, rows in grouped.items() if rows
    }
    exact_stride = sum(1 for row in instance_edges if row["runtime_stride_match"])
    same_array = sum(1 for row in instance_edges if row["same_array"])
    path_joined = sum(
        1 for row in instance_edges if row["path_polyline_join_present"]
    )

    match_addresses = {as_int(row, "runtime_address") for row in runtime_matches}
    node_addresses = {
        address
        for rows in grouped.values()
        for row in rows
        for address in (
            row["from_runtime_address"],
            row["to_runtime_address"],
        )
    }
    all_joined_addresses = match_addresses & node_addresses

    return {
        "format": FORMAT,
        "normalized_runtime_edge_count": len(runtime_edges),
        "runtime_instance_edge_candidate_count": len(instance_edges),
        "runtime_edge_group_count": len(grouped),
        "runtime_edges_with_node_owner": len(fully_joined),
        "runtime_edge_node_owner_coverage": (
            len(fully_joined) / len(normalized_keys)
            if normalized_keys else 0.0
        ),
        "same_array_candidate_count": same_array,
        "path_polyline_join_candidate_count": path_joined,
        "runtime_stride_match_candidate_count": exact_stride,
        "runtime_stride_match_coverage": (
            exact_stride / len(instance_edges) if instance_edges else 0.0
        ),
        "path_polyline_link_count": len(path_polyline_links),
        "runtime_match_count": len(runtime_matches),
        "node_owned_runtime_address_count": len(all_joined_addresses),
        "notes": [
            "This report joins existing runtime correlations through exact captured addresses and recovered container fields.",
            "Multiple endpoint owners are preserved as separate candidates; no ambiguous mapping is collapsed.",
            "A stride match is a structural consistency check against the recovered 0x24-byte AIPolyPathNode array element size, not a gameplay semantic claim.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Join AIW runtime edges to validated Path/AIPolylinePath node instances"
    )
    ap.add_argument("analysis_dir", type=Path)
    ap.add_argument(
        "--out",
        type=Path,
        help="output JSON; defaults to <analysis_dir>/track_path_instance_graph.json",
    )
    ap.add_argument(
        "--require-node-owner",
        action="store_true",
        help="return exit code 2 unless every normalized runtime edge has at least one node-owner candidate",
    )
    ap.add_argument(
        "--require-same-array",
        action="store_true",
        help="return exit code 2 unless every node-owner candidate uses the same AIPolyPathNode array for both endpoints",
    )
    ap.add_argument(
        "--require-stride",
        action="store_true",
        help="return exit code 2 unless every candidate has runtime_delta == node_index_delta * 0x24",
    )
    ap.add_argument(
        "--require-path-polyline-join",
        action="store_true",
        help="return exit code 2 unless every candidate maps to an exact Path/AIPolylinePath array join",
    )
    args = ap.parse_args()

    root = args.analysis_dir
    runtime_edges = load_csv(root / "aiw_runtime_edges.csv")
    runtime_matches = load_csv(root / "aiw_runtime_matches.csv")
    nodes = load_csv(root / "aipolylinepath_nodes.csv")
    path_polyline_links = load_csv(root / "path_polyline_links.csv")

    node_by_address = node_address_index(nodes)
    endpoint_nodes = match_endpoint(runtime_matches, node_by_address)
    instance_edges = build_instance_edges(
        runtime_edges,
        endpoint_nodes,
        path_polyline_links,
    )
    result = summarize(
        runtime_edges,
        instance_edges,
        path_polyline_links,
        runtime_matches,
    )

    out = args.out or root / "track_path_instance_graph.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    edge_out = out.with_name("track_path_instance_edges.csv")
    with edge_out.open("w", newline="", encoding="utf-8") as fh:
        keys = [
            "aiw_source", "from_waypoint", "to_waypoint",
            "from_runtime_address", "to_runtime_address", "runtime_delta",
            "from_path_address", "to_path_address",
            "from_array_address", "to_array_address",
            "from_node_index", "to_node_index", "node_index_delta",
            "expected_runtime_delta", "runtime_stride_match",
            "same_array", "same_path", "path_polyline_join_count",
            "from_match_distance", "to_match_distance",
            "position_match_error", "graph_evidence", "path_polyline_join_present",
        ]
        writer = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(instance_edges)

    normalized_keys = {edge_key(row) for row in runtime_edges}
    grouped_keys = {
        edge_key(row) for row in instance_edges
    }
    owner_complete = normalized_keys <= grouped_keys
    same_array_complete = (
        not normalized_keys
        or (
            owner_complete
            and bool(instance_edges)
            and all(row["same_array"] for row in instance_edges)
        )
    )
    stride_complete = (
        not normalized_keys
        or (
            owner_complete
            and bool(instance_edges)
            and all(row["runtime_stride_match"] for row in instance_edges)
        )
    )
    path_join_complete = (
        not normalized_keys
        or (
            owner_complete
            and bool(instance_edges)
            and all(row["path_polyline_join_present"] for row in instance_edges)
        )
    )

    print(f"runtime edges: {len(runtime_edges)}")
    print(f"instance edge candidates: {len(instance_edges)}")
    print(f"edge groups with node owners: {len(grouped_keys)}")
    print(f"same-array candidates: {sum(1 for r in instance_edges if r['same_array'])}")
    print(f"stride matches: {sum(1 for r in instance_edges if r['runtime_stride_match'])}")
    print(f"output: {out}")

    if args.require_node_owner and not owner_complete:
        return 2
    if args.require_same_array and not same_array_complete:
        return 2
    if args.require_stride and not stride_complete:
        return 2
    if args.require_path_polyline_join and not path_join_complete:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
