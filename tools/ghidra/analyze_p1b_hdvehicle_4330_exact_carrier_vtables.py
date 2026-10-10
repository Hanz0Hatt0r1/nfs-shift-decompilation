#!/usr/bin/env python3
"""Bound vtable-target references to proven exact HDVehicle+0x4330 carriers.

The Ghidra vtable export is navigation/cross-check evidence only. Exact object
identity remains owned by merged retail machine contracts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330ExactCarrierVtableSurface/1"
VTABLE_FORMAT = "SHIFT.GhidraVtableCandidates/1"
VTABLE_SHA256 = "15ca935e5bdca1efe2e6b3cac8eb01d20b54c05c5abf829cdb5903b62e52a7ed"

CARRIERS = {
    "FUN_00769520": 0x00769520,
    "FUN_0076b130": 0x0076B130,
    "FUN_0076df50": 0x0076DF50,
    "FUN_00768a4d": 0x00768A4D,
    "FUN_00756050": 0x00756050,
    "FUN_00772200": 0x00772200,
    "FUN_00772570": 0x00772570,
    "FUN_007c3b00": 0x007C3B00,
    "FUN_0076b280": 0x0076B280,
    "FUN_007618f0": 0x007618F0,
    "FUN_00769640": 0x00769640,
    "FUN_007567a0": 0x007567A0,
    "FUN_00756bb0": 0x00756BB0,
    "FUN_00771db0": 0x00771DB0,
    "FUN_00771e10": 0x00771E10,
}
ADDR_TO_NAME = {address: name for name, address in CARRIERS.items()}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_vtables(payload: dict) -> dict:
    if payload.get("format") != VTABLE_FORMAT:
        raise ValueError(f"unexpected vtable format: {payload.get('format')!r}")
    tables = payload.get("vtables")
    if not isinstance(tables, list):
        raise ValueError("vtables must be a list")

    hits = []
    slot_count = 0
    for table in tables:
        slots = table.get("slots", [])
        if not isinstance(slots, list):
            raise ValueError("vtable slots must be a list")
        slot_count += len(slots)
        for slot in slots:
            try:
                target = int(str(slot.get("target")), 0)
            except (TypeError, ValueError):
                continue
            name = ADDR_TO_NAME.get(target)
            if name:
                hits.append({
                    "carrier": name,
                    "target": f"0x{target:08x}",
                    "vtable": str(table.get("address")),
                    "slot": slot.get("slot"),
                })
    return {"table_count": len(tables), "slot_count": slot_count, "hits": hits}


def analyze(vtables_path: Path) -> dict:
    digest = sha256(vtables_path)
    if digest != VTABLE_SHA256:
        raise ValueError(f"unexpected vtables SHA-256: {digest}")
    result = scan_vtables(json.loads(vtables_path.read_text(encoding="utf-8")))
    if result["table_count"] != 2533 or result["slot_count"] != 22416:
        raise ValueError(f"vtable inventory drift: {result!r}")
    if result["hits"]:
        raise ValueError("an exact HDVehicle+0x4330 carrier appeared as a pinned vtable target")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "authority": {
            "platform": "PC retail 1.02",
            "vtables_sha256": digest,
            "export_is_navigation_crosscheck_only": True,
        },
        "carrier_set": {
            "count": len(CARRIERS),
            "rows": [
                {"name": name, "address": f"0x{address:08x}"}
                for name, address in CARRIERS.items()
            ],
            "semantic_identity_source": "merged exact HDVehicle+0x4330 materializer/consumer retail machine contracts",
        },
        "vtable_surface": {
            "candidate_table_count": result["table_count"],
            "slot_count": result["slot_count"],
            "exact_carrier_target_hit_count": 0,
            "hits": [],
        },
        "adjudication": {
            "exact_4330_carrier_vtable_target_subset_complete": True,
            "static_vtable_exact_carrier_target_found": False,
            "runtime_generated_or_copied_function_pointers_ruled_out": False,
            "callee_created_4330_aliases_ruled_out": False,
            "global_runtime_derived_4330_alias_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only the pinned Ghidra vtable-candidate target subset for the 15 already-proven exact carriers.",
            "Zero vtable hits does not exclude runtime-generated/copied/encoded function pointers, unresolved indirect entry, callee-created aliases, or data-pointer persistence.",
            "The export does not establish object identity; merged retail machine contracts do.",
        ],
        "next_step": "Trace runtime/generated indirect entry and non-root-derived HDVehicle+0x4330 data aliases; keep the manager+0x374 join fail-closed until those bounded avenues close.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vtables", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = analyze(args.vtables)
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
