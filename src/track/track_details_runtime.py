"""Source-backed TrackDetails layout, allocation and lifecycle contract.

Recovered from the retail SHIFT.exe / SHIFT.exe.c pair. This module records
only identities, reflected fields and constructor/destructor/load facts that
are directly supported by source or PE evidence.
"""
from __future__ import annotations

import struct
from typing import Any

FORMAT = "SHIFT.TrackDetailsRuntime/1"

CLASS_NAME = "TrackDetails"
RTTI_DESCRIPTOR = 0x00BCCE48
PARENT_CLASS = "BPersistent"
PARENT_DESCRIPTOR = 0x00BFA608
REFLECTION_METADATA = "DAT_00b81eb0"
REFLECTION_BUILDER = "FUN_00d67c70"
REFLECTION_BUILDER_THUNK = "thunk_FUN_00d67c70"
CONSTRUCTOR = "FUN_0049b9c0"
DESTRUCTOR = "FUN_0049bf00"
DESTRUCTOR_BODY = "FUN_0049bd10"
LOADER = "FUN_0049c050"

VTABLE = 0x00ABB208
RTTI_GETTER = 0x0049BCE0

# PE 0x00432446 pushes 0x1d4 before transferring to the allocation/load path
# at 0x0049ef4d, which calls the retail allocator and FUN_0049b9c0.
OBJECT_SIZE = 0x1D4
ALLOCATION_SIZE_STUB = 0x00432446
ALLOCATION_CONTINUATION = 0x0049EF4D
ALLOCATOR = 0x008868C0

REFLECTED_FIELDS = (
    {"name": "TrackName", "offset": 0x40, "type_code": 0, "flags": 3},
    {"name": "ShortTrackName", "offset": 0x44, "type_code": 0, "flags": 3},
    {"name": "XLASTID", "offset": 0x3C, "type_code": 3, "flags": 3},
    {"name": "ScenegraphFile", "offset": 0x20, "type_code": 0, "flags": 3},
    {"name": "Year", "offset": 0x124, "type_code": 13, "flags": 3},
    {"name": "Length", "offset": 0x38, "type_code": 13, "flags": 3},
    {"name": "Location", "offset": 0x50, "type_code": 0, "flags": 3},
    {"name": "Track Type", "offset": 0xA0, "type_code": 0, "flags": 3},
    {"name": "Allowed Weather", "offset": 0x110, "type_code": 0, "flags": 3},
    {"name": "Allowed TimeOfDay", "offset": 0x114, "type_code": 0, "flags": 3},
    {"name": "PreRace Allowed (true/false)", "offset": 0x134, "type_code": 2, "flags": 3},
    {"name": "Event Types", "offset": 0x118, "type_code": 0, "flags": 3},
    {"name": "Sun Angle(DEG)", "offset": 0x128, "type_code": 1, "flags": 3},
    {"name": "Track Surface", "offset": 0x12C, "type_code": 0, "flags": 3},
    {"name": "Track Group", "offset": 0x130, "type_code": 0, "flags": 3},
    {"name": "Track Description", "offset": 0x11C, "type_code": 0, "flags": 3},
    {"name": "LeaderboardID", "offset": 0x34, "type_code": 13, "flags": 3},
    {"name": "Max AI participants", "offset": 0x138, "type_code": 3, "flags": 3},
    {"name": "Class", "offset": 0x13C, "type_code": 0, "flags": 3},
    {"name": "DirtSkidmarks", "offset": 0x164, "type_code": 0, "flags": 3},
    {"name": "DrySkidmarks", "offset": 0x168, "type_code": 0, "flags": 3},
    {"name": "GrassSkidmarks", "offset": 0x16C, "type_code": 0, "flags": 3},
    {"name": "GravelSkidmarks", "offset": 0x170, "type_code": 0, "flags": 3},
    {"name": "SandSkidmarks", "offset": 0x174, "type_code": 0, "flags": 3},
    {"name": "GravelDustParticles", "offset": 0x178, "type_code": 0, "flags": 3},
    {"name": "GravelChunkParticles", "offset": 0x17C, "type_code": 0, "flags": 3},
    {"name": "GrassParticles", "offset": 0x180, "type_code": 0, "flags": 3},
    {"name": "Track_Location", "offset": 0x48, "type_code": 0, "flags": 3},
    {"name": "Track_Variation", "offset": 0x4C, "type_code": 0, "flags": 3},
    {"name": "AutograssMaterial", "offset": 0x184, "type_code": 0, "flags": 3},
    {"name": "AutograssDensities", "offset": 0x188, "type_code": 0, "flags": 3},
    {"name": "AutograssHeights", "offset": 0x18C, "type_code": 0, "flags": 3},
    {"name": "AI Grip", "offset": 0x190, "type_code": 10, "flags": 3},
    {"name": "AI drift score min", "offset": 0x198, "type_code": 3, "flags": 3},
    {"name": "AI drift score max", "offset": 0x19C, "type_code": 3, "flags": 3},
    {"name": "Rolling Start", "offset": 0x1A0, "type_code": 2, "flags": 3},
    {"name": "Setup group", "offset": 0x1A4, "type_code": 0, "flags": 3},
    {"name": "ZoneName", "offset": 0x1A8, "type_code": 0, "flags": 3},
    {"name": "Post race position", "offset": 0x1AC, "type_code": 16, "flags": 3},
    {"name": "Post race orientation", "offset": 0x1B8, "type_code": 16, "flags": 3},
    {"name": "Post race steering", "offset": 0x1C4, "type_code": 10, "flags": 3},
    {"name": "Time Attack duration short", "offset": 0x1C8, "type_code": 3, "flags": 3},
    {"name": "Time Attack duration medium", "offset": 0x1CC, "type_code": 3, "flags": 3},
    {"name": "Time Attack duration long", "offset": 0x1D0, "type_code": 3, "flags": 3},
)

# Direct 32-bit writes in FUN_0049b9c0, in source order. These include
# BRefCount/header and unreflected storage; no semantic names are assigned.
DIRECT_DWORD_WRITES = (
    (0x004, 0x00000000),
    (0x008, 0x00000001),
    (0x028, 0x00000000),
    (0x02C, 0x00000003),
    (0x034, 0xFFFFFFFF),
    (0x038, 0xFFFFFFFF),
    (0x05C, 0x00000010),
    (0x060, 0x00000010),
    (0x064, 0x00000000),
    (0x070, 0x00000000),
    (0x074, 0x00000000),
    (0x078, 0x00000000),
    (0x058, 0x00000000),
    (0x080, 0x00000010),
    (0x084, 0x00000010),
    (0x088, 0x00000000),
    (0x094, 0x00000000),
    (0x098, 0x00000000),
    (0x09C, 0x00000000),
    (0x07C, 0x00000000),
    (0x0A8, 0x00000010),
    (0x0AC, 0x00000010),
    (0x0B0, 0x00000000),
    (0x0BC, 0x00000000),
    (0x0C0, 0x00000000),
    (0x0C4, 0x00000000),
    (0x0A4, 0x00000000),
    (0x0CC, 0x00000010),
    (0x0D0, 0x00000010),
    (0x0D4, 0x00000000),
    (0x0E0, 0x00000000),
    (0x0E4, 0x00000000),
    (0x0E8, 0x00000000),
    (0x0C8, 0x00000000),
    (0x0F0, 0x00000010),
    (0x0F4, 0x00000010),
    (0x0F8, 0x00000000),
    (0x104, 0x00000000),
    (0x108, 0x00000000),
    (0x10C, 0x00000000),
    (0x0EC, 0x00000000),
    (0x128, 0x00000000),
    (0x124, 0x00000000),
    (0x134, 0x00000000),
    (0x138, 0x0000000F),
    (0x144, 0x00000010),
    (0x148, 0x00000010),
    (0x14C, 0x00000000),
    (0x158, 0x00000000),
    (0x15C, 0x00000000),
    (0x160, 0x00000000),
    (0x140, 0x00000000),
    (0x198, 0x00000190),
    (0x19C, 0x00000FA0),
    (0x1A0, 0x00000000),
    (0x1AC, 0x00000000),
    (0x1B0, 0x00000000),
    (0x1B4, 0x00000000),
    (0x1B8, 0x00000000),
    (0x1BC, 0x00000000),
    (0x1C0, 0x00000000),
    (0x1C4, 0x00000000),
    (0x1C8, 0x00000005),
    (0x1CC, 0x0000000A),
    (0x1D0, 0x00000014),
    (0x190, 0x3F800000),
)

# Helper calls are preserved as raw offsets because this contract does not
# infer the concrete container/string type from the decompiler's helper name.
HELPER_INITIALIZED_OFFSETS = {
    "FUN_00533e70": (
        0x00C, 0x010, 0x014, 0x018, 0x01C, 0x020, 0x024, 0x030,
        0x040, 0x044, 0x048, 0x04C, 0x050, 0x054, 0x0A0, 0x110,
        0x114, 0x118, 0x11C, 0x12C, 0x130, 0x13C, 0x164, 0x168,
        0x16C, 0x170, 0x174, 0x178, 0x17C, 0x180, 0x184, 0x188,
        0x18C, 0x194, 0x1A4, 0x1A8,
    ),
    "AptCharacterInst::GetAnimationInst": (
        0x058, 0x07C, 0x0A4, 0x0C8, 0x0EC, 0x140,
    ),
}

VECTOR_ZERO_DEFAULTS = {
    "Post race position": (0.0, 0.0, 0.0),
    "Post race orientation": (0.0, 0.0, 0.0),
}


def _f32(bits: int) -> float:
    return struct.unpack("<f", struct.pack("<I", bits & 0xFFFFFFFF))[0]


def reflected_field_index() -> dict[str, dict[str, Any]]:
    return {str(row["name"]): dict(row) for row in REFLECTED_FIELDS}


def direct_constructor_writes() -> list[dict[str, int | float]]:
    rows: list[dict[str, int | float]] = []
    for offset, raw in DIRECT_DWORD_WRITES:
        row: dict[str, int | float] = {
            "offset": offset,
            "width": 4,
            "raw_value": raw,
        }
        if offset in (0x190, 0x1C4):
            row["float_value"] = _f32(raw)
        rows.append(row)
    return rows


def reflected_constructor_defaults() -> dict[str, Any]:
    writes = {offset: raw for offset, raw in DIRECT_DWORD_WRITES}
    fields = reflected_field_index()
    out: dict[str, Any] = {}
    for name, field in fields.items():
        offset = int(field["offset"])
        if offset not in writes:
            continue
        raw = writes[offset]
        if offset in (0x190, 0x1C4):
            out[name] = _f32(raw)
        else:
            out[name] = raw
    out.update(VECTOR_ZERO_DEFAULTS)
    return out


def describe_track_details_runtime() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "class_name": CLASS_NAME,
        "identity": {
            "rtti_descriptor": RTTI_DESCRIPTOR,
            "parent_class": PARENT_CLASS,
            "parent_descriptor": PARENT_DESCRIPTOR,
            "reflection_metadata": REFLECTION_METADATA,
            "reflection_builder": REFLECTION_BUILDER,
            "reflection_builder_thunk": REFLECTION_BUILDER_THUNK,
            "constructor": CONSTRUCTOR,
            "destructor": DESTRUCTOR,
            "destructor_body": DESTRUCTOR_BODY,
            "loader": LOADER,
            "vtable": VTABLE,
            "rtti_getter": RTTI_GETTER,
        },
        "allocation": {
            "object_size": OBJECT_SIZE,
            "size_stub": ALLOCATION_SIZE_STUB,
            "continuation": ALLOCATION_CONTINUATION,
            "allocator": ALLOCATOR,
        },
        "direct_reflected_field_count": len(REFLECTED_FIELDS),
        "direct_reflected_fields": [dict(row) for row in REFLECTED_FIELDS],
        "direct_constructor_writes": direct_constructor_writes(),
        "helper_initialized_offsets": {
            name: list(offsets)
            for name, offsets in HELPER_INITIALIZED_OFFSETS.items()
        },
        "reflected_constructor_defaults": reflected_constructor_defaults(),
        "evidence_boundary": (
            "Exact class identity, 0x1d4 allocation, direct reflected layout, "
            "constructor writes and lifecycle entry points are recovered. Helper "
            "container types and higher-level track-selection semantics are not inferred."
        ),
    }
