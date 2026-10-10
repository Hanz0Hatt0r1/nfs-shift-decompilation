#!/usr/bin/env python3
"""Bound CreateThread/__beginthreadex runtime thread-start registration for P1B exact 0x4330 carriers.

SQLite call rows and the hash-pinned decompiler source are cross-check/navigation inputs.
This closes only the explicit thread-start registration surface and does not claim
all runtime callbacks or computed pointer registration mechanisms.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330ThreadStartCallbackSurface/1"
SQLITE_SHA256 = "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
SUPPORTED_SQLITE = {"SHIFT.GhidraSQLiteIndex/1", "SHIFT.GhidraSQLiteIndex/2"}

# Canonical P1B exact HDVehicle+0x4330 carrier set. Keep this distinct from the
# P1D slot3 carrier set; the two lanes intentionally track different receivers.
EXACT_CARRIERS = {
    0x00769520, 0x0076B130, 0x0076DF50, 0x00768A4D, 0x00756050,
    0x00772200, 0x00772570, 0x007C3B00, 0x0076B280, 0x007618F0,
    0x00769640, 0x007567A0, 0x00756BB0, 0x00771DB0, 0x00771E10,
}

EXPECTED_CREATE_THREAD = {
    ("0x005d6130", "0x005d6194"),
    ("0x005fdf30", "0x005fe03f"),
    ("0x005ff260", "0x005ff377"),
    ("0x005ff7e0", "0x005ff86a"),
    ("0x0061cdf0", "0x0061ce39"),
    ("0x00907ecf", "0x00907f4e"),
    ("0x0093db2b", "0x0093db4b"),
}
EXPECTED_BEGINTHREADEX = {
    ("0x00649cb0", "0x00649d02"),
    ("0x00649cb0", "0x00649d47"),
    ("0x00a2a4b0", "0x00a2a54a"),
}
EXPECTED_DYNAMIC_WRAPPER_CALLER = {
    ("0x00939797", "0x0093984a"),
}

THREAD_STARTS = {
    "lpStartAddress_005d5f40": 0x005D5F40,
    "lpStartAddress_005fdd70": 0x005FDD70,
    "lpStartAddress_005ff1e0": 0x005FF1E0,
    "lpStartAddress_005ff710": 0x005FF710,
    "lpStartAddress_0061cd93": 0x0061CD93,
    "lpStartAddress_00907e4f": 0x00907E4F,
    "FUN_00649b10": 0x00649B10,
    "FUN_00a2a370": 0x00A2A370,
    "FUN_009396c0": 0x009396C0,
}

REQUIRED_SOURCE_FRAGMENTS = [
    "CreateThread((LPSECURITY_ATTRIBUTES)0x0,0,\n                              (LPTHREAD_START_ROUTINE)&lpStartAddress_005d5f40",
    "CreateThread((LPSECURITY_ATTRIBUTES)0x0,0,\n                        (LPTHREAD_START_ROUTINE)&lpStartAddress_005fdd70",
    "CreateThread((LPSECURITY_ATTRIBUTES)0x0,0,lpStartAddress_005ff1e0,_Dst,0,&param_2)",
    "CreateThread((LPSECURITY_ATTRIBUTES)0x0,0,\n                        (LPTHREAD_START_ROUTINE)&lpStartAddress_005ff710",
    "CreateThread((LPSECURITY_ATTRIBUTES)0x0,0,lpStartAddress_0061cd93,lpParameter,4,",
    "CreateThread(_Security,_StackSize,(LPTHREAD_START_ROUTINE)&lpStartAddress_00907e4f,",
    "CreateThread((LPSECURITY_ATTRIBUTES)0x0,0,param_2,param_3,0,(LPDWORD)&param_7)",
    "__beginthreadex((void *)0x0,0,FUN_00649b10,pvVar3,4,",
    "__beginthreadex((void *)0x0,_StackSize,FUN_00a2a370,*(void **)this,4,",
    "FUN_0093db2b(param_1,FUN_009396c0,this,iVar1,param_5,param_6,",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _call_rows(db: sqlite3.Connection, target_name: str) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for (raw_text,) in db.execute("SELECT raw_json FROM calls"):
        rec = json.loads(raw_text)
        if rec.get("indirect") is True or rec.get("to_name") != target_name:
            continue
        out.add((str(rec.get("from_function")).lower(), str(rec.get("instruction")).lower()))
    return out


def _direct_callers(db: sqlite3.Connection, target: str) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for (raw_text,) in db.execute("SELECT raw_json FROM calls"):
        rec = json.loads(raw_text)
        if rec.get("indirect") is True:
            continue
        if str(rec.get("to") or "").lower() != target.lower():
            continue
        out.add((str(rec.get("from_function")).lower(), str(rec.get("instruction")).lower()))
    return out


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
        create_rows = _call_rows(db, "CreateThread")
        begin_rows = _call_rows(db, "__beginthreadex")
        wrapper_callers = _direct_callers(db, "0x0093db2b")
    finally:
        db.close()

    if create_rows != EXPECTED_CREATE_THREAD:
        raise ValueError(f"CreateThread call surface drift: {sorted(create_rows)!r}")
    if begin_rows != EXPECTED_BEGINTHREADEX:
        raise ValueError(f"__beginthreadex call surface drift: {sorted(begin_rows)!r}")
    if wrapper_callers != EXPECTED_DYNAMIC_WRAPPER_CALLER:
        raise ValueError(f"FUN_0093db2b caller surface drift: {sorted(wrapper_callers)!r}")

    text = source.read_text(encoding="utf-8", errors="strict")
    missing = [fragment for fragment in REQUIRED_SOURCE_FRAGMENTS if fragment not in text]
    if missing:
        raise ValueError(f"thread-start source fragment drift: {missing!r}")

    exact_hits = sorted(addr for addr in THREAD_STARTS.values() if addr in EXACT_CARRIERS)
    if exact_hits:
        raise ValueError(f"exact HDVehicle+0x4330 carrier used as thread start: {exact_hits!r}")

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
            "create_thread_direct_callsite_count": len(create_rows),
            "beginthreadex_direct_callsite_count": len(begin_rows),
            "dynamic_create_thread_wrapper": "FUN_0093db2b",
            "dynamic_wrapper_direct_caller_count": len(wrapper_callers),
            "resolved_thread_start_count": len(THREAD_STARTS),
            "resolved_thread_starts": [
                {"name": name, "address": f"0x{addr:08x}"}
                for name, addr in sorted(THREAD_STARTS.items(), key=lambda item: item[1])
            ],
            "exact_4330_carrier_thread_start_count": 0,
        },
        "adjudication": {
            "thread_start_registration_surface_complete": True,
            "create_thread_surface_complete": True,
            "beginthreadex_surface_complete": True,
            "dynamic_create_thread_wrapper_resolved": True,
            "exact_4330_carrier_thread_start_found": False,
            "runtime_thread_start_callback_subset_complete": True,
            "runtime_callback_registration_ruled_out": False,
            "runtime_computed_carrier_pointers_ruled_out": False,
            "runtime_copied_or_encoded_carrier_pointers_ruled_out": False,
            "indirect_entry_into_carriers_ruled_out": False,
            "global_runtime_derived_4330_alias_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only explicit CreateThread/__beginthreadex thread-start registration visible in the pinned retail SQLite/source pair.",
            "It does not close window procedures, timers, hooks, APCs, wait callbacks, multimedia/plugin callbacks, arbitrary function-pointer stores, or computed/copied/encoded pointer paths.",
            "Source symbols identify the fixed start routine selected at each bounded registration callsite; no selected-object identity is inferred from decompiler typing.",
        ],
        "next_step": "Inventory other runtime callback-registration API families and generic function-pointer stores; keep indirect-entry and manager identity gates fail-closed until those non-thread surfaces are bounded.",
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
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
