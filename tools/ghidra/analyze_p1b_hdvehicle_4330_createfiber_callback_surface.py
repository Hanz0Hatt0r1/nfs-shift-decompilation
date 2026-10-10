#!/usr/bin/env python3
"""Bound CreateFiber start-routine registration for P1B exact HDVehicle+0x4330 carriers."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330CreateFiberCallbackSurface/1"
SQLITE_SHA256 = "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
SUPPORTED_SQLITE = {"SHIFT.GhidraSQLiteIndex/1", "SHIFT.GhidraSQLiteIndex/2"}
EXPECTED_CALL = ("0x00a62940", "FUN_00a62940", "0x00a62a43")
START_ROUTINE = 0x00A62710
SOURCE_FRAGMENT = "CreateFiber(*(SIZE_T *)(*piVar4 + 8),lpStartAddress_00a62710,piVar4 + 2);"
EXACT_CARRIERS = {
    0x00769520, 0x0076B130, 0x0076DF50, 0x00768A4D, 0x00756050,
    0x00772200, 0x00772570, 0x007C3B00, 0x0076B280, 0x007618F0,
    0x00769640, 0x007567A0, 0x00756BB0, 0x00771DB0, 0x00771E10,
}


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
        calls = []
        for (raw_text,) in db.execute("SELECT raw_json FROM calls"):
            rec = json.loads(raw_text)
            if rec.get("to_name") != "CreateFiber":
                continue
            if rec.get("indirect") is not False:
                raise ValueError("CreateFiber gained indirect call row")
            calls.append((
                str(rec.get("from_function") or "").lower(),
                str(rec.get("from_name") or ""),
                str(rec.get("instruction") or "").lower(),
            ))
    finally:
        db.close()
    if calls != [EXPECTED_CALL]:
        raise ValueError(f"CreateFiber call surface drift: {calls!r}")

    text = source.read_text(encoding="utf-8", errors="strict")
    if text.count("CreateFiber(") != 1:
        raise ValueError(f"CreateFiber source call count drift: {text.count('CreateFiber(')}")
    if text.count(SOURCE_FRAGMENT) != 1:
        raise ValueError("CreateFiber fixed start-routine fragment drift")
    if START_ROUTINE in EXACT_CARRIERS:
        raise ValueError("CreateFiber start routine entered canonical P1B exact carrier set")

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
            "physical_callsite_count": 1,
            "callsite": "0x00a62a43",
            "caller": "0x00a62940",
            "caller_name": "FUN_00a62940",
            "start_routine": "0x00a62710",
            "start_routine_name": "lpStartAddress_00a62710",
            "fiber_parameter": "piVar4 + 2",
            "exact_4330_carrier_start_routine_count": 0,
        },
        "adjudication": {
            "createfiber_callback_surface_complete": True,
            "exact_4330_carrier_reachable_via_createfiber": False,
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
            "This closes only direct CreateFiber start-routine registration in the pinned retail SQLite/source pair.",
            "The single physical callsite uses fixed lpStartAddress_00a62710; the fiber entry itself performs further object/vtable dispatch that is outside this registration subset.",
            "Other callbacks, function-pointer stores/copies and computed indirect entry remain open."
        ],
        "next_step": "Trace remaining finite callback families and generic function-pointer stores/copies; keep global indirect-entry gates fail-closed."
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
