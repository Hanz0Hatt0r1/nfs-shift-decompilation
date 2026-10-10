#!/usr/bin/env python3
"""Bound static pointer-table references to proven P1.3D slot3 carrier functions.

This is navigation/cross-check evidence only. Exact object identity remains owned by
merged retail machine contracts; absence from exported vtable/static-table
candidates is not a whole-program proof against runtime/generated pointers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Iterable

FORMAT = "SHIFT.P1D.Slot3ExactCarrierStaticPointerSurface/1"
VTABLE_FORMAT = "SHIFT.GhidraVtableCandidates/1"
VTABLE_SHA256 = "15ca935e5bdca1efe2e6b3cac8eb01d20b54c05c5abf829cdb5903b62e52a7ed"
STATIC_SHA256 = "798c426ef160d82ea297a088a52e737a7715febc55be631e63afa02390fc5bc2"

CARRIERS = {
    "FUN_00758b50": 0x00758B50,
    "FUN_00755950": 0x00755950,
    "FUN_00770e80": 0x00770E80,
    "FUN_00755a60": 0x00755A60,
    "FUN_00752fc0": 0x00752FC0,
    "FUN_00760b50": 0x00760B50,
    "FUN_00763570": 0x00763570,
    "FUN_00755f80": 0x00755F80,
    "FUN_0076d100": 0x0076D100,
    "FUN_00758810": 0x00758810,
    "FUN_00769ef0": 0x00769EF0,
    "FUN_007675f0": 0x007675F0,
    "FUN_007682c0": 0x007682C0,
    "FUN_00766510": 0x00766510,
    "FUN_00758fc0": 0x00758FC0,
    "FUN_00765c40": 0x00765C40,
}
ADDR_TO_NAME = {value: key for key, value in CARRIERS.items()}


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
            target_text = slot.get("target")
            try:
                target = int(str(target_text), 0)
            except (TypeError, ValueError):
                continue
            if target in ADDR_TO_NAME:
                hits.append({
                    "carrier": ADDR_TO_NAME[target],
                    "target": f"0x{target:08x}",
                    "vtable": str(table.get("address")),
                    "slot": slot.get("slot"),
                })
    return {"table_count": len(tables), "slot_count": slot_count, "hits": hits}


def scan_static_records(lines: Iterable[bytes | str]) -> dict:
    record_count = 0
    declared_length_total = 0
    raw_bytes_total = 0
    hits = []
    needles = {name: struct.pack("<I", address) for name, address in CARRIERS.items()}
    for raw_line in lines:
        if isinstance(raw_line, bytes):
            raw_line = raw_line.decode("utf-8")
        if not raw_line.strip():
            continue
        row = json.loads(raw_line)
        record_count += 1
        length = row.get("length")
        if isinstance(length, int):
            declared_length_total += length
        raw_hex = row.get("raw_hex", "")
        try:
            blob = bytes.fromhex(raw_hex)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid raw_hex at record {record_count}") from exc
        raw_bytes_total += len(blob)
        for name, needle in needles.items():
            start = 0
            while True:
                offset = blob.find(needle, start)
                if offset < 0:
                    break
                hits.append({
                    "carrier": name,
                    "target": f"0x{CARRIERS[name]:08x}",
                    "record_address": str(row.get("address")),
                    "data_type": row.get("data_type"),
                    "byte_offset": offset,
                })
                start = offset + 1
    return {
        "record_count": record_count,
        "declared_length_total": declared_length_total,
        "raw_hex_bytes_total": raw_bytes_total,
        "hits": hits,
    }


def analyze(vtables_path: Path, static_tables_path: Path) -> dict:
    vhash = sha256(vtables_path)
    shash = sha256(static_tables_path)
    if vhash != VTABLE_SHA256:
        raise ValueError(f"unexpected vtables SHA-256: {vhash}")
    if shash != STATIC_SHA256:
        raise ValueError(f"unexpected static-tables SHA-256: {shash}")

    vtable_result = scan_vtables(json.loads(vtables_path.read_text(encoding="utf-8")))
    with static_tables_path.open("rb") as stream:
        static_result = scan_static_records(stream)

    if vtable_result["table_count"] != 2533 or vtable_result["slot_count"] != 22416:
        raise ValueError(f"vtable inventory drift: {vtable_result!r}")
    if static_result["record_count"] != 55066 or static_result["declared_length_total"] != 956464:
        raise ValueError(f"static-table inventory drift: {static_result!r}")
    if static_result["raw_hex_bytes_total"] != 684472:
        raise ValueError(f"static-table raw byte coverage drift: {static_result['raw_hex_bytes_total']}")
    if vtable_result["hits"] or static_result["hits"]:
        raise ValueError("an exact carrier pointer appeared in a pinned static candidate surface")

    carriers = [{"name": name, "address": f"0x{address:08x}"} for name, address in CARRIERS.items()]
    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "authority": {
            "platform": "PC retail 1.02",
            "vtables_sha256": vhash,
            "static_tables_sha256": shash,
            "exports_are_navigation_crosscheck_only": True,
        },
        "carrier_set": {
            "count": len(carriers),
            "rows": carriers,
            "semantic_identity_source": "merged P1D exact-root/exact-wheel retail machine contracts including SHIFT.P1D.Slot3Fun00765c40CarrierHandoff/1",
        },
        "vtable_surface": {
            "candidate_table_count": vtable_result["table_count"],
            "slot_count": vtable_result["slot_count"],
            "exact_carrier_target_hit_count": 0,
            "hits": [],
        },
        "static_table_surface": {
            "record_count": static_result["record_count"],
            "declared_length_total": static_result["declared_length_total"],
            "raw_hex_bytes_total": static_result["raw_hex_bytes_total"],
            "pointer_encoding": "little-endian 32-bit absolute VA",
            "exact_carrier_pointer_hit_count": 0,
            "hits": [],
        },
        "adjudication": {
            "exact_carrier_vtable_slot_target_subset_complete": True,
            "exact_carrier_static_table_literal_pointer_subset_complete": True,
            "static_exact_carrier_pointer_hit_found": False,
            "runtime_generated_pointer_stores_ruled_out": False,
            "unresolved_indirect_targets_ruled_out": False,
            "callee_created_aliases_ruled_out": False,
            "stored_or_escaped_aliases_ruled_out": False,
            "slot3_writer_provenance_proven": False,
            "p1_3d_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "The vtable/static-table exports are finite Ghidra candidate inventories, not exhaustive whole-image pointer provenance.",
            "Zero literal carrier addresses does not exclude runtime-generated pointers, copied pointers, encoded pointers, computed destinations, heap/global stores outside exported table records, or unresolved indirect calls.",
            "Numeric address presence would only be a navigation candidate; absence is used here only to close these two exact exported static subsets.",
        ],
        "next_step": "Trace runtime/generated pointer stores and callee-created aliases from exact carriers; join any positive escape to its consumer before changing slot3 gates.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vtables", type=Path)
    parser.add_argument("static_tables", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = analyze(args.vtables, args.static_tables)
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
