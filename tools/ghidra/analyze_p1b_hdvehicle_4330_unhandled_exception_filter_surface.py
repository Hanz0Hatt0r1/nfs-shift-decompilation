#!/usr/bin/env python3
"""Bound SetUnhandledExceptionFilter registration for P1B exact HDVehicle+0x4330 carriers."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330UnhandledExceptionFilterSurface/1"
SQLITE_SHA256 = "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
SUPPORTED_SQLITE = {"SHIFT.GhidraSQLiteIndex/1", "SHIFT.GhidraSQLiteIndex/2"}
EXPECTED_CALLS = {
    ("0x0090a532", "__invoke_watson", "0x0090a5e6"),
    ("0x0090a6d1", "_abort", "0x0090a7ac"),
    ("0x00916e88", "___report_gsfailure", "0x00916f56"),
}
NULL_SOURCE_CALL = "SetUnhandledExceptionFilter((LPTOP_LEVEL_EXCEPTION_FILTER)0x0);"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def analyze(database: Path, source: Path) -> dict:
    db_hash = sha256(database)
    src_hash = sha256(source)
    if db_hash != SQLITE_SHA256:
        raise ValueError(f"unexpected SQLite SHA-256: {db_hash}")
    if src_hash != SOURCE_SHA256:
        raise ValueError(f"unexpected source SHA-256: {src_hash}")

    db = sqlite3.connect(database)
    try:
        row = db.execute("SELECT value FROM metadata WHERE key='format'").fetchone()
        fmt = None if row is None else row[0]
        if fmt not in SUPPORTED_SQLITE:
            raise ValueError(f"unsupported SQLite format: {fmt!r}")
        calls = set()
        for (raw_text,) in db.execute("SELECT raw_json FROM calls"):
            rec = json.loads(raw_text)
            if rec.get("to_name") != "SetUnhandledExceptionFilter":
                continue
            if rec.get("indirect") is not False:
                raise ValueError("SetUnhandledExceptionFilter gained indirect call row")
            calls.add((
                str(rec.get("from_function") or "").lower(),
                str(rec.get("from_name") or ""),
                str(rec.get("instruction") or "").lower(),
            ))
    finally:
        db.close()
    if calls != EXPECTED_CALLS:
        raise ValueError(f"SetUnhandledExceptionFilter call surface drift: {sorted(calls)!r}")

    text = source.read_text(encoding="utf-8", errors="strict")
    total_name_occurrences = text.count("SetUnhandledExceptionFilter(")
    null_call_occurrences = text.count(NULL_SOURCE_CALL)
    if total_name_occurrences != 3 or null_call_occurrences != 3:
        raise ValueError(
            f"SetUnhandledExceptionFilter source drift: total={total_name_occurrences} null={null_call_occurrences}"
        )

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "authority": {
            "platform": "PC retail 1.02",
            "ghidra_sqlite_sha256": db_hash,
            "shift_exe_c_sha256": src_hash,
            "sqlite_machine_calls_are_physical_callsite_authority": True,
        },
        "surface": {
            "direct_callsite_count": 3,
            "nonnull_filter_registration_count": 0,
            "null_filter_registration_count": 3,
            "callsites": [
                {"caller": caller, "caller_name": name, "callsite": site, "registered_filter": "NULL"}
                for caller, name, site in sorted(calls, key=lambda x: x[2])
            ],
            "exact_4330_carrier_filter_count": 0,
        },
        "adjudication": {
            "set_unhandled_exception_filter_surface_complete": True,
            "exact_4330_carrier_reachable_via_unhandled_exception_filter": False,
            "runtime_callback_registration_ruled_out": False,
            "generic_function_pointer_stores_copies_ruled_out": False,
            "computed_or_encoded_code_pointers_ruled_out": False,
            "remaining_callback_api_families_ruled_out": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "global_runtime_derived_4330_alias_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only direct SetUnhandledExceptionFilter calls in the pinned retail SQLite/source pair.",
            "All three registrations explicitly pass NULL, so this API family cannot enter a P1B exact HDVehicle+0x4330 carrier in the pinned image.",
            "Vectored exception handlers, signal handlers, arbitrary function-pointer stores and other runtime callback mechanisms remain outside this subset."
        ],
        "next_step": "Continue other finite exception/signal callback mechanisms and generic runtime function-pointer stores/copies before promoting global indirect-entry gates."
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("database", type=Path)
    p.add_argument("source", type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    try:
        result = analyze(args.database, args.source)
    except ValueError as exc:
        p.error(str(exc))
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
