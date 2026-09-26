"""Base spline runtime primitives recovered from FUN_00813500..FUN_00813710."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.SplineBasePrimitivesRuntime/1"
WRAP_PERIOD = 8.0
CURSOR_SNAPSHOT_DWORD_COUNT = 25
CURSOR_DWORD_COUNT = 26
CURSOR_INDEX_OFFSET = 0x64


@dataclass(frozen=True)
class SplineCursorState:
    """25-dword cursor/object snapshot used by FUN_008136d0/13710."""
    words: tuple[Any, ...]
    segment_index: int

    def __post_init__(self) -> None:
        if len(self.words) != CURSOR_DWORD_COUNT:
            raise ValueError("cursor words require exactly 25 dwords")


def describe_spline_object_destroy() -> dict[str, Any]:
    """Reproduce FUN_00813500 destructor/reset ordering."""
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "spline-object-destroy",
        "actions": [
            {"action": "write vtable", "value": "PTR_FUN_00b15d08"},
            {"action": "FUN_00688010", "target": "+0x2c"},
            {"action": "FUN_006310c0", "target": "+0xdc"},
            {"action": "FUN_006310c0", "target": "+0xd4"},
            {"action": "FUN_006310c0", "target": "+0xcc"},
            {"action": "FUN_006310c0", "target": "+0x60"},
            {"action": "FUN_004f0050", "target": "+0x2c"},
            {"action": "FUN_006383f0"},
        ],
        "evidence": {"function": "FUN_00813500"},
    }


def sample_spline_slot(
    *,
    source_slot: int,
    resolved_words: Sequence[Any],
) -> dict[str, Any]:
    """Trace FUN_00813550's slot selector and cursor normalization."""
    if int(source_slot) not in (0, 1):
        raise ValueError("source_slot must be 0 or 1")
    if len(resolved_words) != CURSOR_SNAPSHOT_DWORD_COUNT:
        raise ValueError("resolved_words requires exactly 25 snapshot dwords")
    words = list(resolved_words) + [0]
    words[CURSOR_INDEX_OFFSET // 4] = 0
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "sample-spline-slot",
        "status": "resolved",
        "source_slot": int(source_slot),
        "words": words,
        "forced_local_index": 0,
        "evidence": {
            "function": "FUN_00813550",
            "source_pointer": f"this + {int(source_slot) * 4:#x}",
            "snapshot_size": 0x64,
        },
    }


def interpolate_spline_position(
    *,
    first_position: Sequence[float],
    second_position: Sequence[float],
    first_wrap: int,
    second_wrap: int,
    factor: float,
) -> dict[str, Any]:
    """Reproduce FUN_008135b0's two-sample linear position blend."""
    if len(first_position) != 3 or len(second_position) != 3:
        raise ValueError("positions require three values")
    t = float(factor)
    f = 1.0 - t
    a = [float(v) for v in first_position]
    b = [float(v) for v in second_position]
    corrected_a_y = a[1] - float(int(first_wrap)) * WRAP_PERIOD
    corrected_b_y = b[1] - float(int(second_wrap)) * WRAP_PERIOD
    result = [
        f * a[0] + t * b[0],
        f * corrected_a_y + t * corrected_b_y,
        f * a[2] + t * b[2],
    ]
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "spline-position-interpolation",
        "factor": t,
        "first_position": [a[0], corrected_a_y, a[2]],
        "second_position": [b[0], corrected_b_y, b[2]],
        "result": result,
        "evidence": {
            "function": "FUN_008135b0",
            "wrap_period": WRAP_PERIOD,
            "blend": "first*(1-factor) + second*factor",
        },
    }


def advance_spline_cursor(
    *,
    cursor_words: Sequence[Any],
    current_segment_index: int,
    next_segment_index: int,
    direction: str,
    wrap_helper_changed: bool,
) -> dict[str, Any]:
    """Trace FUN_008136d0/FUN_00813710 cursor copy and index update."""
    if len(cursor_words) != CURSOR_DWORD_COUNT:
        raise ValueError("cursor_words requires exactly 26 dwords")
    if direction not in ("forward", "backward"):
        raise ValueError("direction must be forward or backward")

    words = list(cursor_words)
    if direction == "forward":
        updated = int(current_segment_index) + 1
        helper = "FUN_007025a0"
        if int(current_segment_index) == 0 and wrap_helper_changed:
            # Source returns early after helper-induced wrap.
            return {
                "format": FORMAT,
                "version": 1,
                "operation": "cursor-advance",
                "status": "helper-wrapped",
                "words": words,
                "segment_index": updated,
                "helper": helper,
            }
    else:
        updated = int(current_segment_index) - 1
        helper = "FUN_00702580"
        if int(current_segment_index) == 0 and wrap_helper_changed:
            return {
                "format": FORMAT,
                "version": 1,
                "operation": "cursor-advance",
                "status": "helper-wrapped",
                "words": words,
                "segment_index": updated,
                "helper": helper,
            }

    words[CURSOR_INDEX_OFFSET // 4] = updated
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "cursor-advance",
        "status": "advanced",
        "words": words,
        "segment_index": updated,
        "helper": helper,
        "evidence": {
            "function": "FUN_008136d0" if direction == "forward" else "FUN_00813710",
            "index_offset": "+0x64",
        },
    }
