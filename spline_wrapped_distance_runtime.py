"""Pure wrapped-distance arithmetic extracted from FUN_00813750."""

from __future__ import annotations

import math
from typing import Any, Sequence

FORMAT = "SHIFT.SplineWrappedDistanceRuntime/1"
PERIOD = 8.0


def _abs_int(value: float) -> int:
    """Match (x ^ (x >> 31)) - (x >> 31) from the source."""
    integer = int(float(value))
    return abs(integer)


def wrapped_y(value: float, wrap_index: float) -> float:
    return float(value) - float(_abs_int(wrap_index)) * PERIOD


def wrapped_distance(
    point_a: Sequence[float],
    wrap_a: float,
    point_b: Sequence[float],
    wrap_b: float,
) -> dict[str, Any]:
    """Reproduce the distance expression repeatedly used by FUN_00813750."""
    if len(point_a) != 3 or len(point_b) != 3:
        raise ValueError("point_a and point_b require three values")
    a = [float(v) for v in point_a]
    b = [float(v) for v in point_b]
    ay = wrapped_y(a[1], wrap_a)
    by = wrapped_y(b[1], wrap_b)
    dx = a[0] - b[0]
    dy = ay - by
    dz = a[2] - b[2]
    squared = dx * dx + dy * dy + dz * dz
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "wrapped-distance",
        "corrected_points": {
            "a": [a[0], ay, a[2]],
            "b": [b[0], by, b[2]],
        },
        "delta": [dx, dy, dz],
        "squared": squared,
        "distance": math.sqrt(squared),
        "wrap_period": PERIOD,
        "evidence": {
            "function": "FUN_00813750",
            "y_expression": "value - abs(int(wrap_index)) * 8.0",
        },
    }


def accumulate_distance(
    *,
    accumulator: float,
    point_a: Sequence[float],
    wrap_a: float,
    point_b: Sequence[float],
    wrap_b: float,
    scale: float = 1.0,
) -> dict[str, Any]:
    """Expose the exact accumulator += sqrt(...) * scale pattern."""
    measurement = wrapped_distance(point_a, wrap_a, point_b, wrap_b)
    result = float(accumulator) + measurement["distance"] * float(scale)
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "accumulate-distance",
        "before": float(accumulator),
        "distance": measurement["distance"],
        "scale": float(scale),
        "after": result,
        "evidence": {
            "function": "FUN_00813750",
            "accumulation": "accumulator + distance * scale",
        },
    }
