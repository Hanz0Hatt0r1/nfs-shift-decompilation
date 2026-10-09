#!/usr/bin/env python3
"""Close the exact-HDVehicle FUN_00758810 branch for P1.3D slot3.

The PC retail decompiler export is source evidence, joined to the pinned Ghidra
SQLite direct edge and existing BODY/resource identity contracts. Numeric offset
equality is never promoted to selected-object identity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

FORMAT = "SHIFT.P1D.Slot3Fun00758810SourceClosure/1"
SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
SQLITE_SHA256 = "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
RESOURCE_FORMAT = "SHIFT.BMWOffset33bResourceInputs/1"
BODY0_FORMAT = "SHIFT.Fun007682c0Body0DeltaDestination/1"
SUPPORTED_SQLITE_FORMATS = {"SHIFT.GhidraSQLiteIndex/1", "SHIFT.GhidraSQLiteIndex/2"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path, fmt: str) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("format") != fmt or payload.get("ready") is not True:
        raise ValueError(f"{path}: unexpected or unready contract")
    return payload


def extract_function(text: str, signature: str, next_signature: str) -> str:
    start = text.find(signature)
    if start < 0:
        raise ValueError(f"missing source signature: {signature}")
    end = text.find(next_signature, start + len(signature))
    if end < 0:
        raise ValueError(f"missing next source signature after {signature}")
    return text[start:end]


def validate_sqlite(database: Path) -> dict:
    digest = sha256(database)
    if digest != SQLITE_SHA256:
        raise ValueError(f"unexpected SQLite SHA-256: {digest}")
    db = sqlite3.connect(database)
    try:
        row = db.execute("SELECT value FROM metadata WHERE key='format'").fetchone()
        fmt = None if row is None else row[0]
        if fmt not in SUPPORTED_SQLITE_FORMATS:
            raise ValueError(f"unsupported SQLite format: {fmt!r}")
        fn = db.execute(
            "SELECT raw_json FROM functions WHERE lower(address)='0x00758810'"
        ).fetchone()
        if fn is None:
            raise ValueError("FUN_00758810 missing from SQLite")
        function = json.loads(fn[0])
        if function.get("name") != "FUN_00758810" or int(function.get("size") or 0) != 347:
            raise ValueError("FUN_00758810 function identity drift")

        matches = []
        for (raw,) in db.execute("SELECT raw_json FROM calls"):
            rec = json.loads(raw)
            if (
                str(rec.get("from_function", "")).lower() == "0x0076d100"
                and str(rec.get("instruction", "")).lower() == "0x0076d193"
                and str(rec.get("to", "")).lower() == "0x00758810"
                and rec.get("indirect") is False
            ):
                matches.append(rec)
        if len(matches) != 1:
            raise ValueError(f"expected one exact FUN_00758810 edge, got {len(matches)}")
        return {
            "format": fmt,
            "sha256": digest,
            "function_size": 347,
            "direct_callsite": "0x0076d193",
        }
    finally:
        db.close()


def analyze(source: Path, database: Path, resource_path: Path, body0_path: Path) -> dict:
    source_digest = sha256(source)
    if source_digest != SOURCE_SHA256:
        raise ValueError(f"unexpected SHIFT.exe.c SHA-256: {source_digest}")
    text = source.read_text(encoding="utf-8", errors="replace")
    sqlite = validate_sqlite(database)
    resource = load_json(resource_path, RESOURCE_FORMAT)
    body0 = load_json(body0_path, BODY0_FORMAT)

    setup = extract_function(
        text,
        "void __thiscall FUN_007615c0(void *this,char *param_1)",
        "void __thiscall FUN_007618f0",
    )
    caller = extract_function(
        text,
        "void __thiscall FUN_0076d100(void *this,char param_1)",
        "void __fastcall FUN_0076d3c0",
    )
    callee = extract_function(
        text,
        "void __fastcall FUN_00758810(int param_1)",
        "void __thiscall FUN_00758970",
    )

    fuel_lookup = (
        'iVar3 = FUN_007b3da0(*(void **)((int)this + 0x339c),"fuel_tank");\n'
        '  *(int *)((int)this + 0x280) = iVar3;'
    )
    if setup.count(fuel_lookup) != 1:
        raise ValueError("HDVehicle+0x280 fuel_tank lookup binding drift")
    if caller.count("FUN_00758810((int)this);") != 1:
        raise ValueError("FUN_0076d100 direct receiver forwarding drift")

    required_callee = [
        "pdVar4 = *(double **)(param_1 + 0x280);",
        "iVar1 = *(int *)(param_1 + 0x280);",
        "*(double *)(iVar1 + 0x60) = *(double *)(iVar1 + 0x60) + local_48;",
        "*(double *)(iVar1 + 0x68) = *(double *)(iVar1 + 0x68) + local_40;",
        "*(double *)(iVar1 + 0x70) = *(double *)(iVar1 + 0x70) + local_38;",
        "FUN_007baaf0(*(void **)(param_1 + 0x33a0),&local_30,&local_48);",
        "(double *)(param_1 + 0x268),&local_30);",
    ]
    for needle in required_callee:
        if needle not in callee:
            raise ValueError(f"FUN_00758810 source anchor drift: {needle}")
    if "0x28b8" in callee.lower():
        raise ValueError("FUN_00758810 unexpectedly contains selected literal offset")

    bodies = resource.get("sdf", {}).get("bodies", [])
    fuel = next((row for row in bodies if row.get("name") == "fuel_tank"), None)
    chassis = next((row for row in bodies if row.get("name") == "body"), None)
    if not fuel or fuel.get("index") != 9:
        raise ValueError("BMW fuel_tank resource identity drift")
    if not chassis or chassis.get("index") != 0:
        raise ValueError("BMW chassis BODY0 resource identity drift")
    if fuel.get("index") == chassis.get("index"):
        raise ValueError("fuel_tank and chassis BODY identities collapsed")

    identity = body0.get("identity_join", {})
    if identity.get("chassis_BODY_pointer_field") != "HDVehicle+0x33a0":
        raise ValueError("HDVehicle+0x33a0 BODY0 identity drift")
    if identity.get("destination_is_retail_BMW_chassis_BODY0") is not True:
        raise ValueError("retail chassis BODY0 identity is no longer proven")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_decompiler_source_sha256": source_digest,
            "ghidra_sqlite_sha256": sqlite["sha256"],
            "ghidra_sqlite_format": sqlite["format"],
            "source_identity_is_pinned_to_retail_export": True,
        },
        "selected_slot3": {
            "absolute_target": "HDVehicle+0x28b8..+0x28bf",
            "width": "f64/qword",
        },
        "entry": {
            "caller": "FUN_0076d100",
            "callsite": sqlite["direct_callsite"],
            "callee": "FUN_00758810",
            "receiver": "HDVehicle",
            "callee_size": sqlite["function_size"],
        },
        "object_identity": {
            "fuel_tank_pointer_field": "HDVehicle+0x280",
            "fuel_tank_binding": "FUN_007b3da0(..., \"fuel_tank\")",
            "selected_BMW_SDF_fuel_tank_body_index": 9,
            "chassis_body_pointer_field": "HDVehicle+0x33a0",
            "selected_BMW_chassis_BODY0_index": 0,
            "fuel_tank_is_chassis_BODY0": False,
            "pointer_fields_are_embedded_target_bytes": False,
        },
        "callee_effect": {
            "direct_persistent_write_owner": "fuel_tank BODY record",
            "direct_persistent_write_offsets": ["+0x60", "+0x68", "+0x70"],
            "body0_helper_receiver": "HDVehicle+0x33a0 -> chassis BODY0",
            "hdvehicle_subobject_argument": "HDVehicle+0x268",
            "contains_literal_0x28b8": False,
            "selected_slot3_write_found": False,
        },
        "adjudication": {
            "slot3_fun0076d100_to_fun00758810_exact_root_branch_complete": True,
            "fun00758810_selected_slot3_writer_found": False,
            "fun00758810_fuel_tank_destination_identity_proven": True,
            "fun00758810_chassis_body_destination_separate_from_hdvehicle": True,
            "deeper_direct_aliases_ruled_out": False,
            "stored_or_escaped_aliases_ruled_out": False,
            "indirect_callback_aliases_ruled_out": False,
            "slot3_writer_provenance_proven": False,
            "p1_3d_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only the exact FUN_0076d100 -> FUN_00758810 branch.",
            "Writes through HDVehicle+0x280 are assigned to the separately named fuel_tank BODY lookup, not to HDVehicle by numeric offset coincidence.",
            "The BODY0 helper receiver comes from the independently proven HDVehicle+0x33a0 chassis BODY pointer field.",
            "Stored aliases, other lifecycle descendants and indirect/callback carriers remain open."
        ],
        "next_step": "Compose the now-closed FUN_00758810 and FUN_00769ef0 exact-root branches into the remaining slot3 lifecycle frontier; then trace only stored/escaped or indirect carriers with exact selected-wheel identity.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("database", type=Path)
    parser.add_argument("resource_inputs", type=Path)
    parser.add_argument("body0_destination", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = analyze(args.source, args.database, args.resource_inputs, args.body0_destination)
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
