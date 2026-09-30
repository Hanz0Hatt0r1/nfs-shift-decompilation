"""Source-backed AIDatabase layout and lifecycle contract.

Recovered from the retail SHIFT.exe / SHIFT.exe.c pair. This module records
only class identity, reflected field layout, constructor-visible defaults and
the two record-array lifecycle contracts that are explicit in the recovered
code. It does not assign gameplay semantics to unreflected storage.
"""
from __future__ import annotations

import struct
from typing import Any

FORMAT = "SHIFT.AIDatabaseRuntime/1"

CLASS_NAME = "AIDatabase"
RTTI_DESCRIPTOR = 0x00C10F58
REFLECTION_METADATA = "DAT_00b8d070"
REFLECTION_BUILDER = "FUN_0071b530"
CONSTRUCTOR = "FUN_0071da20"
DESTRUCTOR = "FUN_0071dab0"
DEFAULT_INITIALIZER = "FUN_00715690"
VTABLE = 0x00B04C88

# PE startup code at 0x00a89c70 loads ECX with this address before calling
# FUN_0071da20 and then registers cleanup, proving static singleton storage.
SINGLETON_ADDRESS = 0x00C10F68
SINGLETON_INITIALIZER = 0x00A89C70

SOURCE_RECORD_PTR_OFFSET = 0x1394
SOURCE_RECORD_COUNT_OFFSET = 0x1398
META_RECORD_PTR_OFFSET = 0x139C
META_RECORD_COUNT_OFFSET = 0x13A0
META_REBUILD_FLAG_OFFSET = 0x13A4
SOURCE_RECORD_STRIDE = 0x18
META_RECORD_STRIDE = 0x14

# Direct pointer clears in FUN_0071da20 before FUN_00715690 runs.
CONSTRUCTOR_PRESET_WRITES = (
    (SOURCE_RECORD_PTR_OFFSET, 4, 0),
    (META_RECORD_PTR_OFFSET, 4, 0),
)

REFLECTED_FIELDS = (
    {"name": "Pit Lanes", "offset": 0xAC, "type_code": 0x0D, "flags": 3},
    {"name": "Starting Grid", "offset": 0xB0, "type_code": 0x0D, "flags": 3},
    {"name": "Pit Spots", "offset": 0xB4, "type_code": 0x0D, "flags": 3},
    {"name": "Garage Spots", "offset": 0xB8, "type_code": 0x0D, "flags": 3},
    {
        "name": "GRID",
        "offset": 0x9C,
        "type_code": 6,
        "flags": 2,
        "callbacks": ["FUN_00715fc0", "FUN_00716100"],
    },
    {
        "name": "TELEPORT",
        "offset": 0x98,
        "type_code": 6,
        "flags": 2,
        "callbacks": ["FUN_00716850", "FUN_007162a0"],
    },
    {
        "name": "PITS",
        "offset": 0xA0,
        "type_code": 6,
        "flags": 2,
        "callbacks": ["FUN_00716440", "FUN_00716610"],
    },
    {"name": "Track State", "offset": 0x1304, "type_code": 0x0D, "flags": 3},
    {"name": "Dry Line Time", "offset": 0x130C, "type_code": 10, "flags": 3},
    {"name": "Wet Line Time", "offset": 0x1310, "type_code": 10, "flags": 3},
    {"name": "Lap Length", "offset": 0x78, "type_code": 10, "flags": 3},
    {"name": "Sector 1 Length", "offset": 0x7C, "type_code": 10, "flags": 3},
    {"name": "Sector 2 Length", "offset": 0x80, "type_code": 10, "flags": 3},
    {"name": "Left Handed Pits", "offset": 0x64, "type_code": 0x20, "flags": 3},
    {"name": "Fuel Use", "offset": 0x8C, "type_code": 10, "flags": 3},
    {"name": "Groove Width", "offset": 0x2C, "type_code": 10, "flags": 3},
    {"name": "Wet Groove Width", "offset": 0x30, "type_code": 10, "flags": 3},
    {"name": "Garage Depth", "offset": 0x10, "type_code": 10, "flags": 3},
    {"name": "Worst Time", "offset": 0x1320, "type_code": 10, "flags": 3},
    {"name": "Mid Time", "offset": 0x1324, "type_code": 10, "flags": 3},
    {"name": "Best Time", "offset": 0x1328, "type_code": 10, "flags": 3},
    {"name": "Worst Adjust", "offset": 0x50, "type_code": 10, "flags": 3},
    {"name": "Mid Adjust", "offset": 0x54, "type_code": 10, "flags": 3},
    {"name": "Best Adjust", "offset": 0x58, "type_code": 10, "flags": 3},
    {"name": "Qual Ratio", "offset": 0x5C, "type_code": 10, "flags": 3},
    {"name": "Race Ratio", "offset": 0x60, "type_code": 10, "flags": 3},
    {"name": "Cheat Delta Worst", "offset": 0x1330, "type_code": 10, "flags": 3},
    {"name": "Cheat Delta Mid", "offset": 0x1334, "type_code": 10, "flags": 3},
    {"name": "Cheat Delta Best", "offset": 0x1338, "type_code": 10, "flags": 3},
    {"name": "Waypoints", "offset": 0x70, "type_code": 6, "flags": 2},
)

# Exact writes performed by FUN_00715690. Values are preserved in their native
# write width; 32-bit floating-point constants are decoded separately below.
DEFAULT_WRITES = (
    (0x130C, 4, 0x7F7FFFFF),
    (0x1310, 4, 0x7F7FFFFF),
    (0x12F4, 4, 0),
    (0x48, 1, 0),
    (0x12FC, 1, 0),
    (0x1300, 4, 0),
    (0x12F8, 4, 1),
    (0x1388, 4, 1),
    (0x34, 4, 1),
    (0x38, 4, 2),
    (0x3C, 4, 3),
    (0x40, 4, 4),
    (0x2C, 4, 0x40C00000),
    (0x64, 1, 0),
    (0x30, 4, 0x408A0000),
    (0x68, 4, 0),
    (0x6C, 4, 0),
    (0x5C, 4, 0x3F80A3D7),
    (0x70, 4, 0),
    (0x74, 4, 0),
    (0x60, 4, 0x3F7D70A4),
    (0x18, 4, 0),
    (0x1C, 4, 0),
    (0x88, 4, 0),
    (0x20, 4, 0),
    (0x8C, 4, 0),
    (0x24, 4, 0),
    (0x90, 4, 0),
    (0xAD8, 1, 0),
    (0xADC, 4, 0),
    (0xB0, 4, 0x68),
    (0xB4, 4, 0x34),
    (0xB8, 4, 3),
    (0xBC, 4, 0x40),
    (0xAC, 4, 1),
    (0x14, 1, 0),
    (0x15, 1, 0),
    (0xD0, 4, 0),
    (0xD4, 4, 0),
    (0x138C, 4, 0),
    (0x1390, 4, 0),
    (SOURCE_RECORD_COUNT_OFFSET, 4, 0),
    (META_RECORD_COUNT_OFFSET, 4, 0),
    (META_REBUILD_FLAG_OFFSET, 1, 1),
)

_FLOAT_DEFAULT_BITS = {
    0x130C: 0x7F7FFFFF,
    0x1310: 0x7F7FFFFF,
    0x2C: 0x40C00000,
    0x30: 0x408A0000,
    0x5C: 0x3F80A3D7,
    0x60: 0x3F7D70A4,
}


def _f32(bits: int) -> float:
    return struct.unpack("<f", struct.pack("<I", bits))[0]


def reflected_field_index() -> dict[str, dict[str, Any]]:
    """Return a detached name-indexed copy of the 30 direct reflected fields."""
    return {row["name"]: dict(row) for row in REFLECTED_FIELDS}


def constructor_default_writes() -> list[dict[str, int | float]]:
    """Return direct constructor clears plus FUN_00715690 reset writes."""
    rows: list[dict[str, int | float]] = []
    for offset, width, raw in (*CONSTRUCTOR_PRESET_WRITES, *DEFAULT_WRITES):
        row: dict[str, int | float] = {
            "offset": offset,
            "width": width,
            "raw_value": raw,
        }
        if offset in _FLOAT_DEFAULT_BITS:
            row["float_value"] = _f32(_FLOAT_DEFAULT_BITS[offset])
        rows.append(row)
    return rows


def reflected_constructor_defaults() -> dict[str, int | float]:
    """Join constructor writes onto reflected fields without inventing types."""
    writes = {offset: (width, raw) for offset, width, raw in DEFAULT_WRITES}
    out: dict[str, int | float] = {}
    for field in REFLECTED_FIELDS:
        offset = int(field["offset"])
        write = writes.get(offset)
        if write is None:
            continue
        _, raw = write
        if offset in _FLOAT_DEFAULT_BITS:
            out[str(field["name"])] = _f32(raw)
        else:
            out[str(field["name"])] = raw
    return out


def describe_meta_section_storage() -> dict[str, Any]:
    """Describe the source/derived record lifecycle recovered at +0x1394."""
    return {
        "source_records": {
            "pointer_offset": SOURCE_RECORD_PTR_OFFSET,
            "count_offset": SOURCE_RECORD_COUNT_OFFSET,
            "stride": SOURCE_RECORD_STRIDE,
            "meta_index_offset": 0x14,
        },
        "meta_records": {
            "pointer_offset": META_RECORD_PTR_OFFSET,
            "count_offset": META_RECORD_COUNT_OFFSET,
            "stride": META_RECORD_STRIDE,
            "source_index_offset": 0x4,
            "secondary_index_offset": 0x8,
            "range_start_offset": 0xC,
            "range_end_offset": 0x10,
        },
        "rebuild_flag_offset": META_REBUILD_FLAG_OFFSET,
        "rebuild_flag_default": 1,
        "clear_function": "FUN_0071dbf0",
        "rebuild_function": "FUN_0071dc90",
        "boundary": (
            "The 0x0c/0x10 meta-record floats are computed by recovered helper "
            "calls; this contract does not assign names beyond range_start/end."
        ),
    }


def describe_ai_database_runtime() -> dict[str, Any]:
    """Return the source/PE-backed AIDatabase structural contract."""
    return {
        "format": FORMAT,
        "version": 1,
        "class_name": CLASS_NAME,
        "identity": {
            "rtti_descriptor": RTTI_DESCRIPTOR,
            "reflection_metadata": REFLECTION_METADATA,
            "reflection_builder": REFLECTION_BUILDER,
            "constructor": CONSTRUCTOR,
            "destructor": DESTRUCTOR,
            "default_initializer": DEFAULT_INITIALIZER,
            "vtable": VTABLE,
        },
        "singleton": {
            "address": SINGLETON_ADDRESS,
            "initializer_address": SINGLETON_INITIALIZER,
            "storage": "static",
        },
        "direct_reflected_field_count": len(REFLECTED_FIELDS),
        "direct_reflected_fields": [dict(row) for row in REFLECTED_FIELDS],
        "constructor_preset_writes": [
            {"offset": offset, "width": width, "raw_value": raw}
            for offset, width, raw in CONSTRUCTOR_PRESET_WRITES
        ],
        "constructor_default_writes": constructor_default_writes(),
        "reflected_constructor_defaults": reflected_constructor_defaults(),
        "meta_section_storage": describe_meta_section_storage(),
        "evidence_boundary": (
            "Identity, direct reflection layout, constructor writes and record "
            "storage are recovered. Gameplay meaning for unreflected members "
            "and helper-call results is not inferred."
        ),
    }
