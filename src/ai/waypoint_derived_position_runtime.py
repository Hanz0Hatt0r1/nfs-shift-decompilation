"""Source-backed WayPointBase derived query-position pass.

This reconstructs retail FUN_007ade00, the first geometry pass called over each
WayPointBase by FUN_00719ea0 before FUN_007ada70.
"""
from __future__ import annotations

import struct
from typing import Any

from waypoint_base_runtime import POSITION_OFFSET, SIZE
from waypoint_path_query_runtime import QUERY_POSITION_OFFSET

FORMAT = "SHIFT.WayPointDerivedPositionRuntime/1"

FUNCTION = "FUN_007ade00"
FUNCTION_ADDRESS = 0x007ADE00
BATCH_CALLER = "FUN_00719ea0"
SECOND_GEOMETRY_PASS = "FUN_007ada70"

PERPENDICULAR_OFFSET = 0x1C
DRY_LAT_OFFSET = 0x48
WET_LAT_OFFSET = 0x4C
DERIVED_LATERAL_OFFSET = 0x138

VECTOR_ADD_FUNCTION = "FUN_00432c00"
VECTOR_SCALE_FUNCTION = "FUN_004368e0"


def _f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


def derive_waypoint_query_position(
    *,
    position: tuple[float, float, float],
    perpendicular: tuple[float, float, float],
    dry_lat: float,
    wet_lat: float,
    blend_factor: float,
) -> dict[str, Any]:
    """Reproduce FUN_007ade00's scalar blend and vector scale/add operations."""
    factor = _f32(blend_factor)
    dry = _f32(dry_lat)
    wet = _f32(wet_lat)

    # The retail expression is evaluated before being assigned to a float local.
    lateral = _f32(
        (1.0 - float(factor)) * float(wet)
        + float(dry) * float(factor)
    )

    base = tuple(_f32(value) for value in position)
    perpendicular_f32 = tuple(_f32(value) for value in perpendicular)
    scaled = tuple(
        _f32(component * lateral)
        for component in perpendicular_f32
    )
    derived = tuple(
        _f32(base[index] + scaled[index])
        for index in range(3)
    )

    return {
        "blend_factor": factor,
        "dry_lat": dry,
        "wet_lat": wet,
        "lateral_offset": lateral,
        "position": base,
        "perpendicular": perpendicular_f32,
        "scaled_perpendicular": scaled,
        "derived_query_position": derived,
    }


def update_waypoint_derived_position(
    record: bytes | bytearray | memoryview,
    blend_factor: float,
) -> dict[str, Any]:
    """Apply FUN_007ade00 to one serialized/runtime WayPointBase record."""
    view = memoryview(record)
    if len(view) < SIZE:
        raise ValueError(f"WayPointBase record requires 0x{SIZE:x} bytes")

    position = struct.unpack_from("<fff", view, POSITION_OFFSET)
    perpendicular = struct.unpack_from("<fff", view, PERPENDICULAR_OFFSET)
    dry_lat = struct.unpack_from("<f", view, DRY_LAT_OFFSET)[0]
    wet_lat = struct.unpack_from("<f", view, WET_LAT_OFFSET)[0]

    derived = derive_waypoint_query_position(
        position=position,
        perpendicular=perpendicular,
        dry_lat=dry_lat,
        wet_lat=wet_lat,
        blend_factor=blend_factor,
    )

    blob = bytearray(view)
    struct.pack_into(
        "<f",
        blob,
        DERIVED_LATERAL_OFFSET,
        derived["lateral_offset"],
    )
    struct.pack_into(
        "<fff",
        blob,
        QUERY_POSITION_OFFSET,
        *derived["derived_query_position"],
    )

    return {
        "format": FORMAT,
        "version": 1,
        "function": FUNCTION,
        "records": bytes(blob),
        **derived,
    }


def apply_waypoint_derived_position_pass(
    records: bytes | bytearray | memoryview,
    blend_factor: float,
    *,
    count: int | None = None,
) -> dict[str, Any]:
    """Apply the FUN_00719ea0 -> FUN_007ade00 loop to a contiguous array.

    This intentionally performs only the first per-record pass. Retail
    FUN_00719ea0 subsequently calls FUN_007ada70 for every waypoint.
    """
    view = memoryview(records)
    available = len(view) // SIZE
    if count is None:
        count = available
    if count < 0 or count > available:
        raise ValueError("waypoint count exceeds provided record storage")

    blob = bytearray(view)
    updates: list[dict[str, Any]] = []
    for index in range(count):
        offset = index * SIZE
        updated = update_waypoint_derived_position(
            blob[offset:offset + SIZE],
            blend_factor,
        )
        blob[offset:offset + SIZE] = updated["records"]
        updates.append({
            "index": index,
            "record_offset": offset,
            "lateral_offset": updated["lateral_offset"],
            "derived_query_position": updated["derived_query_position"],
        })

    return {
        "format": FORMAT,
        "version": 1,
        "function": FUNCTION,
        "batch_caller": BATCH_CALLER,
        "count": count,
        "blend_factor": _f32(blend_factor),
        "records": bytes(blob),
        "updates": updates,
    }


def describe_waypoint_derived_position_runtime() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "function": FUNCTION,
        "function_address": FUNCTION_ADDRESS,
        "batch_caller": BATCH_CALLER,
        "record_stride": SIZE,
        "inputs": {
            "position_offset": POSITION_OFFSET,
            "perpendicular_offset": PERPENDICULAR_OFFSET,
            "dry_lat_offset": DRY_LAT_OFFSET,
            "wet_lat_offset": WET_LAT_OFFSET,
            "blend_factor": "function argument",
        },
        "outputs": {
            "derived_lateral_offset": DERIVED_LATERAL_OFFSET,
            "derived_query_position_offset": QUERY_POSITION_OFFSET,
        },
        "formula": {
            "lateral": "(1-factor)*WetLat + factor*DryLat",
            "derived_query_position": "Position + Perpendicular*lateral",
        },
        "vector_helpers": {
            "scale": VECTOR_SCALE_FUNCTION,
            "add": VECTOR_ADD_FUNCTION,
        },
        "caller_order": {
            "first_pass": FUNCTION,
            "second_pass": SECOND_GEOMETRY_PASS,
        },
        "evidence_boundary": (
            "Only FUN_007ade00 and its array loop are implemented here. "
            "FUN_007ada70's link-dependent direction, distance and curvature "
            "outputs remain a separate second geometry pass."
        ),
    }
