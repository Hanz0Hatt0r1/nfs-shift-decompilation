#!/usr/bin/env python3
"""Capture the Drive Ghidra index capability for incoming indirect carrier entry.

This is navigation evidence, not an absence proof. The current v1 Drive index
records 19,500 indirect edges but leaves every indirect target unresolved. The
analyzer therefore refuses to promote incoming-indirect-entry closure merely
because no resolved edge names one of the 16 exact carriers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

FORMAT = "SHIFT.P1A.P13AExactCarrierIncomingIndirectIndexFrontier/1"
INDEX_SHA256 = "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
SUPPORTED_FORMATS = {"SHIFT.GhidraSQLiteIndex/1", "SHIFT.GhidraSQLiteIndex/2"}

CARRIERS = [
    ("FUN_00758b50", "0x00758b50"),
    ("FUN_00755950", "0x00755950"),
    ("FUN_00770e80", "0x00770e80"),
    ("FUN_00755a60", "0x00755a60"),
    ("FUN_00752fc0", "0x00752fc0"),
    ("FUN_00760b50", "0x00760b50"),
    ("FUN_00763570", "0x00763570"),
    ("FUN_00755f80", "0x00755f80"),
    ("FUN_0076d100", "0x0076d100"),
    ("FUN_00758810", "0x00758810"),
    ("FUN_00769ef0", "0x00769ef0"),
    ("FUN_007675f0", "0x007675f0"),
    ("FUN_007682c0", "0x007682c0"),
    ("FUN_00766510", "0x00766510"),
    ("FUN_00758fc0", "0x00758fc0"),
    ("FUN_00765c40", "0x00765c40"),
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_record(row: sqlite3.Row) -> dict:
    raw = json.loads(row["raw_json"])
    return {
        "caller": str(raw.get("from_function") or raw.get("from_name") or row["caller"] or ""),
        "callsite": str(raw.get("instruction") or raw.get("callsite") or row["callsite"] or ""),
        "indirect": bool(raw.get("indirect")),
        "target_address": str(raw.get("to") or raw.get("callee_address") or ""),
        "target_name": str(raw.get("to_name") or raw.get("callee") or row["callee"] or ""),
    }


def summarize_records(records: list[dict]) -> dict:
    carrier_tokens = set()
    for name, address in CARRIERS:
        carrier_tokens.add(name.lower())
        carrier_tokens.add(address.lower())

    indirect = [row for row in records if row.get("indirect")]
    resolved = [
        row for row in indirect
        if str(row.get("target_address") or "").strip()
        or str(row.get("target_name") or "").strip()
    ]
    unresolved = [row for row in indirect if row not in resolved]

    carrier_hits = []
    for row in resolved:
        values = {
            str(row.get("target_address") or "").lower(),
            str(row.get("target_name") or "").lower(),
        }
        if values & carrier_tokens:
            carrier_hits.append(row)

    return {
        "call_record_count": len(records),
        "indirect_edge_count": len(indirect),
        "resolved_indirect_target_count": len(resolved),
        "unresolved_indirect_target_count": len(unresolved),
        "resolved_exact_carrier_incoming_count": len(carrier_hits),
        "resolved_exact_carrier_incoming": carrier_hits,
    }


def analyze(database: Path) -> dict:
    actual_sha = sha256(database)
    if actual_sha != INDEX_SHA256:
        raise ValueError(f"unexpected Ghidra SQLite SHA-256: {actual_sha}")

    db = sqlite3.connect(database)
    db.row_factory = sqlite3.Row
    try:
        row = db.execute("SELECT value FROM metadata WHERE key='format'").fetchone()
        fmt = str(row[0]) if row else ""
        if fmt not in SUPPORTED_FORMATS:
            raise ValueError(f"unsupported Ghidra SQLite format: {fmt!r}")
        columns = {r[1] for r in db.execute("PRAGMA table_info(calls)")}
        required = {"caller", "callee", "callsite", "raw_json"}
        if not required.issubset(columns):
            raise ValueError(f"unsupported calls table columns: {sorted(columns)!r}")
        records = [normalize_record(row) for row in db.execute(
            "SELECT caller,callee,callsite,raw_json FROM calls ORDER BY callsite"
        )]
    finally:
        db.close()

    surface = summarize_records(records)
    resolved_coverage = surface["resolved_indirect_target_count"] > 0
    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1A / P1.3A",
        "authority": {
            "platform": "PC retail 1.02 navigation index",
            "ghidra_sqlite_sha256": actual_sha,
            "ghidra_sqlite_format": fmt,
            "sqlite_is_navigation_index": True,
        },
        "carrier_set": {
            "count": len(CARRIERS),
            "rows": [{"name": name, "address": address} for name, address in CARRIERS],
        },
        "incoming_indirect_surface": surface,
        "adjudication": {
            "p13a_incoming_indirect_index_frontier_captured": True,
            "p13a_incoming_indirect_index_has_resolved_target_coverage": resolved_coverage,
            "p13a_resolved_exact_carrier_incoming_indirect_found": bool(surface["resolved_exact_carrier_incoming_count"]),
            "p13a_resolved_exact_carrier_incoming_indirect_count": surface["resolved_exact_carrier_incoming_count"],
            "p13a_index_can_prove_exact_carrier_incoming_indirect_absence": False,
            "incoming_indirect_entry_ruled_out": False,
            "runtime_callback_registration_ruled_out": False,
            "runtime_generated_or_copied_carrier_pointers_ruled_out": False,
            "runtime_generated_selected_wheel_pointer_stores_ruled_out": False,
            "stored_or_escaped_aliases_ruled_out": False,
            "p13a_slot0_complete": False,
            "p13a_slot1_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "The current Drive index records indirect=true edges as navigation candidates but all indirect targets are unresolved; zero exact-carrier resolved hits is therefore not an absence proof.",
            "This frontier does not classify runtime callback registration, virtual dispatch targets, copied/encoded function pointers, or machine-level indirect entry.",
            "Existing retail machine contracts and whole-image pointer scans remain semantic authority for the bounded surfaces they explicitly cover.",
            "No slot or aggregate P1.3 gate is promoted by this index-capability result."
        ],
        "next_step": (
            "Recover incoming indirect targets from machine/vtable/registration dataflow rather than treating the unresolved SQLite CALLIND set as negative evidence; "
            "join any positive exact-carrier registration to its runtime consumer."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = analyze(args.database)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
