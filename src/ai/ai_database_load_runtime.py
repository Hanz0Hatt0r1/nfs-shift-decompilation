"""Source-backed AIDatabase AIW load/reset lifecycle.

Recovered primarily from FUN_00720190 with the section-generation path through
FUN_0071f850 / FUN_0071dc90. The contract preserves control flow, offsets,
strides and helper ordering without emulating the unrecovered serializers.
"""
from __future__ import annotations

import struct
from typing import Any

from ai_database_runtime import (
    DEFAULT_INITIALIZER,
    META_RECORD_COUNT_OFFSET,
    META_RECORD_PTR_OFFSET,
    META_RECORD_STRIDE,
    META_REBUILD_FLAG_OFFSET,
    SOURCE_RECORD_COUNT_OFFSET,
    SOURCE_RECORD_PTR_OFFSET,
    SOURCE_RECORD_STRIDE,
)

FORMAT = "SHIFT.AIDatabaseLoadRuntime/1"

LOAD_FUNCTION = "FUN_00720190"
PERSISTENT_LOAD_HELPER = "FUN_007200b0"
PRE_LOAD_CLEANUP_HELPER = "FUN_0071e3b0"
FALLBACK_OPEN_HELPER = "FUN_0074d140"
META_FILE_LOAD_HELPER = "FUN_0071fd60"
SECTION_BUILD_FUNCTION = "FUN_0071f850"
META_REBUILD_FUNCTION = "FUN_0071dc90"

DATABASE_PATH_OBJECT_OFFSET = 0x44
DATABASE_PATH_OVERRIDE_FLAG_OFFSET = 0x48
LOAD_STATE_OFFSET = 0x12F8
CURRENT_ADJUST_OFFSET = 0x4C

WAYPOINT_COUNT_OFFSET = 0x68
WAYPOINT_PTR_OFFSET = 0x70
WAYPOINT_STRIDE = 0x1BC
WAYPOINT_CLASSIFICATION_OFFSET = 0x6C
WAYPOINT_LINK_NEXT_OFFSET = 0x180

DEFAULT_DATABASE_PATH_GLOBAL = "DAT_00c13420"
META_FILE_PATH_GLOBAL = "DAT_00c13424"

# Writes performed by FUN_00720190 after FUN_00715690. Width is retained
# because +0x28/+0x29/+0x2a/+0xd8/+0x1374 are byte stores.
LOAD_PRESET_WRITES = (
    (0x10, 4, 0xBF800000),
    (0x78, 4, 0x40400000),
    (0x7C, 4, 0x3F800000),
    (0x80, 4, 0x40000000),
    (0x50, 4, 0x3F000000),
    (WAYPOINT_COUNT_OFFSET, 4, 0),
    (WAYPOINT_PTR_OFFSET, 4, 0),
    (0x74, 4, 0),
    (0x54, 4, 0x3F800000),
    (0x18, 4, 0),
    (0x1C, 4, 0),
    (0x58, 4, 0x3FA66666),
    (0xB0, 4, 0x68),
    (0xB4, 4, 0x34),
    (0x2C, 4, 0x40C00000),
    (0xB8, 4, 3),
    (0xBC, 4, 0x40),
    (0x30, 4, 0x408A0000),
    (0xAC, 4, 1),
    (0x2A, 1, 0),
    (0x88, 4, 0xBF800000),
    (0xD8, 1, 0),
    (0x1374, 1, 0),
    (0x84, 4, 0),
    (0x134C, 4, 0),
    (0x1350, 4, 0),
    (0x133C, 4, 0x4B189680),
    (LOAD_STATE_OFFSET, 4, 1),
    (0x28, 1, 0),
    (0x29, 1, 0),
)

_FLOAT_PRESET_OFFSETS = {
    0x10,
    0x78,
    0x7C,
    0x80,
    0x50,
    0x54,
    0x58,
    0x2C,
    0x30,
    0x88,
}


def _f32(bits: int) -> float:
    return struct.unpack("<f", struct.pack("<I", bits))[0]


def aiw_load_preset_writes() -> list[dict[str, int | float]]:
    """Return FUN_00720190's post-reset writes with decoded f32 values."""
    out: list[dict[str, int | float]] = []
    for offset, width, raw in LOAD_PRESET_WRITES:
        row: dict[str, int | float] = {
            "offset": offset,
            "width": width,
            "raw_value": raw,
        }
        if offset in _FLOAT_PRESET_OFFSETS:
            row["float_value"] = _f32(raw)
        out.append(row)
    return out


def derive_generated_meta_flag(meta_file_loaded: bool) -> int:
    """Reproduce FUN_00720190's +0x13a4 = !FUN_0071fd60(...) assignment."""
    return 0 if bool(meta_file_loaded) else 1


def describe_waypoint_post_load_passes() -> list[dict[str, Any]]:
    """Return the three ordered whole-array passes after the AIW load path."""
    return [
        {
            "function": "FUN_007ada70",
            "record_stride": WAYPOINT_STRIDE,
            "arguments": ["waypoint"],
        },
        {
            "function": "FUN_007ad940",
            "record_stride": WAYPOINT_STRIDE,
            "arguments": ["waypoint"],
        },
        {
            "function": "FUN_007acef0",
            "record_stride": WAYPOINT_STRIDE,
            "arguments": ["waypoint", f"waypoint+0x{WAYPOINT_LINK_NEXT_OFFSET:x}"],
        },
    ]


def build_aiw_load_trace(
    *,
    persistent_load_succeeded: bool,
    fallback_open_succeeded: bool = False,
    fallback_resource_present: bool = False,
    meta_file_loaded: bool = False,
) -> dict[str, Any]:
    """Model only the source-proven branch/control state of FUN_00720190.

    Parser internals and waypoint contents are deliberately not synthesized.
    """
    actions: list[dict[str, Any]] = [
        {"action": "reset", "function": DEFAULT_INITIALIZER},
        {"action": "apply-load-preset", "function": LOAD_FUNCTION},
        {
            "action": "default-database-path-if-not-overridden",
            "path_object_offset": DATABASE_PATH_OBJECT_OFFSET,
            "override_flag_offset": DATABASE_PATH_OVERRIDE_FLAG_OFFSET,
            "source_global": DEFAULT_DATABASE_PATH_GLOBAL,
        },
        {"action": "pre-load-cleanup", "function": PRE_LOAD_CLEANUP_HELPER},
        {
            "action": "persistent-load",
            "function": PERSISTENT_LOAD_HELPER,
            "succeeded": bool(persistent_load_succeeded),
        },
    ]

    status = "loaded-persistent"
    if not persistent_load_succeeded:
        actions.append({
            "action": "fallback-open",
            "function": FALLBACK_OPEN_HELPER,
            "succeeded": bool(fallback_open_succeeded),
            "failure_log": "Unable to open AIW %s",
        })
        if not fallback_open_succeeded:
            actions.extend([
                {
                    "action": "write-load-state",
                    "offset": LOAD_STATE_OFFSET,
                    "value": 0,
                },
                {"action": "post-failure-cleanup", "function": PRE_LOAD_CLEANUP_HELPER},
            ])
            return {
                "format": FORMAT,
                "version": 1,
                "status": "failed-open",
                "actions": actions,
                "post_load_waypoint_passes": [],
                "generated_meta_flag": None,
            }

        actions.append({
            "action": "fallback-post-open-cleanup",
            "function": PRE_LOAD_CLEANUP_HELPER,
        })
        if fallback_resource_present:
            actions.append({
                "action": "fallback-resource-activation",
                "function": "FUN_007490f0",
                "argument": 1,
            })
        status = "loaded-fallback"

    actions.extend([
        {
            "action": "current-adjust-from-mid-adjust",
            "destination_offset": CURRENT_ADJUST_OFFSET,
            "source_offset": 0x54,
        },
        {
            "action": "waypoint-post-load-passes",
            "count_offset": WAYPOINT_COUNT_OFFSET,
            "pointer_offset": WAYPOINT_PTR_OFFSET,
            "record_stride": WAYPOINT_STRIDE,
        },
        {
            "action": "count-classification-zero-waypoints",
            "record_field_offset": WAYPOINT_CLASSIFICATION_OFFSET,
            "destination_offset": 0x6C,
        },
        {
            "action": "load-meta-file",
            "function": META_FILE_LOAD_HELPER,
            "path_global": META_FILE_PATH_GLOBAL,
            "succeeded": bool(meta_file_loaded),
        },
        {
            "action": "write-generated-meta-flag",
            "offset": META_REBUILD_FLAG_OFFSET,
            "value": derive_generated_meta_flag(meta_file_loaded),
        },
    ])
    return {
        "format": FORMAT,
        "version": 1,
        "status": status,
        "actions": actions,
        "post_load_waypoint_passes": describe_waypoint_post_load_passes(),
        "generated_meta_flag": derive_generated_meta_flag(meta_file_loaded),
    }


def describe_section_generation_lifecycle() -> dict[str, Any]:
    """Describe source-section construction and derived meta-section fallback."""
    return {
        "builder": SECTION_BUILD_FUNCTION,
        "source_records": {
            "pointer_offset": SOURCE_RECORD_PTR_OFFSET,
            "count_offset": SOURCE_RECORD_COUNT_OFFSET,
            "stride": SOURCE_RECORD_STRIDE,
            "constructor": "FUN_00702a10",
            "materializer": "FUN_00702a40",
        },
        "generated_meta_records": {
            "function": META_REBUILD_FUNCTION,
            "pointer_offset": META_RECORD_PTR_OFFSET,
            "count_offset": META_RECORD_COUNT_OFFSET,
            "stride": META_RECORD_STRIDE,
        },
        "generation_condition": {
            "flag_offset": META_REBUILD_FLAG_OFFSET,
            "generated_when": 1,
            "external_meta_loaded_when": 0,
        },
        "evidence": {
            "invalid_generated_section_log": (
                "Invalid meta section %u %.0fm:%.0fm for track %s - "
                "no corners/straights contained!"
            ),
            "source_file": ".\\Source\\AI\\ai_db.cpp",
        },
        "boundary": (
            "The source-record and generated-meta layouts/strides are proven; "
            "the meaning of all individual record members is not."
        ),
    }


def describe_ai_database_load_runtime() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "load_function": LOAD_FUNCTION,
        "load_state_offset": LOAD_STATE_OFFSET,
        "database_path": {
            "object_offset": DATABASE_PATH_OBJECT_OFFSET,
            "override_flag_offset": DATABASE_PATH_OVERRIDE_FLAG_OFFSET,
            "default_global": DEFAULT_DATABASE_PATH_GLOBAL,
        },
        "waypoints": {
            "count_offset": WAYPOINT_COUNT_OFFSET,
            "pointer_offset": WAYPOINT_PTR_OFFSET,
            "stride": WAYPOINT_STRIDE,
            "classification_offset": WAYPOINT_CLASSIFICATION_OFFSET,
            "next_link_offset": WAYPOINT_LINK_NEXT_OFFSET,
        },
        "load_preset_writes": aiw_load_preset_writes(),
        "post_load_waypoint_passes": describe_waypoint_post_load_passes(),
        "section_generation": describe_section_generation_lifecycle(),
        "evidence_boundary": (
            "This contract reconstructs load/reset control flow and storage "
            "topology. It does not implement the AIW parser or waypoint math."
        ),
    }
