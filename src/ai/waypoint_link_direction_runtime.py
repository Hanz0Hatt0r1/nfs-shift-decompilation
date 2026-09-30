"""Source-backed WayPointBase link-direction pass.

This reconstructs retail FUN_007ad8c0 over an already link-resolved waypoint
array. The routine prefers the runtime next link, falls back to the previous
link, and otherwise writes a fixed (0, 0, -1) vector.
"""
from __future__ import annotations

import struct
from typing import Any

from waypoint_base_runtime import (
    NEXT_LINK_OFFSET,
    POSITION_OFFSET,
    PREV_LINK_OFFSET,
    SIZE,
)

FORMAT = "SHIFT.WayPointLinkDirectionRuntime/1"

FUNCTION = "FUN_007ad8c0"
FUNCTION_ADDRESS = 0x007AD8C0
CALLERS = ("FUN_0071e3ba", "FUN_0071f099")
LINK_RESOLUTION_FUNCTION = "FUN_00717b90"
VECTOR_SUBTRACT_FUNCTION = "FUN_004a7870"

OUTPUT_DIRECTION_OFFSET = 0xF0
DEFAULT_DIRECTION = (0.0, 0.0, -1.0)


def _read_position(
    records: memoryview,
    index: int,
) -> tuple[float, float, float]:
    offset = index * SIZE + POSITION_OFFSET
    return struct.unpack_from("<fff", records, offset)


def _pointer_to_index(
    pointer: int,
    *,
    base_address: int,
    count: int,
    role: str,
) -> int | None:
    if pointer == 0:
        return None
    if pointer < base_address:
        raise ValueError(f"{role} pointer is before the modeled waypoint array")
    delta = pointer - base_address
    if delta % SIZE:
        raise ValueError(f"{role} pointer is not aligned to the 0x{SIZE:x} stride")
    index = delta // SIZE
    if not 0 <= index < count:
        raise ValueError(f"{role} pointer is outside the modeled waypoint count")
    return index


def derive_waypoint_link_direction(
    records: bytes | bytearray | memoryview,
    *,
    index: int,
    base_address: int,
    count: int | None = None,
) -> dict[str, Any]:
    """Reproduce FUN_007ad8c0's source-equivalent direction choice."""
    if not 0 < int(base_address) <= 0xFFFFFFFF:
        raise ValueError("base_address must be a non-zero 32-bit address")

    view = memoryview(records)
    available = len(view) // SIZE
    if count is None:
        count = available
    if count < 0 or count > available:
        raise ValueError("waypoint count exceeds provided record storage")
    if not 0 <= int(index) < count:
        raise ValueError("waypoint index is outside the logical waypoint count")
    if count and base_address + (count - 1) * SIZE > 0xFFFFFFFF:
        raise ValueError("modeled waypoint array exceeds 32-bit address space")

    source_index = int(index)
    source_offset = source_index * SIZE
    self_position = _read_position(view, source_index)
    next_pointer = struct.unpack_from(
        "<I", view, source_offset + NEXT_LINK_OFFSET
    )[0]
    prev_pointer = struct.unpack_from(
        "<I", view, source_offset + PREV_LINK_OFFSET
    )[0]

    next_index = _pointer_to_index(
        next_pointer,
        base_address=base_address,
        count=count,
        role="next",
    )
    prev_index = None

    if next_index is not None:
        target_position = _read_position(view, next_index)
        direction = tuple(
            float(target_position[axis]) - float(self_position[axis])
            for axis in range(3)
        )
        mode = "next-minus-self"
        target_index = next_index
        target_pointer = next_pointer
    else:
        prev_index = _pointer_to_index(
            prev_pointer,
            base_address=base_address,
            count=count,
            role="previous",
        )
        if prev_index is not None:
            target_position = _read_position(view, prev_index)
            direction = tuple(
                float(self_position[axis]) - float(target_position[axis])
                for axis in range(3)
            )
            mode = "self-minus-previous"
            target_index = prev_index
            target_pointer = prev_pointer
        else:
            direction = DEFAULT_DIRECTION
            mode = "default"
            target_index = None
            target_pointer = 0

    # FUN_004a7870 is a three-float subtract helper and each result component is
    # written to the record as float32.
    direction_f32 = tuple(
        struct.unpack("<f", struct.pack("<f", value))[0]
        for value in direction
    )
    return {
        "format": FORMAT,
        "version": 1,
        "function": FUNCTION,
        "index": source_index,
        "record_offset": source_offset,
        "record_address": base_address + source_offset,
        "next_pointer": next_pointer,
        "previous_pointer": prev_pointer,
        "next_index": next_index,
        "previous_index": prev_index,
        "mode": mode,
        "target_index": target_index,
        "target_pointer": target_pointer,
        "direction": direction_f32,
    }


def update_waypoint_link_direction(
    records: bytes | bytearray | memoryview,
    *,
    index: int,
    base_address: int,
    count: int | None = None,
) -> dict[str, Any]:
    """Apply FUN_007ad8c0 to one WayPointBase inside a bounded array."""
    derived = derive_waypoint_link_direction(
        records,
        index=index,
        base_address=base_address,
        count=count,
    )
    blob = bytearray(records)
    struct.pack_into(
        "<fff",
        blob,
        derived["record_offset"] + OUTPUT_DIRECTION_OFFSET,
        *derived["direction"],
    )
    return {
        **derived,
        "records": bytes(blob),
    }


def apply_waypoint_link_direction_pass(
    records: bytes | bytearray | memoryview,
    *,
    base_address: int,
    count: int | None = None,
) -> dict[str, Any]:
    """Apply the observed post-FUN_00717b90 direction pass to each waypoint."""
    if not 0 < int(base_address) <= 0xFFFFFFFF:
        raise ValueError("base_address must be a non-zero 32-bit address")

    view = memoryview(records)
    available = len(view) // SIZE
    if count is None:
        count = available
    if count < 0 or count > available:
        raise ValueError("waypoint count exceeds provided record storage")
    if count and base_address + (count - 1) * SIZE > 0xFFFFFFFF:
        raise ValueError("modeled waypoint array exceeds 32-bit address space")

    blob = bytearray(view)
    updates: list[dict[str, Any]] = []
    for index in range(count):
        derived = derive_waypoint_link_direction(
            blob,
            index=index,
            base_address=base_address,
            count=count,
        )
        struct.pack_into(
            "<fff",
            blob,
            index * SIZE + OUTPUT_DIRECTION_OFFSET,
            *derived["direction"],
        )
        updates.append({
            key: value
            for key, value in derived.items()
            if key not in {"format", "version", "function"}
        })

    return {
        "format": FORMAT,
        "version": 1,
        "function": FUNCTION,
        "callers": list(CALLERS),
        "count": count,
        "base_address": int(base_address),
        "records": bytes(blob),
        "updates": updates,
    }


def describe_waypoint_link_direction_runtime() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "function": FUNCTION,
        "function_address": FUNCTION_ADDRESS,
        "callers": list(CALLERS),
        "required_prior_pass": LINK_RESOLUTION_FUNCTION,
        "record_stride": SIZE,
        "inputs": {
            "position_offset": POSITION_OFFSET,
            "previous_link_offset": PREV_LINK_OFFSET,
            "next_link_offset": NEXT_LINK_OFFSET,
        },
        "output_direction_offset": OUTPUT_DIRECTION_OFFSET,
        "selection_order": [
            "next.Position - self.Position",
            "self.Position - previous.Position",
            "default (0, 0, -1)",
        ],
        "vector_subtract_helper": VECTOR_SUBTRACT_FUNCTION,
        "active_marker_gate": False,
        "evidence_boundary": (
            "FUN_007ad8c0's link choice and raw three-float direction output are "
            "recovered. The semantic role of +0xf0..+0xf8 remains structural "
            "until downstream consumers establish a stronger name."
        ),
    }
