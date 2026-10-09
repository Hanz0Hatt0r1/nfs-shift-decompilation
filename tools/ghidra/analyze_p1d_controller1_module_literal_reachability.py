#!/usr/bin/env python3
"""Bound direct Controller #1 reachability of literal KERNEL32/NTDLL module-name owners.

This is a narrow manual-resolution sub-surface. It does not rule out PEB walks,
hashed/generated module names, indirect calls, or native/syscall APC injection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import deque
from pathlib import Path

FORMAT = "SHIFT.P1D.Controller1ModuleLiteralReachability/1"
WORKER = "0x00662880"
MODULE_NAMES = {"kernel32", "kernel32.dll", "ntdll", "ntdll.dll"}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def call_records(db: sqlite3.Connection) -> list[dict]:
    out: list[dict] = []
    for row in db.execute("SELECT raw_json FROM calls"):
        rec = json.loads(row[0])
        out.append(rec)
    return out


def build_graph(records: list[dict]) -> dict[str, list[tuple[str, str]]]:
    graph: dict[str, list[tuple[str, str]]] = {}
    for rec in records:
        if rec.get("indirect"):
            continue
        src = rec.get("from_function") or rec.get("caller_address") or rec.get("caller")
        dst = rec.get("to") or rec.get("callee_address") or rec.get("callee")
        site = rec.get("instruction") or rec.get("callsite") or rec.get("address") or ""
        if not src or not dst:
            continue
        graph.setdefault(str(src).lower(), []).append((str(dst).lower(), str(site).lower()))
    return graph


def shortest_paths(graph: dict[str, list[tuple[str, str]]], start: str) -> tuple[dict[str, str | None], dict[str, str]]:
    start = start.lower()
    prev: dict[str, str | None] = {start: None}
    edge: dict[str, str] = {}
    queue = deque([start])
    while queue:
        src = queue.popleft()
        for dst, site in graph.get(src, []):
            if dst in prev:
                continue
            prev[dst] = src
            edge[dst] = site
            queue.append(dst)
    return prev, edge


def path_for(prev: dict[str, str | None], target: str) -> list[str]:
    target = target.lower()
    if target not in prev:
        return []
    path = [target]
    while prev[path[-1]] is not None:
        path.append(prev[path[-1]])
    path.reverse()
    return path


def analyze(db_path: Path) -> dict:
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    try:
        fmt_row = db.execute("SELECT value FROM metadata WHERE key='format'").fetchone()
        index_format = fmt_row[0] if fmt_row else "unknown"
        records = call_records(db)
        graph = build_graph(records)
        prev, _edge = shortest_paths(graph, WORKER)

        resolver_callers: set[str] = set()
        for rec in records:
            to_name = str(rec.get("to_name") or rec.get("callee_name") or rec.get("callee") or "")
            if to_name.lower() == "getprocaddress":
                src = rec.get("from_function") or rec.get("caller_address") or rec.get("caller")
                if src:
                    resolver_callers.add(str(src).lower())

        literal_rows: list[dict] = []
        owners: dict[str, set[tuple[str, str]]] = {}
        for row in db.execute("SELECT value,address,containing_function FROM strings ORDER BY address,containing_function"):
            value = str(row["value"] or "")
            folded = value.casefold()
            if folded not in MODULE_NAMES:
                continue
            owner = str(row["containing_function"] or "").lower()
            literal_rows.append({
                "value": value,
                "address": row["address"],
                "containing_function": owner or None,
            })
            if owner:
                owners.setdefault(owner, set()).add((str(row["address"]), value))

        owner_rows: list[dict] = []
        for owner in sorted(owners):
            reachable = owner in prev
            strings = [
                {"address": address, "value": value}
                for address, value in sorted(owners[owner])
            ]
            local_strings = [
                {"address": r["address"], "value": r["value"]}
                for r in db.execute(
                    "SELECT address,value FROM strings WHERE containing_function=? ORDER BY address",
                    (owner,),
                )
            ]
            owner_rows.append({
                "function": owner,
                "direct_worker_reachable": reachable,
                "shortest_direct_path": path_for(prev, owner),
                "is_getprocaddress_caller": owner in resolver_callers,
                "module_literals": strings,
                "local_strings": local_strings,
            })

        reachable = [row for row in owner_rows if row["direct_worker_reachable"]]
        reachable_outside = [row for row in reachable if not row["is_getprocaddress_caller"]]
        ntdll_rows = [row for row in literal_rows if str(row["value"]).casefold().startswith("ntdll")]

        return {
            "format": FORMAT,
            "version": 1,
            "ready": True,
            "owner": "Process 1D / P1.3D",
            "authority": {
                "source_index_format": index_format,
                "source_index_sha256": digest(db_path),
                "index_is_navigation_evidence_only": True,
            },
            "worker": WORKER,
            "surface": {
                "module_literals": sorted(MODULE_NAMES),
                "literal_row_count": len(literal_rows),
                "unique_literal_owner_count": len(owner_rows),
                "ntdll_literal_row_count": len(ntdll_rows),
                "direct_worker_reachable_literal_owner_count": len(reachable),
                "direct_worker_reachable_literal_owners_outside_getprocaddress_surface": len(reachable_outside),
                "owners": owner_rows,
            },
            "adjudication": {
                "direct_literal_module_name_surface_bounded": True,
                "reachable_literal_module_owner_adds_new_direct_manual_resolution_candidate": bool(reachable_outside),
                "direct_literal_module_surface_adds_no_new_candidate": not reachable_outside,
                "peb_walk_without_literal_module_name_ruled_out": False,
                "hashed_or_generated_module_name_ruled_out": False,
                "indirect_callgraph_surface_ruled_out": False,
                "native_or_syscall_injection_ruled_out": False,
                "controller1_timing_exhaustive": False,
                "p1_3d_complete": False,
                "external_provider_count": 7,
            },
            "limits": [
                "Literal module-name ownership is context only; it is not export-table traversal proof.",
                "Direct-call reachability cannot exhaust indirect calls, callbacks, or virtual dispatch.",
                "Absence of NTDLL literals does not rule out PEB walking, hashed/generated names, or pre-resolved pointers.",
                "No timing gate changes without exact API/service identity and Controller #1 target-thread identity.",
            ],
            "next_step": (
                "Adjudicate the native/manual primitive inventory for PEB/export traversal or direct native transitions; "
                "the direct literal KERNEL32/NTDLL module-name surface adds no new worker-reachable candidate beyond "
                "the already bounded GetProcAddress subset."
            ),
        }
    finally:
        db.close()


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
