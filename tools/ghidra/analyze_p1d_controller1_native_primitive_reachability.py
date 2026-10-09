#!/usr/bin/env python3
"""Join P1D native/manual APC primitive candidates to Controller #1 direct reachability.

Input frontier is produced by analyze_p1d_controller1_native_apc_primitives.py.
The SQLite callgraph is navigation evidence only. A reachable primitive candidate
is not APC proof until exact service/API identity and target-thread identity are joined.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import deque
from pathlib import Path

FORMAT = "SHIFT.P1D.Controller1NativePrimitiveReachability/1"
INPUT_FORMAT = "SHIFT.P1D.Controller1NativeApcPrimitiveFrontier/1"
WORKER = "0x00662880"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_frontier(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("format") != INPUT_FORMAT:
        raise ValueError(f"unexpected primitive frontier format {payload.get('format')!r}")
    return payload


def build_graph(db: sqlite3.Connection) -> dict[str, list[str]]:
    graph: dict[str, list[str]] = {}
    for row in db.execute("SELECT raw_json FROM calls"):
        rec = json.loads(row[0])
        if rec.get("indirect"):
            continue
        src = rec.get("from_function") or rec.get("caller_address") or rec.get("caller")
        dst = rec.get("to") or rec.get("callee_address") or rec.get("callee")
        if not src or not dst:
            continue
        graph.setdefault(str(src).lower(), []).append(str(dst).lower())
    return graph


def shortest_tree(graph: dict[str, list[str]], start: str) -> dict[str, str | None]:
    start = start.lower()
    prev: dict[str, str | None] = {start: None}
    queue = deque([start])
    while queue:
        src = queue.popleft()
        for dst in graph.get(src, []):
            if dst in prev:
                continue
            prev[dst] = src
            queue.append(dst)
    return prev


def reconstruct(prev: dict[str, str | None], target: str) -> list[str]:
    target = target.lower()
    if target not in prev:
        return []
    path = [target]
    while prev[path[-1]] is not None:
        path.append(prev[path[-1]])
    return list(reversed(path))


def analyze(frontier_path: Path, db_path: Path) -> dict:
    frontier = load_frontier(frontier_path)
    db = sqlite3.connect(db_path)
    try:
        fmt = db.execute("SELECT value FROM metadata WHERE key='format'").fetchone()
        index_format = fmt[0] if fmt else "unknown"
        prev = shortest_tree(build_graph(db), WORKER)
    finally:
        db.close()

    joined: list[dict] = []
    for candidate in frontier.get("candidate_functions", []):
        address = str(candidate.get("function_address") or "").lower()
        reachable = bool(address) and address in prev
        joined.append(
            {
                "function": candidate.get("function"),
                "function_address": address or None,
                "manual_export_walk_candidate": bool(candidate.get("manual_export_walk_candidate")),
                "direct_native_call_candidate": bool(candidate.get("direct_native_call_candidate")),
                "peb_access_sites": candidate.get("peb_access_sites", []),
                "sysenter_sites": candidate.get("sysenter_sites", []),
                "int2e_sites": candidate.get("int2e_sites", []),
                "direct_worker_reachable": reachable,
                "shortest_direct_path": reconstruct(prev, address) if reachable else [],
                "candidate_only": True,
                "api_or_service_identity_proven": False,
                "controller1_target_thread_identity_proven": False,
            }
        )

    joined.sort(key=lambda row: (not row["direct_worker_reachable"], row["function_address"] or ""))
    reachable = [row for row in joined if row["direct_worker_reachable"]]
    reachable_manual = [row for row in reachable if row["manual_export_walk_candidate"]]
    reachable_native = [row for row in reachable if row["direct_native_call_candidate"]]

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "scope": "Controller #1 native/manual APC timing candidate reachability",
        "authority": {
            "primitive_frontier_format": INPUT_FORMAT,
            "primitive_frontier_sha256": digest(frontier_path),
            "source_index_format": index_format,
            "source_index_sha256": digest(db_path),
            "direct_callgraph_is_navigation_evidence_only": True,
        },
        "worker": WORKER,
        "counts": {
            "primitive_candidate_function_count": len(joined),
            "direct_worker_reachable_candidate_count": len(reachable),
            "direct_worker_reachable_manual_export_walk_candidate_count": len(reachable_manual),
            "direct_worker_reachable_native_transition_candidate_count": len(reachable_native),
        },
        "candidate_functions": joined,
        "adjudication": {
            "direct_reachability_join_complete_for_frontier_candidates": True,
            "unreachable_candidate_rejected_from_direct_worker_surface": True,
            "reachable_candidate_presence_proves_apc_injection": False,
            "indirect_callgraph_surface_ruled_out": False,
            "manual_export_walking_ruled_out": False,
            "native_or_syscall_apc_injection_ruled_out": False,
            "controller1_thread_handle_join_complete": False,
            "controller1_timing_exhaustive": False,
            "p1_3d_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "A direct-call graph cannot exhaust indirect calls, callbacks, virtual dispatch, generated code or external/native stubs.",
            "A reachable PEB/export or SYSENTER/INT 0x2e candidate remains navigation evidence until exact local machine flow identifies the resolved API/service.",
            "No candidate affects Controller #1 timing until the target thread or thread handle is proven to be Controller #1.",
            "An unreachable candidate is rejected only from the direct worker-call surface, not from all possible indirect execution paths."
        ],
        "next_step": (
            "Adjudicate direct-worker-reachable candidates first by exact machine flow. Recover resolved API/service identity, "
            "then prove or reject Controller #1 thread-handle identity. Separately handle indirect-only candidates before timing closure."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("frontier", type=Path)
    parser.add_argument("database", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = analyze(args.frontier, args.database)
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
