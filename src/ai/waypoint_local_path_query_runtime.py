"""Source-backed AIDatabase linked local waypoint query.

This reconstructs retail FUN_00718d00 over an already link-resolved
WayPointBase array. The routine performs a local prev/next search around a
caller-supplied waypoint and falls back to FUN_007189a0 at specific boundaries.
"""
from __future__ import annotations

import operator
import struct
from typing import Any

from waypoint_base_runtime import (
    BRANCH_ID_OFFSET,
    BRANCH_LINK_OFFSET,
    NEXT_LINK_OFFSET,
    PREV_LINK_OFFSET,
    SIZE,
)
from waypoint_path_query_runtime import (
    ORIENTATION_X_OFFSET,
    ORIENTATION_Z_OFFSET,
    QUERY_POSITION_OFFSET,
    orientation_switch_dot,
    select_nearest_path_waypoint,
)

FORMAT = "SHIFT.WayPointLocalPathQueryRuntime/1"

FUNCTION = "FUN_00718d00"
FUNCTION_ADDRESS = 0x00718D00
GLOBAL_FALLBACK_FUNCTION = "FUN_007189a0"

NULL_CURRENT_FALLBACK_CALL = 0x00718D1C
BRANCH_REDIRECT_BLOCK = 0x00718D29
PREVIOUS_SCAN_BLOCK = 0x00718D50
NEXT_SCAN_BLOCK = 0x00718E4B
FINAL_ORIENTATION_BLOCK = 0x00718F14
GLOBAL_FALLBACK_BLOCK = 0x00718F6E


def _f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


def local_query_distance_sq(
    point: tuple[float, float, float],
    record_position: tuple[float, float, float],
) -> float:
    """Reproduce FUN_00718d00's ordinary 3D squared-distance metric."""
    px, py, pz = (_f32(value) for value in point)
    rx, ry, rz = (_f32(value) for value in record_position)
    dx = _f32(px - rx)
    dy = _f32(py - ry)
    dz = _f32(pz - rz)
    score = float(dx) * float(dx)
    score += float(dy) * float(dy)
    score += float(dz) * float(dz)
    return _f32(score)


def _read_fields(
    records: memoryview,
    index: int,
) -> dict[str, Any]:
    offset = index * SIZE
    qx, qy, qz = struct.unpack_from("<fff", records, offset + QUERY_POSITION_OFFSET)
    return {
        "index": index,
        "record_offset": offset,
        "query_position": (qx, qy, qz),
        "branch_id": struct.unpack_from("<i", records, offset + BRANCH_ID_OFFSET)[0],
        "prev_pointer": struct.unpack_from("<I", records, offset + PREV_LINK_OFFSET)[0],
        "next_pointer": struct.unpack_from("<I", records, offset + NEXT_LINK_OFFSET)[0],
        "branch_pointer": struct.unpack_from("<I", records, offset + BRANCH_LINK_OFFSET)[0],
        "orientation_x": struct.unpack_from("<f", records, offset + ORIENTATION_X_OFFSET)[0],
        "orientation_z": struct.unpack_from("<f", records, offset + ORIENTATION_Z_OFFSET)[0],
    }


def _strict_pointer_to_index(
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


def _returned_pointer_index(
    pointer: int | None,
    *,
    base_address: int,
    count: int,
) -> int | None:
    if pointer is None or pointer == 0 or pointer < base_address:
        return None
    delta = pointer - base_address
    if delta % SIZE:
        return None
    index = delta // SIZE
    return index if 0 <= index < count else None


def _validate_branch_selector(branch_id: int) -> int:
    selector = operator.index(branch_id)
    if not -0x80000000 <= selector <= 0x7FFFFFFF:
        raise ValueError("branch selector must fit signed int32")
    return selector


def select_local_path_waypoint(
    records: bytes | bytearray | memoryview,
    point: tuple[float, float, float],
    *,
    current_pointer: int | None,
    branch_id: int,
    advance_forward: bool = False,
    count: int | None = None,
    base_address: int,
) -> dict[str, Any] | None:
    """Reproduce retail FUN_00718d00 over a bounded WayPointBase array.

    Traversed prev/next/branch pointers are dereferenced by the retail routine.
    This bounded reconstruction therefore rejects non-null traversal pointers
    that do not identify a record inside the supplied logical array instead of
    emulating arbitrary process-memory reads.
    """
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

    selector = _validate_branch_selector(branch_id)
    start_pointer = int(current_pointer or 0)
    backward_visited: list[int] = []
    forward_visited: list[int] = []

    def fallback(reason: str) -> dict[str, Any] | None:
        result = select_nearest_path_waypoint(
            view,
            point,
            branch_id=selector,
            count=count,
            base_address=base_address,
        )
        if result is None:
            return None
        return {
            "format": FORMAT,
            "version": 1,
            "function": FUNCTION,
            "strategy": "global-fallback",
            "fallback_function": GLOBAL_FALLBACK_FUNCTION,
            "fallback_reason": reason,
            "branch_selector": selector,
            "start_pointer": start_pointer,
            "backward_visited": list(backward_visited),
            "forward_visited": list(forward_visited),
            "returned_pointer": result["returned_pointer"],
            "returned_index": result["returned_index"],
            "global_query": result,
        }

    if start_pointer == 0:
        return fallback("null-current")

    start_index = _strict_pointer_to_index(
        start_pointer,
        base_address=base_address,
        count=count,
        role="current",
    )
    assert start_index is not None
    start_fields = _read_fields(view, start_index)
    branch_redirected = False
    branch_redirect_from = start_index

    if start_fields["branch_id"] != selector and start_fields["branch_pointer"] != 0:
        branch_index = _strict_pointer_to_index(
            int(start_fields["branch_pointer"]),
            base_address=base_address,
            count=count,
            role="branch",
        )
        assert branch_index is not None
        branch_fields = _read_fields(view, branch_index)
        if branch_fields["branch_id"] == selector:
            start_index = branch_index
            start_fields = branch_fields
            branch_redirected = True

    best_index = start_index
    best_fields = start_fields
    best_distance = local_query_distance_sq(point, start_fields["query_position"])

    # Backward search. A matching, closer previous record is only committed
    # after its own previous pointer is known to be non-null, matching the
    # source's fallback when a decreasing chain terminates.
    prev_pointer = int(start_fields["prev_pointer"])
    if prev_pointer:
        prev_index = _strict_pointer_to_index(
            prev_pointer,
            base_address=base_address,
            count=count,
            role="previous",
        )
        assert prev_index is not None
        prev_fields = _read_fields(view, prev_index)
        prev_distance = local_query_distance_sq(point, prev_fields["query_position"])

        if prev_distance < best_distance:
            while True:
                backward_visited.append(prev_index)
                if prev_fields["branch_id"] != selector:
                    break

                next_prev_pointer = int(prev_fields["prev_pointer"])
                if next_prev_pointer == 0:
                    return fallback("previous-chain-ended")

                next_prev_index = _strict_pointer_to_index(
                    next_prev_pointer,
                    base_address=base_address,
                    count=count,
                    role="previous",
                )
                assert next_prev_index is not None
                next_prev_fields = _read_fields(view, next_prev_index)
                next_prev_distance = local_query_distance_sq(
                    point,
                    next_prev_fields["query_position"],
                )

                best_index = prev_index
                best_fields = prev_fields
                best_distance = prev_distance

                if not next_prev_distance < prev_distance:
                    break
                prev_index = next_prev_index
                prev_fields = next_prev_fields
                prev_distance = next_prev_distance

    # Forward search always starts from the (possibly branch-redirected) anchor,
    # not from the best record found by the backward pass.
    next_pointer = int(start_fields["next_pointer"])
    if next_pointer:
        next_index = _strict_pointer_to_index(
            next_pointer,
            base_address=base_address,
            count=count,
            role="next",
        )
        assert next_index is not None
        next_fields = _read_fields(view, next_index)
        next_distance = local_query_distance_sq(point, next_fields["query_position"])

        if next_distance < best_distance:
            while True:
                forward_visited.append(next_index)
                best_index = next_index
                best_fields = next_fields
                best_distance = next_distance

                following_pointer = int(next_fields["next_pointer"])
                if following_pointer == 0:
                    return fallback("next-chain-ended")

                following_index = _strict_pointer_to_index(
                    following_pointer,
                    base_address=base_address,
                    count=count,
                    role="next",
                )
                assert following_index is not None
                following_fields = _read_fields(view, following_index)
                following_distance = local_query_distance_sq(
                    point,
                    following_fields["query_position"],
                )

                if not following_distance < next_distance:
                    break
                next_index = following_index
                next_fields = following_fields
                next_distance = following_distance

    orientation_dot = None
    advanced_after_orientation = False
    returned_pointer = base_address + best_index * SIZE

    if advance_forward:
        orientation_dot = orientation_switch_dot(
            point,
            best_fields["query_position"],
            best_fields["orientation_x"],
            best_fields["orientation_z"],
        )
        final_next_pointer = int(best_fields["next_pointer"])
        if orientation_dot < 0.0 and final_next_pointer != 0:
            returned_pointer = final_next_pointer
            advanced_after_orientation = True

    return {
        "format": FORMAT,
        "version": 1,
        "function": FUNCTION,
        "strategy": "local",
        "branch_selector": selector,
        "start_pointer": start_pointer,
        "start_index": branch_redirect_from,
        "search_anchor_index": start_index,
        "branch_redirected": branch_redirected,
        "backward_visited": backward_visited,
        "forward_visited": forward_visited,
        "selected_index": best_index,
        "selected_pointer": base_address + best_index * SIZE,
        "selected_distance_sq": best_distance,
        "advance_forward": bool(advance_forward),
        "orientation_dot": orientation_dot,
        "advanced_after_orientation": advanced_after_orientation,
        "returned_pointer": returned_pointer,
        "returned_index": _returned_pointer_index(
            returned_pointer,
            base_address=base_address,
            count=count,
        ),
    }


def describe_waypoint_local_path_query_runtime() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "function": FUNCTION,
        "function_address": FUNCTION_ADDRESS,
        "global_fallback_function": GLOBAL_FALLBACK_FUNCTION,
        "record_stride": SIZE,
        "fields": {
            "derived_position_offset": QUERY_POSITION_OFFSET,
            "branch_id_offset": BRANCH_ID_OFFSET,
            "previous_link_offset": PREV_LINK_OFFSET,
            "next_link_offset": NEXT_LINK_OFFSET,
            "branch_link_offset": BRANCH_LINK_OFFSET,
            "orientation_x_offset": ORIENTATION_X_OFFSET,
            "orientation_z_offset": ORIENTATION_Z_OFFSET,
        },
        "metric": {
            "expression": "dx^2 + dy^2 + dz^2",
            "single_precision_delta_and_result_boundaries": True,
        },
        "blocks": {
            "null_current_fallback_call": NULL_CURRENT_FALLBACK_CALL,
            "branch_redirect": BRANCH_REDIRECT_BLOCK,
            "previous_scan": PREVIOUS_SCAN_BLOCK,
            "next_scan": NEXT_SCAN_BLOCK,
            "final_orientation": FINAL_ORIENTATION_BLOCK,
            "global_fallback": GLOBAL_FALLBACK_BLOCK,
        },
        "source_rules": {
            "branch_redirect": (
                "when anchor Branch ID differs, use +0x184 only if that target "
                "has the requested Branch ID"
            ),
            "previous_scan": (
                "walk +0x17c while distance strictly decreases and each "
                "accepted previous record matches the requested Branch ID"
            ),
            "next_scan": (
                "from the anchor +0x180, walk while distance strictly decreases; "
                "the source does not apply a Branch-ID check in this forward loop"
            ),
            "terminal_decreasing_chain": (
                "a null link reached after entering a decreasing prev/next walk "
                "falls back to FUN_007189a0"
            ),
            "final_orientation": (
                "when the flag is nonzero and dot < 0, advance to +0x180 only "
                "when that next pointer is non-null"
            ),
        },
        "evidence_boundary": (
            "The local branch redirect, Euclidean metric, linked hill-climb, "
            "orientation adjustment and exact global-fallback boundaries are "
            "recovered from retail x86. Traversal is modeled only inside the "
            "supplied contiguous waypoint array."
        ),
    }
