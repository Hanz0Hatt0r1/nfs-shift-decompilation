#!/usr/bin/env python3
"""Bound known static dispatch carriers for FUN_00755950.

This is a navigation/provenance helper, not a proof that FUN_00755950 is unreachable.
It checks three finite surfaces exported by the current Ghidra database bundle:
1) direct callgraph edges, 2) heuristic vtable slots, and 3) literal 32-bit
function pointers embedded in exported static tables.

If all three are empty, runtime registration, code-built pointers, indirect calls,
virtual/callback dispatch missed by the heuristic index, and other dynamic carriers
remain open.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

FORMAT = "SHIFT.P1D.Slot3DispatchCarrierBoundary/1"
TARGET = 0x00755950


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def direct_callers(db_path: Path, target_hex: str) -> list[dict]:
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    try:
        rows = db.execute(
            "SELECT raw_json FROM calls WHERE lower(callee)=lower(?) ORDER BY callsite",
            (target_hex,),
        ).fetchall()
        return [json.loads(row["raw_json"]) for row in rows]
    finally:
        db.close()


def vtable_slots(vtables_path: Path, target_hex: str) -> tuple[int, int, list[dict]]:
    payload = json.loads(vtables_path.read_text(encoding="utf-8"))
    tables = payload.get("vtables", [])
    slot_count = 0
    hits: list[dict] = []
    for table in tables:
        for slot in table.get("slots", []):
            slot_count += 1
            if str(slot.get("target", "")).lower() == target_hex.lower():
                hits.append(
                    {
                        "vtable": table.get("address"),
                        "slot": slot.get("slot"),
                        "target": slot.get("target"),
                        "name": slot.get("name"),
                    }
                )
    return len(tables), slot_count, hits


def static_pointer_hits(static_tables_path: Path, target: int) -> tuple[int, int, list[dict]]:
    needle = target.to_bytes(4, "little").hex()
    records = 0
    total_exported_bytes = 0
    hits: list[dict] = []
    with static_tables_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            records += 1
            rec = json.loads(line)
            total_exported_bytes += int(rec.get("length", 0) or 0)
            raw_hex = str(rec.get("raw_hex", "")).lower()
            start = 0
            while True:
                pos = raw_hex.find(needle, start)
                if pos < 0:
                    break
                hits.append(
                    {
                        "table_address": rec.get("address"),
                        "block": rec.get("block"),
                        "data_type": rec.get("data_type"),
                        "byte_offset": pos // 2,
                    }
                )
                start = pos + 2
    return records, total_exported_bytes, hits


def analyze(db_path: Path, vtables_path: Path, static_tables_path: Path, target: int = TARGET) -> dict:
    target_hex = f"0x{target:08x}"
    callers = direct_callers(db_path, target_hex)
    vtable_count, vtable_slot_count, vtable_hits = vtable_slots(vtables_path, target_hex)
    static_record_count, static_exported_bytes, static_hits = static_pointer_hits(static_tables_path, target)

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "scope": "FUN_00755950 / HDVehicle+0x28b8 slot3 provenance navigation",
        "target": {"address": target_hex, "name": "FUN_00755950"},
        "authority": {
            "ghidra_sqlite_sha256": sha256(db_path),
            "vtables_sha256": sha256(vtables_path),
            "static_tables_sha256": sha256(static_tables_path),
            "indexes_are_navigation_evidence": True,
        },
        "direct_callgraph": {
            "caller_count": len(callers),
            "callers": callers,
        },
        "heuristic_vtables": {
            "table_count": vtable_count,
            "slot_count": vtable_slot_count,
            "target_slot_hit_count": len(vtable_hits),
            "target_slot_hits": vtable_hits,
        },
        "static_tables": {
            "record_count": static_record_count,
            "exported_byte_count": static_exported_bytes,
            "literal_pointer_hit_count": len(static_hits),
            "literal_pointer_hits": static_hits,
        },
        "adjudication": {
            "direct_call_carrier_present": bool(callers),
            "heuristic_vtable_carrier_present": bool(vtable_hits),
            "static_literal_pointer_carrier_present": bool(static_hits),
            "known_exported_static_carriers_empty": not callers and not vtable_hits and not static_hits,
            "runtime_or_code_built_indirect_dispatch_ruled_out": False,
            "consumer_unreachable_proven": False,
            "slot3_writer_provenance_proven": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "Zero direct callers does not prove the function is unreachable; indirect calls are outside the direct callgraph surface.",
            "The vtable export is heuristic and may omit valid virtual-dispatch structures.",
            "Absence of a literal pointer from static tables does not rule out code-built, relocated, copied, registered, or runtime-resolved function pointers.",
            "This contract bounds consumer dispatch carriers only; it does not itself identify the writer of HDVehicle+0x28b8.",
        ],
        "next_step": (
            "Trace runtime/code-built registration or indirect-call sites that can produce FUN_00755950 as a target, then use the exact selected HDVehicle root from that lifecycle to search alias/callee/bulk-copy writers of +0x28b8."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--vtables", required=True, type=Path)
    parser.add_argument("--static-tables", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--target", default=f"0x{TARGET:08x}")
    args = parser.parse_args()
    payload = analyze(args.database, args.vtables, args.static_tables, int(args.target, 0))
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
