#!/usr/bin/env python3
"""Pin the concrete Controller #1 plain-name APC result from a SHIFT Ghidra SQLite index.

The index is navigation evidence, not a universal no-APC theorem. This analyzer
accepts both v1 and v2 index layouts by reading call/string raw_json records.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

FORMAT = "SHIFT.P1D.Controller1ApcSqliteResult/1"
SUPPORTED_INDEX_FORMATS = {"SHIFT.GhidraSQLiteIndex/1", "SHIFT.GhidraSQLiteIndex/2"}
TARGET_NAMES = (
    "QueueUserAPC",
    "NtQueueApcThread",
    "NtQueueApcThreadEx",
    "ZwQueueApcThread",
    "RtlQueueApcWow64Thread",
    "SetWaitableTimerEx",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def analyze(db_path: Path) -> dict:
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    try:
        metadata = dict(db.execute("SELECT key,value FROM metadata").fetchall())
        index_format = metadata.get("format")
        if index_format not in SUPPORTED_INDEX_FORMATS:
            raise ValueError(f"unsupported Ghidra SQLite index format: {index_format!r}")

        resolver_calls = []
        for row in db.execute("SELECT raw_json FROM calls"):
            rec = json.loads(row["raw_json"])
            if rec.get("to_name") == "GetProcAddress":
                resolver_calls.append(rec)

        unique_callers = sorted({rec.get("from_function", "") for rec in resolver_calls if rec.get("from_function")})
        embedded = {}
        for name in TARGET_NAMES:
            rows = db.execute(
                "SELECT value,address,containing_function FROM strings WHERE value = ? ORDER BY address",
                (name,),
            ).fetchall()
            if rows:
                embedded[name] = [dict(row) for row in rows]

        suspicious = []
        for caller in unique_callers:
            for row in db.execute(
                "SELECT value,address FROM strings WHERE containing_function = ? ORDER BY address",
                (caller,),
            ):
                value = row["value"] or ""
                lower = value.lower()
                if any(token in lower for token in ("apc", "queue", "thread", "timer")):
                    suspicious.append({"caller": caller, "address": row["address"], "value": value})

        counts = {
            "functions": db.execute("SELECT COUNT(*) FROM functions").fetchone()[0],
            "calls": db.execute("SELECT COUNT(*) FROM calls").fetchone()[0],
            "strings": db.execute("SELECT COUNT(*) FROM strings").fetchone()[0],
        }
    finally:
        db.close()

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "authority": {
            "source_index_format": index_format,
            "source_index_sha256": sha256(db_path),
            "source_dir": metadata.get("source_dir"),
            "index_is_navigation_evidence_only": True,
        },
        "index_counts": counts,
        "getprocaddress": {
            "direct_call_count": len(resolver_calls),
            "unique_caller_count": len(unique_callers),
            "unique_callers": unique_callers,
        },
        "target_api_names": list(TARGET_NAMES),
        "exact_embedded_target_name_rows": embedded,
        "resolver_caller_suspicious_strings": suspicious,
        "adjudication": {
            "getprocaddress_surface_present": bool(resolver_calls),
            "plain_target_api_names_present_in_index": bool(embedded),
            "plain_name_apc_resolution_supported_by_sqlite_index": bool(resolver_calls and embedded),
            "hashed_or_generated_resolution_ruled_out": False,
            "manual_export_walk_ruled_out": False,
            "native_or_syscall_injection_ruled_out": False,
            "controller1_timing_exhaustive": False,
            "p1_3d_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "Absence of exact API-name strings cannot rule out hashed/generated names.",
            "The Ghidra SQLite index does not contain full instruction data and cannot rule out manual export walking or direct syscall transitions.",
            "GetProcAddress call presence does not prove Controller #1 thread reachability.",
            "Scalar/string-name equality is not semantic identity."
        ],
        "next_step": "Adjudicate the native/manual primitive inventory from P1D PR #1699 and join any positive candidate to Controller #1 worker/thread identity before changing timing gates."
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
