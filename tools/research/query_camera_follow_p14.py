#!/usr/bin/env python3
"""Query the Ghidra SQLite index for the P1.4 camera-follow proof frontier.

This is a navigation/evidence-collection helper only. It deliberately does not
promote camera-follow semantics from callgraph adjacency. PC retail machine code
remains the semantic authority.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.CameraFollowP14CallerInventory/1"
TARGETS = {
    "mode2_activation": "FUN_0080e0d0",
    "camera_selector": "FUN_0080e1b0",
    "controller_apply": "FUN_0080d300",
}


def rows(db: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    db.row_factory = sqlite3.Row
    return [dict(row) for row in db.execute(sql, params)]


def function_record(db: sqlite3.Connection, name: str) -> dict[str, Any] | None:
    matches = rows(
        db,
        "SELECT address,name,end_address,signature,mnemonic_fingerprint,raw_json "
        "FROM functions WHERE name=? ORDER BY address",
        (name,),
    )
    return matches[0] if matches else None


def _call_columns(db: sqlite3.Connection) -> set[str]:
    return {str(row[1]) for row in db.execute("PRAGMA table_info(calls)")}


def _normalise_call(row: dict[str, Any]) -> dict[str, Any]:
    try:
        raw = json.loads(row.get("raw_json") or "{}")
    except json.JSONDecodeError:
        raw = {}

    caller_address = str(
        row.get("caller_address")
        or raw.get("from_function")
        or raw.get("caller_address")
        or ""
    )
    callee_address = str(
        row.get("callee_address")
        or raw.get("to")
        or raw.get("callee_address")
        or ""
    )
    caller_name = str(
        raw.get("from_name")
        or row.get("caller_name")
        or (row.get("caller") if not str(row.get("caller") or "").startswith("0x") else "")
        or caller_address
    )
    callee_name = str(
        raw.get("to_name")
        or row.get("callee_name")
        or (row.get("callee") if not str(row.get("callee") or "").startswith("0x") else "")
        or callee_address
    )
    indirect = bool(row.get("indirect", raw.get("indirect", False)))
    return {
        "caller": caller_name,
        "callee": callee_name,
        "caller_address": caller_address,
        "callee_address": callee_address,
        "callsite": str(row.get("callsite") or raw.get("instruction") or raw.get("address") or ""),
        "kind": str(row.get("kind") or ("indirect" if indirect else "direct")),
        "indirect": indirect,
        "raw_json": row.get("raw_json") or "{}",
    }


def all_calls(db: sqlite3.Connection) -> list[dict[str, Any]]:
    columns = _call_columns(db)
    selected = [name for name in (
        "caller", "callee", "caller_address", "callee_address",
        "callsite", "kind", "indirect", "raw_json"
    ) if name in columns]
    if "raw_json" not in selected:
        raise SystemExit("calls table has no raw_json column")
    return [_normalise_call(row) for row in rows(db, "SELECT " + ",".join(selected) + " FROM calls")]


def callers(call_rows: list[dict[str, Any]], function: dict[str, Any] | None, name: str) -> list[dict[str, Any]]:
    address = str((function or {}).get("address") or "")
    result = [
        row for row in call_rows
        if row.get("callee") == name or (address and row.get("callee_address") == address)
    ]
    return sorted(result, key=lambda row: (str(row.get("caller_address")), str(row.get("callsite"))))


def callees(call_rows: list[dict[str, Any]], function: dict[str, Any] | None, name: str) -> list[dict[str, Any]]:
    address = str((function or {}).get("address") or "")
    result = [
        row for row in call_rows
        if row.get("caller") == name or (address and row.get("caller_address") == address)
    ]
    return sorted(result, key=lambda row: (str(row.get("callsite")), str(row.get("callee_address"))))


def metadata(db: sqlite3.Connection) -> dict[str, str]:
    try:
        return {str(row[0]): str(row[1]) for row in db.execute("SELECT key,value FROM metadata")}
    except sqlite3.OperationalError:
        return {}


def build(db_path: Path) -> dict[str, Any]:
    db = sqlite3.connect(db_path)
    try:
        meta = metadata(db)
        call_rows = all_calls(db)
        target_rows: dict[str, dict[str, Any]] = {}
        for key, name in TARGETS.items():
            function = function_record(db, name)
            target_rows[key] = {
                "name": name,
                "function": function,
                "callers": callers(call_rows, function, name),
                "callees": callees(call_rows, function, name),
            }
    finally:
        db.close()

    direct_mode2_callers = target_rows["mode2_activation"]["callers"]
    selector_calls_mode2 = [
        row
        for row in target_rows["camera_selector"]["callees"]
        if row.get("callee") == TARGETS["mode2_activation"]
        or row.get("callee_address")
        == (target_rows["mode2_activation"]["function"] or {}).get("address")
    ]

    blockers: list[str] = []
    if not direct_mode2_callers:
        blockers.append("p14:mode2-direct-callers-not-present-in-index")
    if not selector_calls_mode2:
        blockers.append("p14:selector-to-mode2-edge-not-present-in-index")

    return {
        "format": FORMAT,
        "version": 1,
        "authority": {
            "semantic_authority": "PC retail machine code",
            "sqlite_index_is_semantic_proof": False,
            "numeric_offset_equality_is_identity": False,
        },
        "index": {
            "path": str(db_path),
            "metadata": meta,
        },
        "targets": target_rows,
        "bounded_findings": {
            "mode2_direct_caller_count": len(direct_mode2_callers),
            "selector_to_mode2_edge_count": len(selector_calls_mode2),
            "selector_to_mode2_edges": selector_calls_mode2,
        },
        "proof_requests": [
            {
                "id": "mode2_runtime_argument_identity",
                "status": "requires-machine-body-trace",
                "next": (
                    "For every listed FUN_0080e0d0 callsite, inspect the PC-retail caller body, "
                    "recover the exact runtime_argument definition reaching source.vtable+0x90, "
                    "and prove or reject identity/ownership with the selected retail player vehicle."
                ),
            },
            {"id": "mode2_source_vtable_identity", "status": "not-promoted"},
            {"id": "mode2_vehicle_pose_dependency", "status": "not-promoted"},
            {"id": "camera_follow_update_order", "status": "not-promoted"},
        ],
        "ready": False,
        "blocking_reasons": blockers
        + [
            "p14:runtime-argument-machine-value-flow-unproven",
            "p14:mode2-source-vtable-unproven",
            "p14:vehicle-pose-dependency-unproven",
            "p14:update-order-unproven",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sqlite_index", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    result = build(args.sqlite_index)
    encoded = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False)
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
