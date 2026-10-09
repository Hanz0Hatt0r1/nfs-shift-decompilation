#!/usr/bin/env python3
"""Bound direct-call reachability from Controller #1 to GetProcAddress callers.

This is navigation evidence only. Direct-call reachability cannot rule out indirect
calls, callbacks, virtual dispatch, manual export walking, or native/syscall APC
injection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import defaultdict, deque
from pathlib import Path

FORMAT = "SHIFT.P1D.Controller1DirectResolverReachability/1"
SUPPORTED_INDEX_FORMATS = {"SHIFT.GhidraSQLiteIndex/1", "SHIFT.GhidraSQLiteIndex/2"}
WORKER = "0x00662880"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def analyze(db_path: Path) -> dict:
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    try:
        metadata = dict(db.execute("SELECT key,value FROM metadata").fetchall())
        index_format = metadata.get("format")
        if index_format not in SUPPORTED_INDEX_FORMATS:
            raise ValueError(f"unsupported Ghidra SQLite index format: {index_format!r}")

        adjacency: dict[str, set[str]] = defaultdict(set)
        resolver_calls: list[dict] = []
        for row in db.execute("SELECT raw_json FROM calls"):
            rec = json.loads(row["raw_json"])
            src = rec.get("from_function")
            dst = rec.get("to")
            if src and dst and isinstance(dst, str) and dst.startswith("0x"):
                adjacency[src].add(dst)
            if rec.get("to_name") == "GetProcAddress":
                resolver_calls.append(rec)

        all_resolver_callers = sorted(
            {rec.get("from_function") for rec in resolver_calls if rec.get("from_function")}
        )
        resolver_call_count_by_caller = defaultdict(int)
        for rec in resolver_calls:
            caller = rec.get("from_function")
            if caller:
                resolver_call_count_by_caller[caller] += 1

        distance = {WORKER: 0}
        predecessor: dict[str, str] = {}
        queue = deque([WORKER])
        while queue:
            node = queue.popleft()
            for nxt in adjacency.get(node, ()):
                if nxt not in distance:
                    distance[nxt] = distance[node] + 1
                    predecessor[nxt] = node
                    queue.append(nxt)

        def shortest_path(target: str) -> list[str]:
            path = [target]
            while path[-1] != WORKER:
                path.append(predecessor[path[-1]])
            path.reverse()
            return path

        reachable = []
        for caller in all_resolver_callers:
            if caller not in distance:
                continue
            strings = [
                {"address": row["address"], "value": row["value"]}
                for row in db.execute(
                    "SELECT address,value FROM strings WHERE containing_function = ? ORDER BY address",
                    (caller,),
                )
            ]
            reachable.append(
                {
                    "caller": caller,
                    "distance": distance[caller],
                    "getprocaddress_call_count": resolver_call_count_by_caller[caller],
                    "shortest_direct_path": shortest_path(caller),
                    "contained_strings": strings,
                }
            )
    finally:
        db.close()

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "authority": {
            "source_index_format": index_format,
            "source_index_sha256": digest(db_path),
            "source_dir": metadata.get("source_dir"),
            "index_is_navigation_evidence_only": True,
        },
        "worker": WORKER,
        "resolver_surface": {
            "all_getprocaddress_call_count": len(resolver_calls),
            "all_unique_resolver_callers": len(all_resolver_callers),
            "directly_reachable_unique_resolver_callers": len(reachable),
            "directly_reachable_getprocaddress_call_count": sum(
                row["getprocaddress_call_count"] for row in reachable
            ),
            "directly_reachable": reachable,
        },
        "adjudication": {
            "direct_callgraph_resolver_surface_bounded": True,
            "direct_worker_reachable_resolver_count": len(reachable),
            "direct_worker_reachable_plain_apc_name_evidence": False,
            "indirect_callgraph_surface_ruled_out": False,
            "hashed_or_generated_resolution_ruled_out": False,
            "manual_export_walk_ruled_out": False,
            "native_or_syscall_injection_ruled_out": False,
            "controller1_timing_exhaustive": False,
            "p1_3d_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "A direct-call graph cannot model indirect calls, callbacks or virtual dispatch exhaustively.",
            "Strings contained by a function are candidate context; they are not argument-flow proof by themselves.",
            "The absence of APC names on reachable resolver callers does not rule out hashed/generated API names.",
            "No reachability result changes Controller #1 timing gates without exact target-thread and API/service identity."
        ],
        "next_step": "Adjudicate indirect/native primitive candidates and exact target-thread identity; keep Controller #1 timing fail-closed until those surfaces are exhausted."
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = analyze(args.database)
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
