#!/usr/bin/env python3
"""Verify the P1.3A nearest secure-copy branches against PC retail SHIFT.exe.

This closes only the named secure-copy branches selected by the Drive-backed
callgraph frontier. It does not claim exhaustive alias/bulk-copy closure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

FORMAT = "SHIFT.P1A.P13ASlot01NearestSecureCopyMachineProof/1"
RETAIL_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"

EXPECTED_BYTES = {
    0x006310F9: "e8d2900200",
    0x006310FE: "8d4806",
    0x0063110E: "890f",
    0x0063123F: "e84cffffff",
    0x00631247: "8b0f",
    0x00631249: "56505651",
    0x0063124D: "e8645d2d00",
    0x00631265: "c6041600",
    0x00631791: "e83af9ffff",
    0x00631796: "8b03",
    0x00631798: "56575650",
    0x0063179C: "e849f62c00",
    0x00632A19: "e812e8ffff",
    0x00632A2C: "e8ffe7ffff",
    0x00632A3F: "e8ece7ffff",
    0x00632A52: "e8d9e7ffff",
    0x00647827: "8d4f24",
    0x0064782A: "e8b1b1feff",
    0x0070FB72: "8dbe80030000",
    0x0070FDCB: "8d8e70030000",
    0x0070FDE1: "e8fa2bf2ff",
    0x0070FDEB: "8d8e74030000",
    0x0070FDF1: "e8ea2bf2ff",
    0x0070FDFB: "8d8e78030000",
    0x0070FE01: "e8da2bf2ff",
    0x0070FE0B: "8d8e7c030000",
    0x0070FE11: "e8ca2bf2ff",
    0x0070FE1B: "8bcf",
    0x0070FE1D: "e8be2bf2ff",
    0x0070FE27: "8bd7",
    0x0070FE29: "8d4df0",
    0x0070FE2C: "e83f2ef2ff",
}

EXPECTED_CALL_TARGETS = {
    0x006310F9: 0x0065A1D0,
    0x0063123F: 0x00631190,
    0x0063124D: 0x00906FB6,
    0x00631791: 0x006310D0,
    0x0063179C: 0x00900DEA,
    0x00632A19: 0x00631230,
    0x00632A2C: 0x00631230,
    0x00632A3F: 0x00631230,
    0x00632A52: 0x00631230,
    0x0064782A: 0x006329E0,
    0x0070FDE1: 0x006329E0,
    0x0070FDF1: 0x006329E0,
    0x0070FE01: 0x006329E0,
    0x0070FE11: 0x006329E0,
    0x0070FE1D: 0x006329E0,
    0x0070FE2C: 0x00632C70,
}


def parse_pe32(data: bytes):
    if len(data) < 0x40 or data[:2] != b"MZ":
        raise ValueError("not a PE image")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("missing PE signature")
    count = struct.unpack_from("<H", data, pe + 6)[0]
    opt_size = struct.unpack_from("<H", data, pe + 20)[0]
    opt = pe + 24
    if struct.unpack_from("<H", data, opt)[0] != 0x10B:
        raise ValueError("expected PE32")
    image_base = struct.unpack_from("<I", data, opt + 28)[0]
    table = opt + opt_size
    sections = []
    for i in range(count):
        off = table + i * 40
        sections.append({
            "rva": struct.unpack_from("<I", data, off + 12)[0],
            "raw_size": struct.unpack_from("<I", data, off + 16)[0],
            "raw_offset": struct.unpack_from("<I", data, off + 20)[0],
        })
    return image_base, sections


def read_va(data: bytes, va: int, size: int) -> bytes:
    base, sections = parse_pe32(data)
    rva = va - base
    for section in sections:
        if section["rva"] <= rva and rva + size <= section["rva"] + section["raw_size"]:
            off = section["raw_offset"] + (rva - section["rva"])
            return data[off:off + size]
    raise ValueError(f"VA 0x{va:08x} is not file-backed")


def rel32_target(data: bytes, site: int) -> int:
    raw = read_va(data, site, 5)
    if raw[0] != 0xE8:
        raise ValueError(f"0x{site:08x}: expected CALL rel32")
    rel = struct.unpack_from("<i", raw, 1)[0]
    return site + 5 + rel


def analyze(path: Path) -> dict:
    data = path.read_bytes()
    actual_sha = hashlib.sha256(data).hexdigest()
    if actual_sha != RETAIL_SHA256:
        raise ValueError(f"unexpected SHIFT.exe SHA-256: {actual_sha}")

    byte_rows = []
    for va, expected_hex in sorted(EXPECTED_BYTES.items()):
        expected = bytes.fromhex(expected_hex)
        actual = read_va(data, va, len(expected))
        if actual != expected:
            raise ValueError(
                f"0x{va:08x}: bytes mismatch: expected {expected_hex}, got {actual.hex()}"
            )
        byte_rows.append({"site": f"0x{va:08x}", "bytes": expected_hex})

    call_rows = []
    for site, expected_target in sorted(EXPECTED_CALL_TARGETS.items()):
        target = rel32_target(data, site)
        if target != expected_target:
            raise ValueError(
                f"0x{site:08x}: call target mismatch: "
                f"expected 0x{expected_target:08x}, got 0x{target:08x}"
            )
        call_rows.append({"site": f"0x{site:08x}", "target": f"0x{target:08x}"})

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "authority": {
            "platform": "PC retail 1.02",
            "retail_executable_sha256": actual_sha,
            "machine_transfer_adjudicates": True,
        },
        "verified_byte_windows": byte_rows,
        "verified_calls": call_rows,
        "copy_helper_proof": {
            "FUN_006310d0": (
                "allocates separate backing storage, advances returned pointer by 6, "
                "and stores that backing pointer into [this]"
            ),
            "FUN_00631230": (
                "loads destination from [this] and invokes 0x00906fb6 (_memmove_s); "
                "the destination is backing storage, not the inline string object"
            ),
            "FUN_00631740": (
                "allocates backing storage, loads destination from [this], and invokes "
                "0x00900dea (_memcpy_s)"
            ),
            "FUN_006329e0": (
                "bounded NUL-length scan followed by one of four calls to FUN_00631230"
            ),
        },
        "nearest_branch_proof": {
            "FUN_0070fae0_receivers": [
                "object+0x370",
                "object+0x374",
                "object+0x378",
                "object+0x37c",
                "object+0x380",
                "stack-local string object fed from object+0x380",
            ],
            "FUN_00647820_receiver": "containing object+0x24",
            "copy_destination_domain": "separately allocated string backing storage reached through [string_object]",
            "writes_inline_wheel_target_bytes": False,
            "targets_rejected": [
                "HDVehicle+0x938",
                "HDVehicle+0x13b8",
                "wheel-local +0x538",
            ],
        },
        "adjudication": {
            "nearest_named_secure_copy_branches_rejected_as_slot01_target_writers": True,
            "all_named_copy_paths_exhausted": False,
            "inline_or_custom_bulk_copy_ruled_out": False,
            "indirect_copy_dispatch_ruled_out": False,
            "slot0_selected_root_alias_callee_bulk_copy_complete": False,
            "slot1_selected_root_alias_callee_bulk_copy_complete": False,
            "p13a_slot0_complete": False,
            "p13a_slot1_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "next_step": (
            "Remove these secure-string branches from the slot0/slot1 bulk-copy frontier, "
            "then trace remaining interprocedural aliases and inline/custom copy/init paths."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = analyze(args.executable)
    except ValueError as exc:
        parser.error(str(exc))
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
