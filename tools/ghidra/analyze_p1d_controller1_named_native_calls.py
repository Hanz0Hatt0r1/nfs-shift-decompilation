#!/usr/bin/env python3
"""Bound direct named Nt*/Zw*/Rtl* call targets for Controller #1 APC timing.

This is a narrow named-native surface only. It does not rule out direct syscalls,
indirect ntdll pointers, generated stubs, wow64 transitions, or manual resolution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from collections import deque
from pathlib import Path

FORMAT = "SHIFT.P1D.Controller1NamedNativeCallSurface/1"
WORKER = "0x00662880"
NATIVE_NAME_RE = re.compile(r"^(?:Nt|Zw|Rtl)")
APC_NATIVE_NAMES = {
    "ntqueueapcthread",
    "ntqueueapcthreadex",
    "zwqueueapcthread",
    "rtlqueueapcwow64thread",
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_calls(db: sqlite3.Connection) -> list[dict]:
    return [json.loads(row[0]) for row in db.execute("SELECT raw_json FROM calls")]


def build_graph(records: list[dict]) -> dict[str, list[str]]:
    graph: dict[str, list[str]] = {}
    for rec in records:
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


def analyze(db_path: Path) -> dict:
    db = sqlite3.connect(db_path)
    try:
        fmt = db.execute("SELECT value FROM metadata WHERE key='format'").fetchone()
        index_format = fmt[0] if fmt else "unknown"
        records = load_calls(db)
    finally:
        db.close()

    prev = shortest_tree(build_graph(records), WORKER)
    calls: list[dict] = []
    unique_targets: set[tuple[str, str]] = set()
    for rec in records:
        if rec.get("indirect"):
            continue
        target_name = str(rec.get("to_name") or rec.get("callee_name") or rec.get("callee") or "")
        if not NATIVE_NAME_RE.match(target_name):
            continue
        caller = str(rec.get("from_function") or rec.get("caller_address") or rec.get("caller") or "").lower()
        target = str(rec.get("to") or rec.get("callee_address") or rec.get("callee") or "").lower()
        callsite = str(rec.get("instruction") or rec.get("callsite") or rec.get("address") or "").lower()
        reachable = bool(caller) and caller in prev
        folded = target_name.casefold()
        calls.append(
            {
                "caller": caller or None,
                "callsite": callsite or None,
                "target_address": target or None,
                "target_name": target_name,
                "direct_worker_reachable_caller": reachable,
                "shortest_direct_path_to_caller": reconstruct(prev, caller) if reachable else [],
                "apc_capable_name_match": folded in APC_NATIVE_NAMES,
            }
        )
        unique_targets.add((target, target_name))

    calls.sort(key=lambda row: (row["callsite"] or "", row["caller"] or ""))
    reachable = [row for row in calls if row["direct_worker_reachable_caller"]]
    apc_named = [row for row in calls if row["apc_capable_name_match"]]
    reachable_apc_named = [row for row in reachable if row["apc_capable_name_match"]]

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "scope": "Controller #1 direct named native API call surface",
        "authority": {
            "source_index_format": index_format,
            "source_index_sha256": digest(db_path),
            "index_is_navigation_evidence_only": True,
        },
        "worker": WORKER,
        "native_name_prefixes": ["Nt", "Zw", "Rtl"],
        "apc_native_names": sorted(APC_NATIVE_NAMES),
        "counts": {
            "direct_named_native_call_count": len(calls),
            "unique_named_native_target_count": len(unique_targets),
            "direct_worker_reachable_named_native_call_count": len(reachable),
            "apc_capable_name_match_count": len(apc_named),
            "direct_worker_reachable_apc_capable_name_match_count": len(reachable_apc_named),
        },
        "calls": calls,
        "adjudication": {
            "direct_named_native_call_surface_bounded": True,
            "direct_named_native_surface_contains_apc_target_name": bool(apc_named),
            "direct_worker_reachable_named_native_surface_contains_apc_target_name": bool(reachable_apc_named),
            "direct_named_native_surface_adds_no_controller1_apc_candidate": not reachable_apc_named,
            "direct_syscall_surface_ruled_out": False,
            "indirect_ntdll_pointer_surface_ruled_out": False,
            "manual_or_hashed_resolution_ruled_out": False,
            "controller1_thread_handle_join_complete": False,
            "controller1_timing_exhaustive": False,
            "p1_3d_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "Named direct-call targets depend on recovered symbols and do not cover unnamed/direct syscall stubs.",
            "No direct-callgraph result can exhaust indirect calls, callbacks, generated code, wow64 transitions, or pre-resolved function pointers.",
            "Rtl-prefixed runtime helpers are not APC evidence unless exact invocation semantics prove otherwise.",
            "Controller #1 timing cannot advance without exact API/service identity plus target-thread identity."
        ],
        "next_step": (
            "Continue with #1699 native/manual primitive adjudication and direct-syscall/indirect-ntdll paths. "
            "The named direct Nt/Zw/Rtl surface adds no Controller #1 APC candidate."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = analyze(args.database)
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
