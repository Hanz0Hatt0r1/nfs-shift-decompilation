#!/usr/bin/env python3
"""Cross-check FUN_00755950 dispatch carriers against retail machine proof.

The Ghidra SQLite/vtable/static-table exports are navigation indexes. Version-1
SQLite indexes stored authoritative call targets in raw_json while some legacy
callee columns were left empty, so this analyzer reports both surfaces.
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


def callgraph_matches(db_path: Path, target_hex: str) -> dict:
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    try:
        fmt_row = db.execute("SELECT value FROM metadata WHERE key='format'").fetchone()
        fmt = str(fmt_row[0]) if fmt_row else ""
        columns = {row[1] for row in db.execute("PRAGMA table_info(calls)")}
        if fmt == "SHIFT.GhidraSQLiteIndex/1":
            column_rows = db.execute(
                "SELECT raw_json FROM calls WHERE lower(callee)=lower(?) ORDER BY callsite",
                (target_hex,),
            ).fetchall()
            normalized: list[dict] = []
            for row in db.execute("SELECT caller,callee,callsite,kind,raw_json FROM calls ORDER BY callsite"):
                rec = json.loads(row["raw_json"])
                to_addr = str(rec.get("to") or row["callee"] or "")
                to_name = str(rec.get("to_name") or rec.get("callee") or to_addr)
                if target_hex.lower() not in {to_addr.lower(), to_name.lower()}:
                    continue
                normalized.append(
                    {
                        "from_function": str(rec.get("from_function") or row["caller"] or ""),
                        "from_name": str(rec.get("from_name") or rec.get("caller") or rec.get("from_function") or row["caller"] or ""),
                        "instruction": str(rec.get("instruction") or rec.get("callsite") or row["callsite"] or ""),
                        "to": to_addr,
                        "to_name": to_name,
                        "indirect": bool(rec.get("indirect")),
                    }
                )
            return {
                "index_format": fmt,
                "legacy_callee_column_match_count": len(column_rows),
                "normalized_match_count": len(normalized),
                "callers": normalized,
            }

        if {"callee", "callee_address"}.issubset(columns):
            rows = db.execute(
                "SELECT raw_json FROM calls WHERE lower(callee)=lower(?) OR lower(callee_address)=lower(?) ORDER BY callsite",
                (target_hex, target_hex),
            ).fetchall()
            normalized = [json.loads(row["raw_json"]) for row in rows]
            return {
                "index_format": fmt,
                "legacy_callee_column_match_count": len(rows),
                "normalized_match_count": len(normalized),
                "callers": normalized,
            }
        raise ValueError(f"unsupported calls schema for {fmt!r}")
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
    callgraph = callgraph_matches(db_path, target_hex)
    callers = callgraph["callers"]
    machine_call = load_machine_call(machine_proof_path)
    vt_count, vt_slots, vt_hits = vtable_slots(vtables_path, target_hex)
    st_count, st_bytes, st_hits = static_pointer_hits(static_tables_path, target)
    machine_call_covered = any(str(rec.get("instruction", "")).lower() == machine_call["call_instruction"].lower() for rec in callers)
    legacy_gap = (
        callgraph["index_format"] == "SHIFT.GhidraSQLiteIndex/1"
        and callgraph["legacy_callee_column_match_count"] < callgraph["normalized_match_count"]
    )

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
        "sqlite_callgraph": {
            **callgraph,
            "known_machine_call_covered_after_raw_json_normalization": machine_call_covered,
            "legacy_v1_callee_column_population_gap": legacy_gap,
        },
        "heuristic_vtables": {"table_count": vt_count, "slot_count": vt_slots, "target_slot_hit_count": len(vt_hits), "target_slot_hits": vt_hits},
        "static_tables": {"record_count": st_count, "exported_byte_count": st_bytes, "literal_pointer_hit_count": len(st_hits), "literal_pointer_hits": st_hits},
        "adjudication": {
            "direct_call_carrier_proven_by_machine": True,
            "normalized_sqlite_callgraph_recovers_machine_call": machine_call_covered,
            "legacy_v1_column_population_gap_proven": legacy_gap,
            "heuristic_vtable_carrier_present": bool(vt_hits),
            "static_literal_pointer_carrier_present": bool(st_hits),
            "vtable_or_static_pointer_misses_prove_carrier_absence": False,
            "slot3_writer_provenance_proven": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "Version-1 callee-column misses are navigation-index defects when raw_json contains the target; they are not semantic absence proofs.",
            "The vtable export is heuristic and a miss cannot rule out virtual dispatch.",
            "A static-table literal-pointer miss cannot rule out code-built, copied, registered, relocated, or runtime-resolved pointers.",
            "The proven FUN_00758b50 -> FUN_00755950 call establishes the consumer lifecycle but not the writer of selected HDVehicle+0x28b8."
        ],
        "next_step": "Use the proven FUN_00758b50 wheel lifecycle and exact HDVehicle+0x400+slot*0xa80 receiver expression to trace alias/callee/bulk-copy writes to slot3; use raw_json-compatible caller queries for v1 indexes."
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
