#!/usr/bin/env python3
"""Bound whole-image literal pointer encodings for exact HDVehicle+0x4330 carriers.

The scan is byte-exact over the authoritative retail PE. It checks both 32-bit
absolute virtual addresses and image-base-relative RVAs for all 15 already
proven exact carrier entrypoints. Zero hits close only these literal encoding
classes; computed/copied/encoded runtime pointers remain open.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

FORMAT = "SHIFT.P1B.HDVehicle4330WholeImageLiteralPointerSurface/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
EXPECTED_FILE_SIZE = 8_801_792
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


def image_base(data: bytes) -> int:
    if data[:2] != b"MZ":
        raise ValueError("not an MZ executable")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("missing PE signature")
    optional = pe + 4 + 20
    if struct.unpack_from("<H", data, optional)[0] != 0x10B:
        raise ValueError("expected PE32")
    return struct.unpack_from("<I", data, optional + 28)[0]


def find_all(blob: bytes, needle: bytes) -> list[int]:
    hits = []
    start = 0
    while True:
        offset = blob.find(needle, start)
        if offset < 0:
            return hits
        hits.append(offset)
        start = offset + 1


def scan_literals(blob: bytes, base: int) -> dict:
    absolute_hits = []
    rva_hits = []
    for name, address in CARRIERS.items():
        absolute = struct.pack("<I", address)
        rva = struct.pack("<I", address - base)
        for offset in find_all(blob, absolute):
            absolute_hits.append({
                "carrier": name,
                "value": f"0x{address:08x}",
                "file_offset": offset,
            })
        for offset in find_all(blob, rva):
            rva_hits.append({
                "carrier": name,
                "value": f"0x{address - base:08x}",
                "file_offset": offset,
            })
    return {
        "absolute_va_hits": absolute_hits,
        "rva_hits": rva_hits,
    }


def analyze(exe: Path) -> dict:
    digest = sha256(exe)
    if digest != RETAIL_SHA256:
        raise ValueError(f"unexpected retail SHA-256: {digest}")
    blob = exe.read_bytes()
    if len(blob) != EXPECTED_FILE_SIZE:
        raise ValueError(f"retail file-size drift: {len(blob)}")
    base = image_base(blob)
    if base != 0x00400000:
        raise ValueError(f"unexpected image base: 0x{base:08x}")
    scan = scan_literals(blob, base)
    if scan["absolute_va_hits"] or scan["rva_hits"]:
        raise ValueError(f"exact carrier literal pointer appeared: {scan!r}")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1B / P1.3B",
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": digest,
            "retail_file_size": len(blob),
            "image_base": "0x00400000",
            "whole_file_raw_bytes_scanned": len(blob),
            "retail_bytes_are_machine_authority": True,
        },
        "upstream_contracts": [
            "SHIFT.P1B.HDVehicle4330ExternalCallerFinalTranche/1",
            "SHIFT.P1B.HDVehicle4330ExactCarrierVtableSurface/1",
            "SHIFT.P1B.HDVehicle4330ExactCarrierStaticTableLiteralPointerSurface/1",
        ],
        "carrier_set": {
            "count": len(CARRIERS),
            "functions": [
                {"name": name, "address": f"0x{address:08x}", "rva": f"0x{address - base:08x}"}
                for name, address in CARRIERS.items()
            ],
        },
        "whole_image_surface": {
            "absolute_va_encoding": "little-endian uint32",
            "rva_encoding": "little-endian uint32",
            "absolute_va_hit_count": 0,
            "rva_hit_count": 0,
            "absolute_va_hits": [],
            "rva_hits": [],
        },
        "adjudication": {
            "whole_image_exact_carrier_absolute_va_literal_surface_complete": True,
            "whole_image_exact_carrier_rva_literal_surface_complete": True,
            "whole_image_exact_carrier_literal_pointer_hit_found": False,
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
            "The scan is exhaustive for literal 32-bit absolute VA and image-base-relative RVA encodings in the retail file bytes.",
            "Direct rel32 CALL/JMP encodings do not contain the target VA/RVA and are intentionally not classified as pointer literals.",
            "Computed pointers, call/pop EIP synthesis, transformed/encoded values, and pointers copied from runtime inputs remain open.",
            "Zero literal pointer bytes do not by itself prove that indirect entry is impossible."
        ],
        "next_step": "Trace computed or copied exact-carrier function-pointer creation, prioritizing code-relative/EIP-derived synthesis and runtime callback registration. Keep the manager identity join fail-closed."
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = analyze(args.exe)
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
