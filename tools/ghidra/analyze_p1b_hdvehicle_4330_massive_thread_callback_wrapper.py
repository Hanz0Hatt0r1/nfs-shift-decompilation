#!/usr/bin/env python3
"""Bound the internal Massive thread callback wrapper for P1B exact 0x4330 carriers."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330MassiveThreadCallbackWrapper/1"
SQLITE_SHA256 = "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
SUPPORTED = {"SHIFT.GhidraSQLiteIndex/1", "SHIFT.GhidraSQLiteIndex/2"}
WRAPPER = "0x0061cdf0"
EXPECTED_CALLERS = {
    ("0x0060b54e", "0x0060b6e5"),
    ("0x0061a780", "0x0061a7ce"),
}
CALLBACKS = {
    "FUN_0060b457": 0x0060B457,
    "FUN_0061d300": 0x0061D300,
}
THREAD_START = 0x0061CD93
P1B_EXACT_CARRIERS = {
    0x00769520, 0x0076B130, 0x0076DF50, 0x00768A4D, 0x00756050,
    0x00772200, 0x00772570, 0x007C3B00, 0x0076B280, 0x007618F0,
    0x00769640, 0x007567A0, 0x00756BB0, 0x00771DB0, 0x00771E10,
}
REQUIRED_SOURCE_FRAGMENTS = [
    'FUN_0061cdf0(DAT_00be861c,FUN_0060b457,0,"Massive Shutdown")',
    'FUN_0061cdf0(DAT_00be8830,FUN_0061d300,param_1,"Massive DNS")',
    '*lpParameter = param_1;\n      lpParameter[1] = param_2;',
    'CreateThread((LPSECURITY_ATTRIBUTES)0x0,0,lpStartAddress_0061cd93,lpParameter,4,',
    'uVar1 = (*(code *)*param_1)(param_1[1]);',
]


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
        if fmt not in SUPPORTED:
            raise ValueError(f"unsupported SQLite format: {fmt!r}")
        callers = set()
        for (raw_text,) in db.execute("SELECT raw_json FROM calls"):
            rec = json.loads(raw_text)
            if rec.get("indirect") is True:
                continue
            if str(rec.get("to") or "").lower() != WRAPPER:
                continue
            callers.add((str(rec.get("from_function")).lower(), str(rec.get("instruction")).lower()))
    finally:
        db.close()
    if callers != EXPECTED_CALLERS:
        raise ValueError(f"FUN_0061cdf0 caller surface drift: {sorted(callers)!r}")

    text = source.read_text(encoding="utf-8", errors="strict")
    missing = [fragment for fragment in REQUIRED_SOURCE_FRAGMENTS if fragment not in text]
    if missing:
        raise ValueError(f"Massive callback source fragment drift: {missing!r}")

    callback_hits = sorted(addr for addr in CALLBACKS.values() if addr in P1B_EXACT_CARRIERS)
    thread_start_hit = THREAD_START in P1B_EXACT_CARRIERS
    if callback_hits or thread_start_hit:
        raise ValueError("P1B exact carrier entered through Massive thread wrapper")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "authority": {
            "platform": "PC retail 1.02",
            "ghidra_sqlite_sha256": db_hash,
            "shift_exe_c_sha256": src_hash,
            "sqlite_and_source_are_navigation_crosscheck": True,
        },
        "surface": {
            "wrapper": WRAPPER,
            "direct_caller_count": len(callers),
            "direct_callers": [
                {"caller": caller, "callsite": callsite}
                for caller, callsite in sorted(callers)
            ],
            "resolved_callback_count": len(CALLBACKS),
            "resolved_callbacks": [
                {"name": name, "address": f"0x{addr:08x}"}
                for name, addr in sorted(CALLBACKS.items(), key=lambda item: item[1])
            ],
            "fixed_thread_start": f"0x{THREAD_START:08x}",
            "callback_storage": "heap record [0]=callback, [1]=callback argument",
            "thread_dispatch": "lpStartAddress_0061cd93 invokes (*(code*)record[0])(record[1])",
            "exact_4330_carrier_callback_count": 0,
            "exact_4330_carrier_thread_start": False,
        },
        "adjudication": {
            "massive_thread_callback_wrapper_surface_complete": True,
            "massive_thread_callback_values_complete": True,
            "exact_4330_carrier_reachable_via_massive_thread_wrapper": False,
            "runtime_callback_registration_ruled_out": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "global_runtime_derived_4330_alias_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only the two direct FUN_0061cdf0 registrations visible in the pinned SQLite/source pair.",
            "It does not close other application-owned callback wrappers, arbitrary function-pointer storage, computed/encoded code pointers or indirect dispatch.",
            "Decompiler source is used only to pin the wrapper dataflow and concrete callback values; no object identity is inferred from types.",
        ],
        "next_step": "Continue application-owned callback wrappers and generic function-pointer stores/copies before promoting the global runtime-callback or indirect-entry gates.",
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
