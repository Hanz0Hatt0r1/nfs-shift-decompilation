"""StaticCamera spline movement/cursor primitives.

Recovered directly from FUN_00814670, FUN_00814690, FUN_008146e0,
FUN_00814730 and FUN_00814830.

The cursor state is the raw three-word spline position tuple:
  word0 = node/record id
  word1 = sub-index
  word2 = segment parameter

14690 moves the +direction cursor to the next segment with parameter 1.0.
146e0 moves the -direction cursor to the previous segment with parameter 0.
14730 scans backward in 0.05 parameter steps until the external candidate
score becomes positive, then commits through FUN_00813750.
14830 performs the symmetric forward scan.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

FORMAT = "SHIFT.StaticCameraSplineMovementRuntime/1"
STEP = 0.05
WRAP_PERIOD = 8.0


@dataclass(frozen=True)
class SplineCursor:
    node: int
    sub_index: int
    parameter: float


def sample_static_camera_position(
    *,
    cursor: SplineCursor,
    blend_factor: float,
    sampled_position: Sequence[float],
) -> dict:
    """Trace FUN_00814670 -> FUN_008135b0 as a sampler boundary."""
    if len(sampled_position) != 3:
        raise ValueError("sampled_position requires exactly three values")
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "sample-position",
        "status": "sampled",
        "cursor": cursor,
        "blend_factor": float(blend_factor),
        "position": list(map(float, sampled_position)),
        "action": {
            "function": "FUN_008135b0",
            "arguments": [cursor, float(blend_factor)],
        },
    }


def move_cursor_forward_segment(
    cursor: SplineCursor,
    *,
    next_node: int,
) -> tuple[SplineCursor, dict]:
    """Reproduce FUN_00814690's successful segment transition."""
    if int(next_node) == int(cursor.node):
        return cursor, {
            "format": FORMAT,
            "version": 1,
            "operation": "move-forward-segment",
            "status": "terminal",
            "result": 0,
            "action": "FUN_008136d0",
        }
    updated = SplineCursor(
        node=int(next_node),
        sub_index=int(cursor.sub_index),
        parameter=0.0,
    )
    return updated, {
        "format": FORMAT,
        "version": 1,
        "operation": "move-forward-segment",
        "status": "advanced",
        "result": 1,
        "updated": updated,
        "evidence": {
            "function": "FUN_00814690",
            "next_parameter": 0.0,
            "sub_index_behavior": "preserve current sub-index",
        },
    }


def move_cursor_backward_segment(
    cursor: SplineCursor,
    *,
    previous_node: int,
) -> tuple[SplineCursor, dict]:
    """Reproduce FUN_008146e0's successful segment transition."""
    if int(previous_node) == int(cursor.node):
        return cursor, {
            "format": FORMAT,
            "version": 1,
            "operation": "move-backward-segment",
            "status": "terminal",
            "result": 0,
            "action": "FUN_00813710",
        }
    updated = SplineCursor(
        node=int(previous_node),
        sub_index=int(cursor.sub_index),
        parameter=1.0,
    )
    return updated, {
        "format": FORMAT,
        "version": 1,
        "operation": "move-backward-segment",
        "status": "advanced",
        "result": 1,
        "updated": updated,
        "evidence": {
            "function": "FUN_008146e0",
            "next_parameter": 1.0,
            "sub_index_behavior": "preserve current sub-index",
        },
    }


def scan_backward_until_positive(
    cursor: SplineCursor,
    *,
    blend_factor: float,
    initial_score: float,
    score_at: Callable[[SplineCursor], float],
    previous_node: int | None = None,
    max_steps: int = 1000,
) -> tuple[SplineCursor, dict]:
    """Reproduce FUN_00814730's 0.05 backward scan and segment transition."""
    score = float(initial_score)
    trace = []
    if score > 0.0:
        return cursor, {
            "format": FORMAT,
            "version": 1,
            "operation": "scan-backward",
            "status": "already-positive",
            "committed": False,
            "trace": trace,
        }

    current = cursor
    last_valid = cursor
    parameter = float(cursor.parameter)
    steps = 0
    while parameter > 0.0 and steps < int(max_steps):
        position = max(0.0, parameter - STEP)
        current = SplineCursor(
            node=current.node,
            sub_index=current.sub_index,
            parameter=position,
        )
        score = float(score_at(current))
        trace.append({"cursor": current, "score": score})
        if score > 0.0:
            last_valid = current
            return last_valid, {
                "format": FORMAT,
                "version": 1,
                "operation": "scan-backward",
                "status": "found-positive",
                "committed": True,
                "trace": trace,
                "action": "FUN_00813750",
                "blend_factor": float(blend_factor),
            }
        last_valid = current
        parameter = position
        steps += 1

    if previous_node is not None:
        transitioned, transition = move_cursor_backward_segment(
            current,
            previous_node=int(previous_node),
        )
        trace.append({"segment-transition": transition})
        if transition["status"] == "advanced":
            return transitioned, {
                "format": FORMAT,
                "version": 1,
                "operation": "scan-backward",
                "status": "segment-transitioned",
                "committed": True,
                "trace": trace,
                "action": "FUN_00813750",
                "blend_factor": float(blend_factor),
            }

    return last_valid, {
        "format": FORMAT,
        "version": 1,
        "operation": "scan-backward",
        "status": "not-found",
        "committed": True,
        "trace": trace,
        "action": "FUN_00813750",
        "blend_factor": float(blend_factor),
    }


def scan_forward_until_positive(
    cursor: SplineCursor,
    *,
    initial_score: float,
    score_at: Callable[[SplineCursor], float],
    next_node: int | None = None,
    max_steps: int = 1000,
) -> tuple[SplineCursor, dict]:
    """Reproduce FUN_00814830's 0.05 forward scan and segment transition."""
    score = float(initial_score)
    trace = []
    if score > 0.0:
        return cursor, {
            "format": FORMAT,
            "version": 1,
            "operation": "scan-forward",
            "status": "already-positive",
            "committed": False,
            "trace": trace,
        }

    current = cursor
    last_valid = cursor
    parameter = float(cursor.parameter)
    steps = 0
    while parameter < 1.0 and steps < int(max_steps):
        position = min(1.0, parameter + STEP)
        current = SplineCursor(
            node=current.node,
            sub_index=current.sub_index,
            parameter=position,
        )
        score = float(score_at(current))
        trace.append({"cursor": current, "score": score})
        if score > 0.0:
            last_valid = current
            return last_valid, {
                "format": FORMAT,
                "version": 1,
                "operation": "scan-forward",
                "status": "found-positive",
                "committed": True,
                "trace": trace,
                "action": "FUN_00813750",
            }
        last_valid = current
        parameter = position
        steps += 1

    if next_node is not None:
        transitioned, transition = move_cursor_forward_segment(
            current,
            next_node=int(next_node),
        )
        trace.append({"segment-transition": transition})
        if transition["status"] == "advanced":
            return transitioned, {
                "format": FORMAT,
                "version": 1,
                "operation": "scan-forward",
                "status": "segment-transitioned",
                "committed": True,
                "trace": trace,
                "action": "FUN_00813750",
            }

    return last_valid, {
        "format": FORMAT,
        "version": 1,
        "operation": "scan-forward",
        "status": "not-found",
        "committed": True,
        "trace": trace,
        "action": "FUN_00813750",
    }


def normalize_wrapped_y(value: float, wrap_count: int) -> float:
    """The shared static-camera Y-wrap operation visible in 135b0/13750."""
    return float(value) - abs(int(wrap_count)) * WRAP_PERIOD
