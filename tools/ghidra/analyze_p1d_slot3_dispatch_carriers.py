#!/usr/bin/env python3
"""Cross-check FUN_00755950 dispatch carriers against retail machine proof.

The Ghidra SQLite/vtable/static-table exports are navigation indexes. This tool
must not promote an index miss over direct PC-retail machine evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

FORMAT = "SHIFT.P1D.Slot3DispatchCarrierBoundary/1"
MACHINE_PROOF_FORMAT = "SHIFT.Fun00755950AbsoluteConsumedFieldMachineProof/1"
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


def load_machine_call(machine_proof_path: Path) -> dict:
    proof = json.loads(machine_proof_path.read_text(encoding="utf-8"))
    if proof.get("format") != MACHINE_PROOF_FORMAT:
        raise ValueError("unexpected FUN_00755950 machine-proof format")
    consumer = proof["consumer"]
    return {
        "caller": consumer["caller"],
        "callee": consumer["callee"],
        "call_instruction": consumer["call_instruction"],
        "wheel_runtime_this_expression": consumer["wheel_runtime_this_expression"],
    }


def vtable_slots(vtables_path: Path, target_hex: str) -> tuple[int, int, list[dict]]:
    payload = json.loads(vtables_path.read_text(encoding="utf-8"))
    tables = payload.get("vtables", [])
    slot_count = 0
    hits: list[dict] = []
    for table in tables:
        for slot in table.get("slots", []):
            slot_count += 1
            if str(slot.get("target", "")).lower() == target_hex.lower():
                hits.append({"vtable": table.get("address"), "slot": slot.get("slot"), "target": slot.get("target"), "name": slot.get("name")})
    return len(tables), slot_count, hits


def static_pointer_hits(static_tables_path: Path, target: int) -> tuple[int, int, list[dict]]:
    needle = target.to_bytes(4, "little").hex()
    records = 0
    exported_bytes = 0
    hits: list[dict] = []
    with static_tables_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            records += 1
            rec = json.loads(line)
            exported_bytes += int(rec.get("length", 0) or 0)
            raw_hex = str(rec.get("raw_hex", "")).lower()
            start = 0
            while True:
                pos = raw_hex.find(needle, start)
                if pos < 0:
                    break
                hits.append({"table_address": rec.get("address"), "block": rec.get("block"), "data_type": rec.get("data_type"), "byte_offset": pos // 2})
                start = pos + 2
    return records, exported_bytes, hits


def analyze(db_path: Path, vtables_path: Path, static_tables_path: Path, machine_proof_path: Path, target: int = TARGET) -> dict:
    target_hex = f"0x{target:08x}"
    callers = direct_callers(db_path, target_hex)
    machine_call = load_machine_call(machine_proof_path)
    vt_count, vt_slots, vt_hits = vtable_slots(vtables_path, target_hex)
    st_count, st_bytes, st_hits = static_pointer_hits(static_tables_path, target)
    machine_call_covered = any(str(rec.get("instruction", "")).lower() == machine_call["call_instruction"].lower() for rec in callers)

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
            "machine_proof_contract": MACHINE_PROOF_FORMAT,
            "pc_retail_machine_proof_overrides_index_misses": True,
        },
        "retail_machine_direct_call": machine_call,
        "sqlite_direct_callgraph": {
            "caller_count": len(callers),
            "callers": callers,
            "known_machine_call_covered": machine_call_covered,
            "coverage_gap_against_machine_proof": not machine_call_covered,
        },
        "heuristic_vtables": {"table_count": vt_count, "slot_count": vt_slots, "target_slot_hit_count": len(vt_hits), "target_slot_hits": vt_hits},
        "static_tables": {"record_count": st_count, "exported_byte_count": st_bytes, "literal_pointer_hit_count": len(st_hits), "literal_pointer_hits": st_hits},
        "adjudication": {
            "direct_call_carrier_proven_by_machine": True,
            "sqlite_direct_callgraph_complete_for_target": machine_call_covered,
            "heuristic_vtable_carrier_present": bool(vt_hits),
            "static_literal_pointer_carrier_present": bool(st_hits),
            "index_misses_can_prove_carrier_absence": False,
            "runtime_or_other_indirect_dispatch_ruled_out": False,
            "slot3_writer_provenance_proven": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "The SQLite direct-callgraph miss is contradicted by direct retail machine evidence and therefore demonstrates index incompleteness, not carrier absence.",
            "The vtable export is heuristic and a miss cannot rule out virtual dispatch.",
            "A static-table literal-pointer miss cannot rule out code-built, copied, registered, relocated, or runtime-resolved pointers.",
            "The proven FUN_00758b50 -> FUN_00755950 call establishes the consumer lifecycle but not the writer of selected HDVehicle+0x28b8."
        ],
        "next_step": "Use the proven FUN_00758b50 wheel lifecycle and exact HDVehicle+0x400+slot*0xa80 receiver expression to trace alias/callee/bulk-copy writes to slot3; treat SQLite caller queries as non-authoritative for this target until the index exporter is repaired."
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--vtables", required=True, type=Path)
    parser.add_argument("--static-tables", required=True, type=Path)
    parser.add_argument("--machine-proof", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--target", default=f"0x{TARGET:08x}")
    args = parser.parse_args()
    payload = analyze(args.database, args.vtables, args.static_tables, args.machine_proof, int(args.target, 0))
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
