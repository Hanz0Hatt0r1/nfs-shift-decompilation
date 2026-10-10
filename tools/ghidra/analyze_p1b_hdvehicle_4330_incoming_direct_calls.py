#!/usr/bin/env python3
"""Inventory direct incoming calls into exact HDVehicle+0x4330 carrier functions."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330IncomingDirectCallFrontier/1"
SQLITE_SHA256 = "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
SUPPORTED = {"SHIFT.GhidraSQLiteIndex/1", "SHIFT.GhidraSQLiteIndex/2"}
CARRIERS = {
    "0x00769520": "FUN_00769520",
    "0x0076b130": "FUN_0076b130",
    "0x0076df50": "FUN_0076df50",
    "0x00768a4d": "FUN_00768a4d",
    "0x00756050": "FUN_00756050",
    "0x00772200": "FUN_00772200",
    "0x00772570": "FUN_00772570",
    "0x007c3b00": "FUN_007c3b00",
    "0x0076b280": "FUN_0076b280",
    "0x007618f0": "FUN_007618f0",
    "0x00769640": "FUN_00769640",
    "0x007567a0": "FUN_007567a0",
    "0x00756bb0": "FUN_00756bb0",
    "0x00771db0": "FUN_00771db0",
    "0x00771e10": "FUN_00771e10",
}
EXPECTED_EXTERNAL_CALLERS = {
    "0x00aa2850": "FUN_00aa2850",
    "0x0074da70": "FUN_0074da70",
    "0x00798df0": "FUN_00798df0",
    "0x00491d86": "FUN_00491d86",
    "0x00a7063f": "Unwind@00a7063f",
    "0x00a72322": "Unwind@00a72322",
    "0x00795d60": "FUN_00795d60",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def analyze(database: Path) -> dict:
    digest = sha256(database)
    if digest != SQLITE_SHA256:
        raise ValueError(f"unexpected SQLite SHA-256: {digest}")
    db = sqlite3.connect(database)
    try:
        row = db.execute("SELECT value FROM metadata WHERE key='format'").fetchone()
        fmt = None if row is None else row[0]
        if fmt not in SUPPORTED:
            raise ValueError(f"unsupported SQLite format: {fmt!r}")

        direct = []
        for (raw_text,) in db.execute("SELECT raw_json FROM calls"):
            rec = json.loads(raw_text)
            if rec.get("indirect") is True:
                continue
            target = str(rec.get("to") or "").lower()
            if target not in CARRIERS:
                continue
            source = str(rec.get("from_function") or "").lower()
            direct.append({
                "caller": source,
                "caller_name": rec.get("from_name"),
                "callsite": str(rec.get("instruction") or "").lower(),
                "target": target,
                "target_name": rec.get("to_name"),
                "caller_is_exact_carrier": source in CARRIERS,
            })

        direct.sort(key=lambda x: (x["callsite"], x["target"]))
        internal = [row for row in direct if row["caller_is_exact_carrier"]]
        external = [row for row in direct if not row["caller_is_exact_carrier"]]
        external_callers = {row["caller"]: row["caller_name"] for row in external}

        if len(direct) != 25 or len(internal) != 14 or len(external) != 11:
            raise ValueError("incoming direct-call inventory drift")
        if external_callers != EXPECTED_EXTERNAL_CALLERS:
            raise ValueError(f"external caller set drift: {external_callers!r}")

        return {
            "format": FORMAT,
            "version": 1,
            "ready": True,
            "owner": "Process 1B / P1.3B",
            "authority": {
                "platform": "PC retail 1.02",
                "ghidra_sqlite_sha256": digest,
                "ghidra_sqlite_format": fmt,
                "sqlite_is_navigation_index": True,
            },
            "carrier_set": {"count": len(CARRIERS), "functions": CARRIERS},
            "incoming_direct_surface": {
                "callsite_count": len(direct),
                "exact_carrier_internal_callsite_count": len(internal),
                "external_callsite_count": len(external),
                "external_caller_count": len(external_callers),
                "external_callers": [
                    {"address": address, "name": name}
                    for address, name in EXPECTED_EXTERNAL_CALLERS.items()
                ],
                "external_calls": external,
            },
            "adjudication": {
                "incoming_direct_call_frontier_inventory_complete": True,
                "known_internal_carrier_edges_separated": True,
                "external_receiver_provenance_complete": False,
                "indirect_entry_into_carriers_ruled_out": False,
                "global_runtime_derived_4330_alias_surface_complete": False,
                "manager_374_join_to_hdvehicle_4330_complete": False,
                "last_literal_0x004b86cf_rejected": False,
                "p1_3_control_producer_complete": False,
                "external_provider_count": 7,
            },
            "limits": [
                "Direct callgraph reachability is not HDVehicle+0x4330 receiver identity.",
                "The seven external callers require exact receiver/argument provenance before any can be admitted or rejected as an alternate 0x4330 path.",
                "Two external caller records are named Unwind@ by Ghidra; that label alone is not sufficient to reject them as non-executable metadata.",
            ],
            "next_step": "Adjudicate the seven external caller functions by exact machine receiver provenance, starting with one-hop wrappers and the FUN_00798df0 cluster.",
        }
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = analyze(args.database)
    except ValueError as exc:
        parser.error(str(exc))
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
