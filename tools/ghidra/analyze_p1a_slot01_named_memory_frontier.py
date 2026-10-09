#!/usr/bin/env python3
"""Bound named memory-family reachability from P1.3A wheel/physics roots.

This is navigation evidence only. A reachable memcpy/memmove/memset symbol is not
proof that the call touches selected HDVehicle+0x938 or +0x13b8. The tool records
shortest direct-call paths so exact alias/destination provenance can be traced
without broad callgraph expansion.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sqlite3
from pathlib import Path

FORMAT = "SHIFT.P1A.P13ASlot01NamedMemoryFrontier/1"
SUPPORTED_INDEXES = {"SHIFT.GhidraSQLiteIndex/1", "SHIFT.GhidraSQLiteIndex/2"}
DEFAULT_ROOTS = (
    "FUN_00758b50",
    "FUN_0076d100",
    "FUN_00763570",
    "FUN_00770e80",
)
COPY_SYMBOLS = {
    "__VEC_memcpy", "_memcpy", "_memcpy_s", "_memmove", "_memmove_s",
    "memcpy", "memcpy_s", "memmove", "memmove_s",
}
SET_SYMBOLS = {
    "__VEC_memset", "_memset", "memset", "memset_s", "RtlFillMemory", "RtlZeroMemory",
}


def _index_format(db: sqlite3.Connection) -> str:
    row = db.execute("SELECT value FROM metadata WHERE key='format'").fetchone()
    if row is None:
        raise ValueError("SQLite index has no metadata format")
    fmt = str(row[0])
    if fmt not in SUPPORTED_INDEXES:
        raise ValueError(f"unsupported SQLite index format: {fmt!r}")
    return fmt


def _direct_edges(db: sqlite3.Connection, fmt: str) -> dict[str, list[tuple[str, str]]]:
    adj: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
    if fmt == "SHIFT.GhidraSQLiteIndex/1":
        for (raw_json,) in db.execute("SELECT raw_json FROM calls"):
            rec = json.loads(raw_json)
            if rec.get("indirect"):
                continue
            src = str(rec.get("from_name") or rec.get("from_function") or "")
            dst = str(rec.get("to_name") or rec.get("to") or "")
            site = str(rec.get("instruction") or rec.get("callsite") or "")
            if src and dst:
                adj[src].append((dst, site))
        return adj

    rows = db.execute(
        "SELECT caller,callee,callsite,kind,indirect FROM calls"
    )
    for caller, callee, callsite, kind, indirect in rows:
        if indirect or str(kind).lower() == "indirect":
            continue
        if caller and callee:
            adj[str(caller)].append((str(callee), str(callsite or "")))
    return adj


def _bfs(adjacency: dict[str, list[tuple[str, str]]], root: str, max_depth: int):
    distance = {root: 0}
    parent: dict[str, str] = {}
    parent_site: dict[str, str] = {}
    queue = collections.deque([root])
    while queue:
        node = queue.popleft()
        if distance[node] >= max_depth:
            continue
        for callee, callsite in adjacency.get(node, []):
            if callee in distance:
                continue
            distance[callee] = distance[node] + 1
            parent[callee] = node
            parent_site[callee] = callsite
            queue.append(callee)
    return distance, parent, parent_site


def _nearest_group(root: str, names: set[str], distance, parent, parent_site) -> dict:
    reachable = [name for name in names if name in distance]
    if not reachable:
        return {"nearest_depth": None, "nearest_symbols": [], "nearest_paths": []}
    depth = min(distance[name] for name in reachable)
    nearest = sorted(name for name in reachable if distance[name] == depth)
    paths = []
    for symbol in nearest:
        nodes = [symbol]
        callsites = []
        cur = symbol
        while cur != root:
            callsites.append(parent_site[cur])
            cur = parent[cur]
            nodes.append(cur)
        nodes.reverse()
        callsites.reverse()
        paths.append({
            "symbol": symbol,
            "depth": depth,
            "nodes": nodes,
            "callsites": callsites,
        })
    return {"nearest_depth": depth, "nearest_symbols": nearest, "nearest_paths": paths}


def analyze(db_path: Path, roots=DEFAULT_ROOTS, max_depth: int = 12) -> dict:
    if max_depth < 1:
        raise ValueError("max_depth must be >= 1")
    source_sha256 = hashlib.sha256(db_path.read_bytes()).hexdigest()
    db = sqlite3.connect(db_path)
    try:
        fmt = _index_format(db)
        adjacency = _direct_edges(db, fmt)
    finally:
        db.close()

    root_results = []
    for root in roots:
        distance, parent, parent_site = _bfs(adjacency, root, max_depth)
        by_depth = collections.Counter(distance.values())
        root_results.append({
            "root": root,
            "max_depth": max_depth,
            "reachable_unique_node_count": len(distance),
            "nodes_by_min_depth": {str(k): by_depth[k] for k in sorted(by_depth)},
            "copy_family": _nearest_group(root, COPY_SYMBOLS, distance, parent, parent_site),
            "set_family": _nearest_group(root, SET_SYMBOLS, distance, parent, parent_site),
        })

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1A / P1.3A",
        "scope": "slot0 HDVehicle+0x938 and slot1 HDVehicle+0x13b8 named memory-family navigation frontier",
        "source_index_format": fmt,
        "source_index_sha256": source_sha256,
        "roots": list(roots),
        "max_direct_call_depth": max_depth,
        "copy_symbols": sorted(COPY_SYMBOLS),
        "set_symbols": sorted(SET_SYMBOLS),
        "root_results": root_results,
        "adjudication": {
            "navigation_frontier_captured": True,
            "named_memory_reachability_proves_target_alias": False,
            "slot0_selected_root_alias_callee_bulk_copy_complete": False,
            "slot1_selected_root_alias_callee_bulk_copy_complete": False,
            "p13a_slot0_complete": False,
            "p13a_slot1_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "next_step": (
            "Trace only the nearest game-side copy/set paths that intersect a concrete "
            "selected-HDVehicle wheel alias from the topology exporter; do not broaden "
            "the whole callgraph or promote semantic gates from symbol reachability alone."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("--max-depth", type=int, default=12)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = analyze(args.database, max_depth=args.max_depth)
    except ValueError as exc:
        parser.error(str(exc))
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
