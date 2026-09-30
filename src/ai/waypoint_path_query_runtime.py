"""Source-backed AIDatabase nearest path-waypoint query.

This reconstructs retail FUN_007189a0 over captured/raw WayPointBase records.
The function uses an intentionally non-Euclidean score and can return the
selected record's +0x180 link based on a final X/Z orientation test.
"""
from __future__ import annotations

import operator
import struct
from typing import Any

from waypoint_base_runtime import (
    ACTIVE_MARKER_OFFSET,
    BRANCH_ID_OFFSET,
    NEXT_LINK_OFFSET,
    SIZE,
)

FORMAT = "SHIFT.WayPointPathQueryRuntime/1"

FUNCTION = "FUN_007189a0"
QUERY_POSITION_OFFSET = 0x8C
ORIENTATION_X_OFFSET = 0x13C
ORIENTATION_Z_OFFSET = 0x144
ANY_BRANCH_ID = -1

# Retail .rdata constants used by FUN_007189a0.
INITIAL_SCORE_BITS = 0x7CF0BDC2
INITIAL_SCORE = struct.unpack("<f", struct.pack("<I", INITIAL_SCORE_BITS))[0]
ORIENTATION_SWITCH_THRESHOLD_BITS = 0x00000000
ORIENTATION_SWITCH_THRESHOLD = 0.0

# PE instruction anchors for the unusual metric and final switch.
FUNCTION_ADDRESS = 0x007189A0
BRANCH_FILTER_INSTRUCTION = 0x00718A44
REMAINDER_BRANCH_FILTER_INSTRUCTION = 0x00718C6E
FINAL_ORIENTATION_BLOCK = 0x00718C9A
FINAL_THRESHOLD_COMPARE = 0x00718CD7


def _f32(value: float) -> float:
    """Round one value to the retail single-precision local/store boundary."""
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


def _read_record_fields(
    record: bytes | bytearray | memoryview,
) -> dict[str, Any]:
    view = memoryview(record)
    if len(view) < SIZE:
        raise ValueError(f"WayPointBase record requires 0x{SIZE:x} bytes")
    qx, qy, qz = struct.unpack_from("<fff", view, QUERY_POSITION_OFFSET)
    branch_id = struct.unpack_from("<i", view, BRANCH_ID_OFFSET)[0]
    active_marker = struct.unpack_from("<H", view, ACTIVE_MARKER_OFFSET)[0]
    orientation_x = struct.unpack_from("<f", view, ORIENTATION_X_OFFSET)[0]
    orientation_z = struct.unpack_from("<f", view, ORIENTATION_Z_OFFSET)[0]
    next_pointer = struct.unpack_from("<I", view, NEXT_LINK_OFFSET)[0]
    return {
        "query_position": (qx, qy, qz),
        "branch_id": branch_id,
        "active_marker": active_marker,
        "orientation_x": orientation_x,
        "orientation_z": orientation_z,
        "next_pointer": next_pointer,
    }


def path_query_score(
    point: tuple[float, float, float],
    record_position: tuple[float, float, float],
) -> float:
    """Reproduce FUN_007189a0's dx^2 + dz^2 + dy^4 score.

    x87 evaluates the products at extended precision but each input delta and
    the final score are stored through 32-bit locals. The explicit f32 rounds
    below preserve those observable boundaries.
    """
    px, py, pz = (_f32(value) for value in point)
    rx, ry, rz = (_f32(value) for value in record_position)
    dx = _f32(px - rx)
    dy = _f32(py - ry)
    dz = _f32(pz - rz)
    dy2 = float(dy) * float(dy)
    score = float(dx) * float(dx) + float(dz) * float(dz) + dy2 * dy2
    return _f32(score)


def orientation_switch_dot(
    point: tuple[float, float, float],
    record_position: tuple[float, float, float],
    orientation_x: float,
    orientation_z: float,
) -> float:
    """Reproduce the final X/Z dot product before the +0x180 link switch."""
    px, _, pz = (_f32(value) for value in point)
    rx, _, rz = (_f32(value) for value in record_position)
    dx = _f32(rx - px)
    dz = _f32(rz - pz)
    dot = float(_f32(orientation_x)) * float(dx)
    dot += float(_f32(orientation_z)) * float(dz)
    return _f32(dot)


def _pointer_to_index(
    pointer: int,
    *,
    base_address: int,
    count: int,
) -> int | None:
    if pointer == 0 or base_address == 0 or pointer < base_address:
        return None
    delta = pointer - base_address
    if delta % SIZE:
        return None
    index = delta // SIZE
    return index if 0 <= index < count else None


def select_nearest_path_waypoint(
    records: bytes | bytearray | memoryview,
    point: tuple[float, float, float],
    *,
    branch_id: int = ANY_BRANCH_ID,
    count: int | None = None,
    base_address: int = 0,
) -> dict[str, Any] | None:
    """Reproduce FUN_007189a0 over contiguous WayPointBase records.

    branch_id == -1 accepts every branch. Other values are compared as
    integers against reflected WayPointBase::Branch ID at +0x6c.

    The source return value is a pointer. This report keeps both the initially
    selected record and the final returned pointer so a +0x180 switch to null
    remains observable instead of being silently replaced by the selected row.
    """
    view = memoryview(records)
    available = len(view) // SIZE
    if count is None:
        count = available
    if count < 0 or count > available:
        raise ValueError("waypoint count exceeds provided record storage")

    selector = operator.index(branch_id)
    if not -0x80000000 <= selector <= 0x7FFFFFFF:
        raise ValueError("branch selector must fit signed int32")
    best_index: int | None = None
    best_score = INITIAL_SCORE
    best_fields: dict[str, Any] | None = None

    for index in range(count):
        offset = index * SIZE
        fields = _read_record_fields(view[offset:offset + SIZE])

        # Retail computes the score before testing the marker/branch, but those
        # rejected rows cannot update the winner. Keeping the predicates here
        # is equivalent at the externally visible result boundary.
        if fields["active_marker"] == 0:
            continue
        if selector != ANY_BRANCH_ID and fields["branch_id"] != selector:
            continue

        score = path_query_score(point, fields["query_position"])
        if score < best_score:
            best_score = score
            best_index = index
            best_fields = fields

    if best_index is None or best_fields is None:
        return None

    selected_offset = best_index * SIZE
    selected_address = (
        base_address + selected_offset if base_address else None
    )
    dot = orientation_switch_dot(
        point,
        best_fields["query_position"],
        best_fields["orientation_x"],
        best_fields["orientation_z"],
    )
    switched_to_next = dot < ORIENTATION_SWITCH_THRESHOLD

    if switched_to_next:
        returned_pointer: int | None = int(best_fields["next_pointer"])
    else:
        returned_pointer = selected_address

    return {
        "format": FORMAT,
        "version": 1,
        "function": FUNCTION,
        "branch_selector": selector,
        "selected_index": best_index,
        "selected_record_offset": selected_offset,
        "selected_address": selected_address,
        "selected_score": best_score,
        "selected_branch_id": best_fields["branch_id"],
        "selected_active_marker": best_fields["active_marker"],
        "selected_query_position": best_fields["query_position"],
        "orientation_x": best_fields["orientation_x"],
        "orientation_z": best_fields["orientation_z"],
        "orientation_dot": dot,
        "orientation_threshold": ORIENTATION_SWITCH_THRESHOLD,
        "switched_to_next": switched_to_next,
        "next_pointer": best_fields["next_pointer"],
        "returned_pointer": returned_pointer,
        "returned_index": (
            _pointer_to_index(
                returned_pointer,
                base_address=base_address,
                count=count,
            )
            if returned_pointer is not None
            else None
        ),
    }


def describe_waypoint_path_query_runtime() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "function": FUNCTION,
        "function_address": FUNCTION_ADDRESS,
        "record_stride": SIZE,
        "scan_fields": {
            "query_position_offset": QUERY_POSITION_OFFSET,
            "branch_id_offset": BRANCH_ID_OFFSET,
            "active_marker_offset": ACTIVE_MARKER_OFFSET,
        },
        "branch_selector": {
            "any_value": ANY_BRANCH_ID,
            "comparison_kind": "signed/int32",
            "instruction_addresses": [
                BRANCH_FILTER_INSTRUCTION,
                REMAINDER_BRANCH_FILTER_INSTRUCTION,
            ],
        },
        "score": {
            "expression": "dx^2 + dz^2 + dy^4",
            "initial_limit_bits": INITIAL_SCORE_BITS,
            "initial_limit": INITIAL_SCORE,
            "single_precision_local_boundaries": True,
        },
        "final_switch": {
            "orientation_x_offset": ORIENTATION_X_OFFSET,
            "orientation_z_offset": ORIENTATION_Z_OFFSET,
            "next_link_offset": NEXT_LINK_OFFSET,
            "expression": "orientation_x*(record_x-query_x) + orientation_z*(record_z-query_z)",
            "condition": "dot < 0.0",
            "threshold_bits": ORIENTATION_SWITCH_THRESHOLD_BITS,
            "block_address": FINAL_ORIENTATION_BLOCK,
            "compare_address": FINAL_THRESHOLD_COMPARE,
            "null_next_is_returned_as_null": True,
        },
        "evidence_boundary": (
            "The scan/filter/score/final-link behavior is recovered from retail "
            "x86. The semantic meaning of query-position/orientation storage "
            "at +0x8c/+0x13c/+0x144 remains intentionally structural."
        ),
    }
