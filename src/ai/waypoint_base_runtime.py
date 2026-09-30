"""Source-backed WayPointBase layout and nearest-waypoint query primitives."""
from __future__ import annotations

import struct
from typing import Any

FORMAT = "SHIFT.WayPointBaseRuntime/1"

CLASS_NAME = "WayPointBase"
RTTI_DESCRIPTOR = 0x00C1C21C
RTTI_GETTER = 0x00715C70
VTABLE = 0x00B0CAD8
REGISTRATION_FUNCTION = "FUN_00a8c470"
REFLECTION_METADATA = "DAT_00b8d7bc"
REFLECTION_BUILDER = "FUN_007acfc0"
CONSTRUCTOR = "FUN_007ae5d0"
DESTRUCTOR = "FUN_007ad680"

SIZE = 0x1BC
POSITION_OFFSET = 0x10
BRANCH_ID_OFFSET = 0x6C
PREV_INDEX_OFFSET = 0x74
NEXT_INDEX_OFFSET = 0x78
BRANCH_INDEX_OFFSET = 0x7C
PREV_LINK_OFFSET = 0x17C
NEXT_LINK_OFFSET = 0x180
BRANCH_LINK_OFFSET = 0x184
ACTIVE_MARKER_OFFSET = 0x18E

LINK_RESOLUTION_FUNCTION = "FUN_00717b90"
LINK_RESOLUTION_CALLERS = ("FUN_0071e3ba", "FUN_0071f099")
NEAREST_BRANCH_ZERO_FUNCTION = "FUN_00718060"
NEAREST_BRANCH_ONE_FUNCTION = "FUN_00718120"

REFLECTED_FIELDS = (
    {
        "name": "Position",
        "offset": 0x10,
        "type_code": 0x10,
        "flags": 3,
        "description": "Position of waypoint always dead center of track.(maybe)",
    },
    {
        "name": "Perpendicular",
        "offset": 0x1C,
        "type_code": 0x10,
        "flags": 3,
        "description": "Perpendicular vector (positive to right)",
    },
    {
        "name": "Road Left/Right",
        "offset": 0x28,
        "type_code": 0x0F,
        "flags": 3,
        "description": "Width of road to left/right",
    },
    {
        "name": "Far Left/Right",
        "offset": 0x30,
        "type_code": 0x0F,
        "flags": 3,
        "description": "Farthest left/right we can go",
    },
    {
        "name": "Coll Left/Right",
        "offset": 0x38,
        "type_code": 0x0F,
        "flags": 3,
        "description": "Left/right edge of no-collision corridor",
    },
    {
        "name": "Cut Left/Right",
        "offset": 0x40,
        "type_code": 0x0F,
        "flags": 3,
        "description": "Offset from road left/right to set cut corridor",
    },
    {
        "name": "Dry Lat",
        "offset": 0x48,
        "type_code": 10,
        "flags": 3,
        "description": "Is defined as dry optimal path",
    },
    {
        "name": "Wet Lat",
        "offset": 0x4C,
        "type_code": 10,
        "flags": 3,
        "description": "Is defined as wet optimal path",
    },
    {
        "name": "Groove Alpha",
        "offset": 0x50,
        "type_code": 10,
        "flags": 3,
        "description": "Alpha of translucent groove polygon",
    },
    {
        "name": "Sector",
        "offset": 0x54,
        "type_code": 0x0D,
        "flags": 3,
        "description": "Which sector this waypoint follows",
    },
    {
        "name": "Lap Distance",
        "offset": 0x58,
        "type_code": 10,
        "flags": 3,
        "description": "Distance into lap (0.0 at start/finish)",
    },
    {
        "name": "Groove Lat",
        "offset": 0x5C,
        "type_code": 10,
        "flags": 3,
        "description": "Lateral offset so groove doesn't go over grass",
    },
    {
        "name": "Corner Speed Mult",
        "offset": 0x60,
        "type_code": 10,
        "flags": 3,
        "description": "Fraction of calculated speed to take corner",
    },
    {
        "name": "Event Type",
        "offset": 0x64,
        "type_code": 0x0D,
        "flags": 3,
        "description": "Event type",
    },
    {
        "name": "Event Speed Fraction",
        "offset": 0x68,
        "type_code": 10,
        "flags": 3,
        "description": "Event MPS",
    },
    {
        "name": "Branch ID",
        "offset": 0x6C,
        "type_code": 0x0D,
        "flags": 3,
        "description": "Branch id (pitstop or slot pit)",
    },
    {
        "name": "BitFields",
        "offset": 0x70,
        "type_code": 0x0D,
        "flags": 3,
        "description": "Bit fields",
    },
    {
        "name": "Prev Index",
        "offset": 0x74,
        "type_code": 0x0D,
        "flags": 3,
        "description": "Index to previous waypoint",
    },
    {
        "name": "Next Index",
        "offset": 0x78,
        "type_code": 0x0D,
        "flags": 3,
        "description": "Index to next waypoint",
    },
    {
        "name": "Branch Index",
        "offset": 0x7C,
        "type_code": 0x0D,
        "flags": 3,
        "description": "Index to branched waypoint",
    },
)

# Direct constructor writes that overlap reflected members. Fields omitted from
# this table are not assumed to have a constructor default.
REFLECTED_CONSTRUCTOR_DEFAULTS = {
    "Position": (0.0, 0.0, 0.0),
    "Perpendicular": (0.0, 0.0, 0.0),
    "Road Left/Right": (0.0, 0.0),
    "Far Left/Right": (0.0, 0.0),
    "Coll Left/Right": (0.0, 0.0),
    "Cut Left/Right": (0.0, 0.0),
    "Dry Lat": 0.0,
    "Wet Lat": 0.0,
    "Lap Distance": 0.0,
    "Groove Lat": 0.0,
    "Corner Speed Mult": 1.0,
    "Branch ID": -1,
    "BitFields": 0,
    "Prev Index": -1,
    "Next Index": -1,
    "Branch Index": -1,
}


def reflected_field_index() -> dict[str, dict[str, Any]]:
    return {row["name"]: dict(row) for row in REFLECTED_FIELDS}


def decode_query_fields(record: bytes | bytearray | memoryview) -> dict[str, Any]:
    """Decode only the fields consumed by FUN_00718060/FUN_00718120."""
    view = memoryview(record)
    if len(view) < SIZE:
        raise ValueError(f"WayPointBase record requires 0x{SIZE:x} bytes")
    x, y, z = struct.unpack_from("<fff", view, POSITION_OFFSET)
    branch_id = struct.unpack_from("<i", view, BRANCH_ID_OFFSET)[0]
    active_marker = struct.unpack_from("<H", view, ACTIVE_MARKER_OFFSET)[0]
    return {
        "position": (x, y, z),
        "branch_id": branch_id,
        "active_marker": active_marker,
    }


def decode_link_fields(record: bytes | bytearray | memoryview) -> dict[str, Any]:
    """Decode the index/pointer members consumed or written by FUN_00717b90."""
    view = memoryview(record)
    if len(view) < SIZE:
        raise ValueError(f"WayPointBase record requires 0x{SIZE:x} bytes")
    return {
        "active_marker": struct.unpack_from("<H", view, ACTIVE_MARKER_OFFSET)[0],
        "prev_index": struct.unpack_from("<i", view, PREV_INDEX_OFFSET)[0],
        "next_index": struct.unpack_from("<i", view, NEXT_INDEX_OFFSET)[0],
        "branch_index": struct.unpack_from("<i", view, BRANCH_INDEX_OFFSET)[0],
        "prev_link": struct.unpack_from("<I", view, PREV_LINK_OFFSET)[0],
        "next_link": struct.unpack_from("<I", view, NEXT_LINK_OFFSET)[0],
        "branch_link": struct.unpack_from("<I", view, BRANCH_LINK_OFFSET)[0],
    }


_LINK_SPECS = (
    ("prev", PREV_INDEX_OFFSET, PREV_LINK_OFFSET),
    ("next", NEXT_INDEX_OFFSET, NEXT_LINK_OFFSET),
    ("branch", BRANCH_INDEX_OFFSET, BRANCH_LINK_OFFSET),
)


def resolve_waypoint_links(
    records: bytes | bytearray | memoryview,
    *,
    base_address: int,
    count: int | None = None,
) -> dict[str, Any]:
    """Reproduce FUN_00717b90's index-to-pointer resolution over one array.

    The retail function only special-cases -1 and indices >= count. A value
    below -1 would address memory before the waypoint array, so this recovered
    helper rejects such malformed input instead of emulating an out-of-bounds
    read.
    """
    if not 0 < int(base_address) <= 0xFFFFFFFF:
        raise ValueError("base_address must be a non-zero 32-bit address")

    view = memoryview(records)
    available = len(view) // SIZE
    if count is None:
        count = available
    if count < 0 or count > available:
        raise ValueError("waypoint count exceeds provided record storage")

    blob = bytearray(view)
    decisions: list[dict[str, Any]] = []
    for source_index in range(count):
        source_offset = source_index * SIZE
        active_marker = struct.unpack_from(
            "<H", blob, source_offset + ACTIVE_MARKER_OFFSET
        )[0]
        source_row = {
            "source_index": source_index,
            "source_offset": source_offset,
            "source_address": int(base_address) + source_offset,
            "active_marker": active_marker,
            "processed": active_marker != 0,
            "links": {},
        }

        if active_marker == 0:
            decisions.append(source_row)
            continue

        for name, index_offset, pointer_offset in _LINK_SPECS:
            index_address = source_offset + index_offset
            pointer_address = source_offset + pointer_offset
            target_index = struct.unpack_from("<i", blob, index_address)[0]

            if target_index < -1:
                raise ValueError(
                    f"{name} index {target_index} is below the retail -1 sentinel"
                )

            valid = target_index != -1 and target_index < count
            target_active_marker = None
            target_pointer = 0
            reason = "sentinel" if target_index == -1 else "out-of-range"

            if valid:
                target_offset = target_index * SIZE
                target_active_marker = struct.unpack_from(
                    "<H", blob, target_offset + ACTIVE_MARKER_OFFSET
                )[0]
                if target_active_marker != 0:
                    target_pointer = int(base_address) + target_offset
                    if target_pointer > 0xFFFFFFFF:
                        raise ValueError("resolved waypoint pointer exceeds 32 bits")
                    reason = "resolved"
                else:
                    valid = False
                    reason = "inactive-target"

            if valid:
                struct.pack_into("<I", blob, pointer_address, target_pointer)
            else:
                struct.pack_into("<I", blob, pointer_address, 0)
                struct.pack_into("<i", blob, index_address, -1)

            source_row["links"][name] = {
                "input_index": target_index,
                "output_index": (
                    target_index if valid else -1
                ),
                "target_active_marker": target_active_marker,
                "pointer": target_pointer if valid else 0,
                "reason": reason,
            }

        decisions.append(source_row)

    return {
        "records": bytes(blob),
        "base_address": int(base_address),
        "count": count,
        "decisions": decisions,
    }


def nearest_active_waypoint(
    records: bytes | bytearray | memoryview,
    point: tuple[float, float, float],
    *,
    branch_id: int,
    count: int | None = None,
    base_address: int = 0,
) -> dict[str, Any] | None:
    """Reproduce the simple nearest-record loop used for branch IDs 0/1.

    This intentionally models the Euclidean-squared queries only; it is not the
    more complex FUN_007189a0 path-selection metric.
    """
    view = memoryview(records)
    available = len(view) // SIZE
    if count is None:
        count = available
    if count < 0 or count > available:
        raise ValueError("waypoint count exceeds provided record storage")

    best: dict[str, Any] | None = None
    best_distance_sq = 1.0e37
    px, py, pz = (float(point[0]), float(point[1]), float(point[2]))
    for index in range(count):
        offset = index * SIZE
        row = decode_query_fields(view[offset:offset + SIZE])
        if row["branch_id"] != int(branch_id) or row["active_marker"] == 0:
            continue
        x, y, z = row["position"]
        dx, dy, dz = px - x, py - y, pz - z
        distance_sq = dx * dx + dy * dy + dz * dz
        if distance_sq < best_distance_sq:
            best_distance_sq = distance_sq
            best = {
                "index": index,
                "record_offset": offset,
                "address": base_address + offset if base_address else None,
                "distance_sq": distance_sq,
                **row,
            }
    return best


def nearest_branch_zero_waypoint(
    records: bytes | bytearray | memoryview,
    point: tuple[float, float, float],
    *,
    count: int | None = None,
    base_address: int = 0,
) -> dict[str, Any] | None:
    """FUN_00718060 equivalent over captured/decoded record bytes."""
    return nearest_active_waypoint(
        records,
        point,
        branch_id=0,
        count=count,
        base_address=base_address,
    )


def nearest_branch_one_waypoint(
    records: bytes | bytearray | memoryview,
    point: tuple[float, float, float],
    *,
    count: int | None = None,
    base_address: int = 0,
) -> dict[str, Any] | None:
    """FUN_00718120 equivalent over captured/decoded record bytes."""
    return nearest_active_waypoint(
        records,
        point,
        branch_id=1,
        count=count,
        base_address=base_address,
    )


def describe_waypoint_base_runtime() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "class_name": CLASS_NAME,
        "identity": {
            "rtti_descriptor": RTTI_DESCRIPTOR,
            "rtti_getter": RTTI_GETTER,
            "vtable": VTABLE,
            "registration_function": REGISTRATION_FUNCTION,
            "reflection_metadata": REFLECTION_METADATA,
            "reflection_builder": REFLECTION_BUILDER,
            "constructor": CONSTRUCTOR,
            "destructor": DESTRUCTOR,
        },
        "size": SIZE,
        "direct_reflected_field_count": len(REFLECTED_FIELDS),
        "direct_reflected_fields": [dict(row) for row in REFLECTED_FIELDS],
        "reflected_constructor_defaults": dict(REFLECTED_CONSTRUCTOR_DEFAULTS),
        "link_resolution": {
            "function": LINK_RESOLUTION_FUNCTION,
            "callers": list(LINK_RESOLUTION_CALLERS),
            "active_marker_offset": ACTIVE_MARKER_OFFSET,
            "index_offsets": {
                "prev": PREV_INDEX_OFFSET,
                "next": NEXT_INDEX_OFFSET,
                "branch": BRANCH_INDEX_OFFSET,
            },
            "pointer_offsets": {
                "prev": PREV_LINK_OFFSET,
                "next": NEXT_LINK_OFFSET,
                "branch": BRANCH_LINK_OFFSET,
            },
            "invalid_index_sentinel": -1,
        },
        "query_fields": {
            "position_offset": POSITION_OFFSET,
            "branch_id_offset": BRANCH_ID_OFFSET,
            "active_marker_offset": ACTIVE_MARKER_OFFSET,
            "next_link_offset": NEXT_LINK_OFFSET,
        },
        "query_functions": {
            "branch_zero": NEAREST_BRANCH_ZERO_FUNCTION,
            "branch_one": NEAREST_BRANCH_ONE_FUNCTION,
        },
        "evidence_boundary": (
            "The class identity, 0x1bc element size, direct reflected layout, "
            "index-to-pointer link resolution and two simple nearest-record "
            "queries are recovered. The active marker and other unreflected "
            "record members keep structural names only."
        ),
    }
