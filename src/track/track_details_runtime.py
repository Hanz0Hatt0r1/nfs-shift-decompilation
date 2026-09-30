"""Source-backed TrackDetails runtime layout and constructor contract."""
from __future__ import annotations

import struct
from typing import Any

FORMAT = "SHIFT.TrackDetailsRuntime/1"

CLASS_NAME = "TrackDetails"
PARENT_CLASS = "BPersistent"
PARENT_DESCRIPTOR = 0x00BFA608
RTTI_DESCRIPTOR = 0x00BCCE48
RTTI_GETTER = 0x0049BCE0
VTABLE = 0x00ABB208
REGISTRATION_FUNCTION = "FUN_00a78170"
REFLECTION_METADATA = "DAT_00b81eb0"
REFLECTION_BUILDER = "FUN_00d67c70"
REFLECTION_BUILDER_ALIASES = ("FUN_00d67c70", "thunk_FUN_00d67c70")
CONSTRUCTOR = "FUN_0049b9c0"
DESTRUCTOR = "FUN_0049bf00"
DESTRUCTOR_BODY = "FUN_0049bd10"
ALLOCATION_ENTRY = "FUN_0049ef40"
ALLOCATION_CONTINUATION = "FUN_0049ef4d"
ALLOCATION_COLD_STUB = 0x00432446
ALLOCATOR = "FUN_008868c0"

SIZE = 0x1D4

REFLECTED_FIELDS = (
    {"name": "ScenegraphFile", "offset": 0x20, "type_code": 0x0, "flags": 3},
    {"name": "LeaderboardID", "offset": 0x34, "type_code": 0xD, "flags": 3},
    {"name": "Length", "offset": 0x38, "type_code": 0xD, "flags": 3},
    {"name": "XLASTID", "offset": 0x3C, "type_code": 0x3, "flags": 3},
    {"name": "TrackName", "offset": 0x40, "type_code": 0x0, "flags": 3},
    {"name": "ShortTrackName", "offset": 0x44, "type_code": 0x0, "flags": 3},
    {"name": "Track_Location", "offset": 0x48, "type_code": 0x0, "flags": 3},
    {"name": "Track_Variation", "offset": 0x4C, "type_code": 0x0, "flags": 3},
    {"name": "Location", "offset": 0x50, "type_code": 0x0, "flags": 3},
    {"name": "Track Type", "offset": 0xA0, "type_code": 0x0, "flags": 3},
    {"name": "Allowed Weather", "offset": 0x110, "type_code": 0x0, "flags": 3},
    {"name": "Allowed TimeOfDay", "offset": 0x114, "type_code": 0x0, "flags": 3},
    {"name": "Event Types", "offset": 0x118, "type_code": 0x0, "flags": 3},
    {"name": "Track Description", "offset": 0x11C, "type_code": 0x0, "flags": 3},
    {"name": "Year", "offset": 0x124, "type_code": 0xD, "flags": 3},
    {"name": "Sun Angle(DEG)", "offset": 0x128, "type_code": 0x1, "flags": 3},
    {"name": "Track Surface", "offset": 0x12C, "type_code": 0x0, "flags": 3},
    {"name": "Track Group", "offset": 0x130, "type_code": 0x0, "flags": 3},
    {
        "name": "PreRace Allowed (true/false)",
        "offset": 0x134,
        "type_code": 0x2,
        "flags": 3,
    },
    {"name": "Max AI participants", "offset": 0x138, "type_code": 0x3, "flags": 3},
    {"name": "Class", "offset": 0x13C, "type_code": 0x0, "flags": 3},
    {"name": "DirtSkidmarks", "offset": 0x164, "type_code": 0x0, "flags": 3},
    {"name": "DrySkidmarks", "offset": 0x168, "type_code": 0x0, "flags": 3},
    {"name": "GrassSkidmarks", "offset": 0x16C, "type_code": 0x0, "flags": 3},
    {"name": "GravelSkidmarks", "offset": 0x170, "type_code": 0x0, "flags": 3},
    {"name": "SandSkidmarks", "offset": 0x174, "type_code": 0x0, "flags": 3},
    {
        "name": "GravelDustParticles",
        "offset": 0x178,
        "type_code": 0x0,
        "flags": 3,
    },
    {
        "name": "GravelChunkParticles",
        "offset": 0x17C,
        "type_code": 0x0,
        "flags": 3,
    },
    {"name": "GrassParticles", "offset": 0x180, "type_code": 0x0, "flags": 3},
    {"name": "AutograssMaterial", "offset": 0x184, "type_code": 0x0, "flags": 3},
    {"name": "AutograssDensities", "offset": 0x188, "type_code": 0x0, "flags": 3},
    {"name": "AutograssHeights", "offset": 0x18C, "type_code": 0x0, "flags": 3},
    {"name": "AI Grip", "offset": 0x190, "type_code": 0xA, "flags": 3},
    {"name": "AI drift score min", "offset": 0x198, "type_code": 0x3, "flags": 3},
    {"name": "AI drift score max", "offset": 0x19C, "type_code": 0x3, "flags": 3},
    {"name": "Rolling Start", "offset": 0x1A0, "type_code": 0x2, "flags": 3},
    {"name": "Setup group", "offset": 0x1A4, "type_code": 0x0, "flags": 3},
    {"name": "ZoneName", "offset": 0x1A8, "type_code": 0x0, "flags": 3},
    {"name": "Post race position", "offset": 0x1AC, "type_code": 0x10, "flags": 3},
    {
        "name": "Post race orientation",
        "offset": 0x1B8,
        "type_code": 0x10,
        "flags": 3,
    },
    {"name": "Post race steering", "offset": 0x1C4, "type_code": 0xA, "flags": 3},
    {
        "name": "Time Attack duration short",
        "offset": 0x1C8,
        "type_code": 0x3,
        "flags": 3,
    },
    {
        "name": "Time Attack duration medium",
        "offset": 0x1CC,
        "type_code": 0x3,
        "flags": 3,
    },
    {
        "name": "Time Attack duration long",
        "offset": 0x1D0,
        "type_code": 0x3,
        "flags": 3,
    },
)

STRING_INITIALIZER = "FUN_00533e70"
STRING_ASSIGNMENT_HELPER = "FUN_006329e0"
STRING_INITIALIZED_FIELDS = tuple(
    row["name"] for row in REFLECTED_FIELDS if row["type_code"] == 0
)
CONSTRUCTOR_STRING_ASSIGNMENTS = {"Class": "All"}

# Direct scalar/vector writes visible in FUN_0049b9c0. Fields not listed here
# are intentionally not assigned a default merely from reflection metadata.
REFLECTED_CONSTRUCTOR_DEFAULTS = {
    "LeaderboardID": -1,
    "Length": -1,
    "Year": 0,
    "Sun Angle(DEG)": 0.0,
    "PreRace Allowed (true/false)": 0,
    "Max AI participants": 15,
    "AI Grip": 1.0,
    "AI drift score min": 400,
    "AI drift score max": 4000,
    "Rolling Start": 0,
    "Post race position": (0.0, 0.0, 0.0),
    "Post race orientation": (0.0, 0.0, 0.0),
    "Post race steering": 0.0,
    "Time Attack duration short": 5,
    "Time Attack duration medium": 10,
    "Time Attack duration long": 20,
}

_NUMERIC_DECODE = (
    ("leaderboard_id", 0x34, "<i"),
    ("length_raw", 0x38, "<i"),
    ("xlastid", 0x3C, "<i"),
    ("year", 0x124, "<i"),
    ("sun_angle_deg", 0x128, "<f"),
    ("pre_race_allowed_raw", 0x134, "<I"),
    ("max_ai_participants", 0x138, "<i"),
    ("ai_grip", 0x190, "<f"),
    ("ai_drift_score_min", 0x198, "<i"),
    ("ai_drift_score_max", 0x19C, "<i"),
    ("rolling_start_raw", 0x1A0, "<I"),
    ("post_race_steering", 0x1C4, "<f"),
    ("time_attack_duration_short", 0x1C8, "<i"),
    ("time_attack_duration_medium", 0x1CC, "<i"),
    ("time_attack_duration_long", 0x1D0, "<i"),
)


def reflected_field_index() -> dict[str, dict[str, Any]]:
    """Return a detached name-indexed copy of the direct reflected layout."""
    return {str(row["name"]): dict(row) for row in REFLECTED_FIELDS}


def decode_numeric_fields(record: bytes | bytearray | memoryview) -> dict[str, Any]:
    """Decode only embedded primitive/vector fields with source-backed offsets."""
    view = memoryview(record)
    if len(view) < SIZE:
        raise ValueError(f"TrackDetails record requires 0x{SIZE:x} bytes")

    out: dict[str, Any] = {}
    for name, offset, fmt in _NUMERIC_DECODE:
        out[name] = struct.unpack_from(fmt, view, offset)[0]
    out["post_race_position"] = struct.unpack_from("<fff", view, 0x1AC)
    out["post_race_orientation"] = struct.unpack_from("<fff", view, 0x1B8)
    return out


def describe_track_details_runtime() -> dict[str, Any]:
    """Return the source/PE-backed TrackDetails structural contract."""
    return {
        "format": FORMAT,
        "version": 1,
        "class_name": CLASS_NAME,
        "parent": {
            "class_name": PARENT_CLASS,
            "descriptor": PARENT_DESCRIPTOR,
        },
        "identity": {
            "rtti_descriptor": RTTI_DESCRIPTOR,
            "rtti_getter": RTTI_GETTER,
            "vtable": VTABLE,
            "registration_function": REGISTRATION_FUNCTION,
            "reflection_metadata": REFLECTION_METADATA,
            "reflection_builder": REFLECTION_BUILDER,
            "reflection_builder_aliases": list(REFLECTION_BUILDER_ALIASES),
            "constructor": CONSTRUCTOR,
            "destructor": DESTRUCTOR,
            "destructor_body": DESTRUCTOR_BODY,
        },
        "allocation": {
            "entry_function": ALLOCATION_ENTRY,
            "continuation_function": ALLOCATION_CONTINUATION,
            "cold_stub_address": ALLOCATION_COLD_STUB,
            "allocator": ALLOCATOR,
            "exact_size": SIZE,
            "proof": "0x00432446 pushes 0x1d4 before FUN_008868c0",
        },
        "size": SIZE,
        "direct_reflected_field_count": len(REFLECTED_FIELDS),
        "direct_reflected_fields": [dict(row) for row in REFLECTED_FIELDS],
        "constructor": {
            "string_initializer": STRING_INITIALIZER,
            "string_initialized_fields": list(STRING_INITIALIZED_FIELDS),
            "string_assignment_helper": STRING_ASSIGNMENT_HELPER,
            "string_assignments": dict(CONSTRUCTOR_STRING_ASSIGNMENTS),
            "reflected_defaults": dict(REFLECTED_CONSTRUCTOR_DEFAULTS),
        },
        "evidence_boundary": (
            "Identity, exact allocation size, direct reflected layout and direct "
            "constructor writes are recovered. Dynamic string storage, hash/table "
            "members between reflected fields and gameplay interpretation remain "
            "outside this contract."
        ),
    }
