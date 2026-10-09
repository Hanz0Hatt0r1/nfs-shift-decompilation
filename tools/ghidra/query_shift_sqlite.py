#!/usr/bin/env python3
"""Query the local SHIFT Ghidra SQLite acceleration index.

This tool is navigation-only. Returned rows are not semantic proof.
Version-1 indexes remain readable through a raw_json compatibility path; v2 is
the preferred schema for new builds.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

FORMAT = "SHIFT.GhidraSQLiteQuery/1"
SUPPORTED_INDEXES = {"SHIFT.GhidraSQLiteIndex/1", "SHIFT.GhidraSQLiteIndex/2"}
PREFERRED_INDEX = "SHIFT.GhidraSQLiteIndex/2"


def connect(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise SystemExit(f"SQLite index not found: {path}")
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    fmt = db.execute("SELECT value FROM metadata WHERE key='format'").fetchone()
    if fmt is None:
        db.close()
        raise SystemExit("SQLite index has no metadata format")
    if fmt[0] not in SUPPORTED_INDEXES:
        db.close()
        raise SystemExit(
            f"unsupported SQLite index format: {fmt[0]!r}; rebuild with build_shift_sqlite_index.py"
        )
    return db


def index_format(db: sqlite3.Connection) -> str:
    row = db.execute("SELECT value FROM metadata WHERE key='format'").fetchone()
    if row is None:
        raise ValueError("SQLite index has no metadata format")
    return str(row[0])


def rows(db: sqlite3.Connection, sql: str, params: tuple, limit: int) -> list[dict]:
    return [dict(row) for row in db.execute(sql + " LIMIT ?", (*params, limit)).fetchall()]


def function_query(db: sqlite3.Connection, value: str, limit: int) -> list[dict]:
    return rows(
        db,
        """
        SELECT address,name,end_address,signature,mnemonic_fingerprint
        FROM functions
        WHERE name = ? OR address = ?
        ORDER BY address
        """,
        (value, value),
        limit,
    )


def _normalize_v1_call(row: sqlite3.Row) -> dict:
    rec = json.loads(row["raw_json"])
    caller_address = str(rec.get("from_function") or row["caller"] or "")
    callee_address = str(rec.get("to") or row["callee"] or "")
    caller = str(rec.get("from_name") or rec.get("caller") or caller_address)
    callee = str(rec.get("to_name") or rec.get("callee") or callee_address)
    return {
        "callsite": str(rec.get("instruction") or rec.get("callsite") or row["callsite"] or ""),
        "caller": caller,
        "caller_address": caller_address,
        "callee": callee,
        "callee_address": callee_address,
        "kind": str(rec.get("kind") or row["kind"] or ("indirect" if rec.get("indirect") else "direct")),
        "indirect": 1 if rec.get("indirect") else 0,
    }


def _v1_calls(db: sqlite3.Connection, *, caller: str | None = None, callee: str | None = None, callsite: str | None = None, limit: int) -> list[dict]:
    result: list[dict] = []
    for row in db.execute("SELECT caller,callee,callsite,kind,raw_json FROM calls ORDER BY callsite"):
        normalized = _normalize_v1_call(row)
        if caller is not None and caller not in {normalized["caller"], normalized["caller_address"]}:
            continue
        if callee is not None and callee not in {normalized["callee"], normalized["callee_address"]}:
            continue
        if callsite is not None and callsite != normalized["callsite"]:
            continue
        result.append(normalized)
        if len(result) >= limit:
            break
    return result


def callers_query(db: sqlite3.Connection, value: str, limit: int) -> list[dict]:
    if index_format(db) == "SHIFT.GhidraSQLiteIndex/1":
        return _v1_calls(db, callee=value, limit=limit)
    return rows(
        db,
        """
        SELECT callsite,caller,caller_address,callee,callee_address,kind,indirect
        FROM calls
        WHERE callee = ? OR callee_address = ?
        ORDER BY callsite,caller_address
        """,
        (value, value),
        limit,
    )


def callees_query(db: sqlite3.Connection, value: str, limit: int) -> list[dict]:
    if index_format(db) == "SHIFT.GhidraSQLiteIndex/1":
        return _v1_calls(db, caller=value, limit=limit)
    return rows(
        db,
        """
        SELECT callsite,caller,caller_address,callee,callee_address,kind,indirect
        FROM calls
        WHERE caller = ? OR caller_address = ?
        ORDER BY callsite,callee_address
        """,
        (value, value),
        limit,
    )


def callsite_query(db: sqlite3.Connection, value: str, limit: int) -> list[dict]:
    if index_format(db) == "SHIFT.GhidraSQLiteIndex/1":
        return _v1_calls(db, callsite=value, limit=limit)
    return rows(
        db,
        """
        SELECT callsite,caller,caller_address,callee,callee_address,kind,indirect
        FROM calls
        WHERE callsite = ?
        ORDER BY caller_address,callee_address
        """,
        (value,),
        limit,
    )


def strings_query(db: sqlite3.Connection, value: str, limit: int) -> list[dict]:
    pattern = f"%{value}%"
    return rows(
        db,
        """
        SELECT value,address,containing_function
        FROM strings
        WHERE value LIKE ?
        ORDER BY value,address,containing_function
        """,
        (pattern,),
        limit,
    )


def globals_query(db: sqlite3.Connection, value: str, limit: int) -> list[dict]:
    pattern = f"%{value}%"
    return rows(
        db,
        """
        SELECT address,name,data_type,xref_count
        FROM globals
        WHERE address = ? OR name = ? OR name LIKE ?
        ORDER BY address,name
        """,
        (value, value, pattern),
        limit,
    )


QUERIES = {
    "function": function_query,
    "callers": callers_query,
    "callees": callees_query,
    "callsite": callsite_query,
    "strings": strings_query,
    "globals": globals_query,
}


def query(db_path: Path, command: str, value: str, limit: int = 100) -> dict:
    if command not in QUERIES:
        raise ValueError(f"unknown query command: {command}")
    if limit < 1:
        raise ValueError("limit must be >= 1")
    db = connect(db_path)
    try:
        fmt = index_format(db)
        result = QUERIES[command](db, value, limit)
    finally:
        db.close()
    return {
        "format": FORMAT,
        "index_format": fmt,
        "preferred_index_format": PREFERRED_INDEX,
        "command": command,
        "query": value,
        "limit": limit,
        "count": len(result),
        "rows": result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in QUERIES:
        cmd = sub.add_parser(name)
        cmd.add_argument("value")
        cmd.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    try:
        payload = query(args.database, args.command, args.value, args.limit)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
