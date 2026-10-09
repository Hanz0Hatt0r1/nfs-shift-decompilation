#!/usr/bin/env python3
"""Bound shallow named bulk-copy callees around proven wheel lifecycle roots.

This is navigation evidence only. Zero named memcpy/memmove calls does not rule
out inline copies, aliases, indirect calls, custom copy helpers, or deeper paths.
Version-1 SQLite call rows are normalized from raw_json.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sqlite3
from pathlib import Path

FORMAT = "SHIFT.P1D.Slot3ShallowCopyFrontier/1"
SUPPORTED_INDEXES = {"SHIFT.GhidraSQLiteIndex/1", "SHIFT.GhidraSQLiteIndex/2"}
DEFAULT_ROOTS = (
    "FUN_00758b50",
    "FUN_0076d100",
    "FUN_00763570",
    "FUN_00770e80",
)
COPY_NAMES = {
    "memcpy",
    "_memcpy",
    "memcpy_s",
    "_memcpy_s",
    "memmove",
    "_memmove",
    "memmove_s",
    "_memmove_s",
    "__VEC_memcpy",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_direct_graph(db_path: Path) -> tuple[str, dict[str, list[dict]]]:
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    try:
        fmt_row = db.execute("SELECT value FROM metadata WHERE key='format'").fetchone()
        if not fmt_row or fmt_row[0] not in SUPPORTED_INDEXES:
            raise ValueError("unsupported Ghidra SQLite index")
        fmt = str(fmt_row[0])
        graph: dict[str, list[dict]] = collections.defaultdict(list)
        for row in db.execute("SELECT raw_json FROM calls"):
            rec = json.loads(row["raw_json"])
            if rec.get("indirect"):
                continue
            src_name = str(rec.get("from_name") or rec.get("caller") or rec.get("from_function") or "")
            src_addr = str(rec.get("from_function") or rec.get("caller_address") or "")
            dst_name = str(rec.get("to_name") or rec.get("callee") or rec.get("to") or "")
            dst_addr = str(rec.get("to") or rec.get("callee_address") or "")
            if not src_name and not src_addr:
                continue
            edge = {
                "from_name": src_name,
                "from_address": src_addr,
                "instruction": str(rec.get("instruction") or rec.get("callsite") or ""),
                "to_name": dst_name,
                "to_address": dst_addr,
            }
            if src_name:
                graph[src_name].append(edge)
            if src_addr and src_addr != src_name:
                graph[src_addr].append(edge)
        return fmt, graph
    finally:
        db.close()


def is_named_copy(edge: dict) -> bool:
    names = {str(edge.get("to_name", "")), str(edge.get("to_address", ""))}
    for name in names:
        if name in COPY_NAMES:
            return True
        lower = name.lower()
        if "memcpy" in lower or "memmove" in lower:
            return True
    return False


def traverse(root: str, graph: dict[str, list[dict]], max_depth: int) -> dict:
    queue = collections.deque([(root, 0, [root])])
    best_depth = {root: 0}
    nodes_by_depth: collections.Counter[int] = collections.Counter()
    copy_hits: list[dict] = []

    while queue:
        node, depth, path = queue.popleft()
        nodes_by_depth[depth] += 1
        if depth >= max_depth:
            continue
        for edge in graph.get(node, []):
            target = edge["to_name"] or edge["to_address"]
            next_depth = depth + 1
            next_path = path + [target]
            if is_named_copy(edge):
                copy_hits.append(
                    {
                        "depth": next_depth,
                        "callsite": edge["instruction"],
                        "caller": node,
                        "callee": target,
                        "path": next_path,
                    }
                )
            prior = best_depth.get(target)
            if prior is None or next_depth < prior:
                best_depth[target] = next_depth
                queue.append((target, next_depth, next_path))

    return {
        "root": root,
        "max_depth": max_depth,
        "reachable_unique_node_count": len(best_depth),
        "nodes_by_min_depth": {str(k): nodes_by_depth[k] for k in sorted(nodes_by_depth)},
        "named_copy_hit_count": len(copy_hits),
        "named_copy_hits": copy_hits,
    }


def analyze(db_path: Path, roots: tuple[str, ...] = DEFAULT_ROOTS, max_depth: int = 4) -> dict:
    if max_depth < 1:
        raise ValueError("max_depth must be >= 1")
    fmt, graph = load_direct_graph(db_path)
    results = [traverse(root, graph, max_depth) for root in roots]
    total_hits = sum(item["named_copy_hit_count"] for item in results)
    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "scope": "HDVehicle+0x28b8 slot3 bulk-copy navigation frontier",
        "authority": {
            "source_index_format": fmt,
            "source_index_sha256": sha256(db_path),
            "index_is_navigation_evidence_only": True,
        },
        "roots": list(roots),
        "max_direct_call_depth": max_depth,
        "named_copy_symbols": sorted(COPY_NAMES),
        "root_results": results,
        "summary": {
            "named_copy_hits_within_depth": total_hits,
            "all_roots_empty_for_named_copy_calls": total_hits == 0,
        },
        "adjudication": {
            "shallow_named_memcpy_memmove_surface_empty": total_hits == 0,
            "inline_or_custom_bulk_copy_ruled_out": False,
            "indirect_copy_dispatch_ruled_out": False,
            "deeper_direct_copy_paths_ruled_out": False,
            "slot3_writer_provenance_proven": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This scan follows direct call edges only and cannot reject indirect/callback copy dispatch.",
            "Named memcpy/memmove absence cannot reject compiler-inlined copies or custom copy helpers.",
            "The depth bound is a prioritization frontier, not a semantic reachability theorem.",
            "A copy routine on a deeper path would still require exact destination range and selected-HDVehicle root provenance."
        ],
        "next_step": (
            "Prioritize exact +0x538 STORE/address-materializer/callee candidates from the corrected Ghidra exporter. "
            "If none writes the target, extend copy analysis only along concrete alias-forwarding callees rather than broadening the entire callgraph blindly."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("--depth", type=int, default=4)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = analyze(args.database, max_depth=args.depth)
    except ValueError as exc:
        parser.error(str(exc))
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
