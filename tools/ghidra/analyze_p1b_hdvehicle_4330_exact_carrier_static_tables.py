#!/usr/bin/env python3
"""Bound literal static-table pointers to proven exact HDVehicle+0x4330 carriers."""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Iterable

FORMAT = "SHIFT.P1B.HDVehicle4330ExactCarrierStaticTableSurface/1"
STATIC_SHA256 = "798c426ef160d82ea297a088a52e737a7715febc55be631e63afa02390fc5bc2"

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


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_static_records(lines: Iterable[bytes | str]) -> dict:
    record_count = 0
    declared_length_total = 0
    raw_hex_bytes_total = 0
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
        raw_hex_bytes_total += len(blob)

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
        "raw_hex_bytes_total": raw_hex_bytes_total,
        "hits": hits,
    }


def analyze(path: Path) -> dict:
    digest = sha256(path)
    if digest != STATIC_SHA256:
        raise ValueError(f"unexpected static_tables SHA-256: {digest}")
    with path.open("rb") as stream:
        result = scan_static_records(stream)
    if result["record_count"] != 55066 or result["declared_length_total"] != 956464:
        raise ValueError(f"static-table inventory drift: {result!r}")
    if result["raw_hex_bytes_total"] != 684472:
        raise ValueError(f"static-table raw byte coverage drift: {result['raw_hex_bytes_total']}")
    if result["hits"]:
        raise ValueError("an exact HDVehicle+0x4330 carrier pointer appeared in the pinned static-table surface")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "authority": {
            "platform": "PC retail 1.02",
            "static_tables_sha256": digest,
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
        "static_table_surface": {
            "record_count": result["record_count"],
            "declared_length_total": result["declared_length_total"],
            "raw_hex_bytes_total": result["raw_hex_bytes_total"],
            "pointer_encoding": "little-endian 32-bit absolute VA",
            "exact_carrier_pointer_hit_count": 0,
            "hits": [],
        },
        "adjudication": {
            "exact_4330_carrier_static_table_literal_pointer_subset_complete": True,
            "static_table_exact_carrier_pointer_found": False,
            "runtime_generated_or_copied_function_pointers_ruled_out": False,
            "callee_created_4330_aliases_ruled_out": False,
            "global_runtime_derived_4330_alias_surface_complete": False,
            "manager_374_join_to_hdvehicle_4330_complete": False,
            "last_literal_0x004b86cf_rejected": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "This closes only literal little-endian 32-bit absolute carrier pointers inside raw bytes exported for Ghidra static-table candidates.",
            "The static-table export is finite and does not cover runtime-generated/copied/encoded pointers, computed destinations, or arbitrary heap/global writes.",
            "Carrier identity is supplied by merged retail machine contracts, not address coincidence in the export.",
        ],
        "next_step": "Trace runtime-generated/copied indirect entry and non-root-derived HDVehicle+0x4330 data aliases before changing the manager identity gate.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("static_tables", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = analyze(args.static_tables)
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
