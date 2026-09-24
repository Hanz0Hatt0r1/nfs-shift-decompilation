"""Decode the recovered D3D9 lookup-table bytes from a raw loaded-memory dump.

The SHIFT.exe.c export exposes table addresses and indexing but not their initializer
bytes. This module accepts a raw memory window plus its virtual base address and
extracts the table words/pointers without selecting an ABI.
"""
from __future__ import annotations

import struct
from pathlib import Path
from typing import Any


FORMAT = "SHIFT.D3D9MemoryTableEvidence/1"

TYPE_TABLE_ADDRESS = 0x00B90088
TYPE_TABLE_LAYOUT_WORDS = 20
TYPE_TABLE_PROVEN_WORDS = 17
SIZE_TABLE_ADDRESS = 0x00B900D8
SIZE_TABLE_WORDS = 17
USAGE_TABLE_ADDRESS = 0x00B9011C
USAGE_TABLE_WORDS = 9
USAGE_INDEX_TABLE_ADDRESS = 0x00B90140
USAGE_INDEX_LAYOUT_WORDS = 14
TYPE_NAME_POINTER_TABLE_ADDRESS = 0x00B901D0
TYPE_NAME_POINTERS = 17

PRINTABLE_ASCII_MIN = 0x20
PRINTABLE_ASCII_MAX = 0x7E
MAX_CSTRING = 256


def _read_u32(data: bytes, base_address: int, address: int) -> int | None:
    offset = address - base_address
    if offset < 0 or offset + 4 > len(data):
        return None
    return struct.unpack_from("<I", data, offset)[0]


def _read_u32_list(
    data: bytes,
    base_address: int,
    address: int,
    count: int,
) -> list[int | None]:
    return [
        _read_u32(data, base_address, address + index * 4)
        for index in range(count)
    ]


def _read_cstring(
    data: bytes,
    base_address: int,
    address: int,
    max_length: int = MAX_CSTRING,
) -> str | None:
    offset = address - base_address
    if offset < 0 or offset >= len(data):
        return None
    chunk = data[offset : min(len(data), offset + max_length)]
    end = chunk.find(b"\x00")
    if end >= 0:
        chunk = chunk[:end]
    if not chunk:
        return ""
    if any(byte < PRINTABLE_ASCII_MIN or byte > PRINTABLE_ASCII_MAX for byte in chunk):
        return None
    return chunk.decode("ascii", errors="strict")


def _table_report(
    data: bytes,
    base_address: int,
    name: str,
    address: int,
    count: int,
    *,
    layout_hint: bool = False,
) -> dict[str, Any]:
    values = _read_u32_list(data, base_address, address, count)
    present = sum(value is not None for value in values)
    return {
        "name": name,
        "address": f"0x{address:08x}",
        "count_requested": count,
        "values": values,
        "present_count": present,
        "complete": present == count,
        "layout_basis": "address-span-hint" if layout_hint else "source-observed-domain",
        "status": "decoded" if present == count else ("partial" if present else "out-of-range"),
    }


def analyze_d3d9_memory_tables(
    data: bytes,
    base_address: int,
    *,
    include_channel_layout_hint: bool = False,
) -> dict[str, Any]:
    """Decode D3D9 lookup tables from one raw memory window."""
    report: dict[str, Any] = {
        "format": FORMAT,
        "memory": {
            "base_address": f"0x{base_address:08x}",
            "bytes": len(data),
        },
        "tables": {
            "type_code": _table_report(
                data,
                base_address,
                "DAT_00b90088",
                TYPE_TABLE_ADDRESS,
                TYPE_TABLE_LAYOUT_WORDS,
                layout_hint=True,
            ),
            "size": _table_report(
                data,
                base_address,
                "DAT_00b900d8",
                SIZE_TABLE_ADDRESS,
                SIZE_TABLE_WORDS,
            ),
            "usage": _table_report(
                data,
                base_address,
                "DAT_00b9011c",
                USAGE_TABLE_ADDRESS,
                USAGE_TABLE_WORDS,
            ),
            "usage_index": _table_report(
                data,
                base_address,
                "DAT_00b90140",
                USAGE_INDEX_TABLE_ADDRESS,
                USAGE_INDEX_LAYOUT_WORDS,
                layout_hint=True,
            ),
        },
        "type_name_pointers": [],
        "conclusions": {
            "type_table_initializer": "decoded" if base_address <= TYPE_TABLE_ADDRESS < base_address + len(data) else "out-of-range",
            "meb_460_461_to_type_code": {
                "status": "not-proven",
                "detail": "memory bytes alone are only promoted to a mapping after explicit table contents and declaration semantics are compared; no automatic MEB property assignment is performed",
            },
        },
    }

    pointers = _read_u32_list(
        data,
        base_address,
        TYPE_NAME_POINTER_TABLE_ADDRESS,
        TYPE_NAME_POINTERS,
    )
    for ordinal, pointer in enumerate(pointers):
        entry: dict[str, Any] = {
            "ordinal": ordinal,
            "pointer": None if pointer is None else f"0x{pointer:08x}",
            "status": "unavailable" if pointer is None else "unresolved",
            "string": None,
        }
        if pointer is not None:
            value = _read_cstring(data, base_address, pointer)
            if value is not None:
                entry["status"] = "decoded"
                entry["string"] = value
        report["type_name_pointers"].append(entry)

    if include_channel_layout_hint:
        report["tables"]["channel_layout_hint"] = _table_report(
            data,
            base_address,
            "DAT_00b90178",
            0x00B90178,
            22,
            layout_hint=True,
        )

    type_values = report["tables"]["type_code"]["values"][:TYPE_TABLE_PROVEN_WORDS]
    if all(value is not None for value in type_values):
        report["proven_type_code_prefix"] = {
            "status": "decoded",
            "words": type_values,
        }
    else:
        report["proven_type_code_prefix"] = {
            "status": "partial",
            "words": type_values,
        }

    return report


def analyze_d3d9_memory_tables_file(
    path: str | Path,
    base_address: int,
    *,
    include_channel_layout_hint: bool = False,
) -> dict[str, Any]:
    source_path = Path(path)
    report = analyze_d3d9_memory_tables(
        source_path.read_bytes(),
        base_address,
        include_channel_layout_hint=include_channel_layout_hint,
    )
    report["memory"]["path"] = str(source_path)
    return report
