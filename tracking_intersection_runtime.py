"""Exact six-candidate intersection bound helper from FUN_0081f370.

The routine consumes four vec4-like source records (+0x00..+0x3c), a four-float
plane coefficient vector, and a three-float direction vector. It computes six
candidate scalar intersections and updates a negative/positive bound pair:
negative candidates update the lower bound by max(), non-negative candidates
update the upper bound by min().
"""

from __future__ import annotations

from typing import Any, Sequence

FORMAT = "SHIFT.TrackingIntersectionRuntime/1"


def _f(values: Sequence[float], count: int, name: str) -> tuple[float, ...]:
    if len(values) != count:
        raise ValueError(f"{name} requires exactly {count} values")
    return tuple(float(v) for v in values)


def _update_bounds(
    lower: float,
    upper: float,
    candidate: float,
) -> tuple[float, float]:
    if candidate >= 0.0:
        return lower, min(upper, candidate)
    return max(lower, candidate), upper


def compute_intersection_candidates(
    box_values: Sequence[float],
    plane: Sequence[float],
    direction: Sequence[float],
) -> list[float | None]:
    """Reproduce FUN_0081f370's six denominator/numerator candidates."""
    v = _f(box_values, 16, "box_values")
    p = _f(plane, 4, "plane")
    d = _f(direction, 3, "direction")
    x0,y0,z0,w0 = v[0:4]
    x1,y1,z1,w1 = v[4:8]
    x2,y2,z2,w2 = v[8:12]
    x3,y3,z3,w3 = v[12:16]

    candidates: list[float | None] = []

    denom = p[0]*(x1-x0) + p[1]*(y1-y0) + p[2]*(z1-z0)
    candidates.append(
        -((w3 + p[0]*(x1-x0) + p[1]*(y1-y0) + p[2]*(z1-z0)) - w2) / denom
        if denom != 0.0 else None
    )

    denom = p[0]*(x0+x1) + p[1]*(y0+y1) + p[2]*(z0+z1)
    candidates.append(
        -((x0+x1)*p[0] + (y0+y1)*p[1] + (z0+z1)*p[2] + w3 + w2) / denom
        if denom != 0.0 else None
    )

    denom = p[0]*(x3-x2) + p[1]*(y3-y2) + p[2]*(z3-z2)
    candidates.append(
        -(((x3-x2)*p[0] + (y3-y2)*p[1] + (z3-z2)*p[2] + w3) - w1) / denom
        if denom != 0.0 else None
    )

    denom = p[0]*(x2+x3) + p[1]*(y2+y3) + p[2]*(z2+z3)
    candidates.append(
        -((x2+x3)*p[0] + (y2+y3)*p[1] + (z2+z3)*p[2] + w3 + w1) / denom
        if denom != 0.0 else None
    )

    denom = p[0]*(x0-x3) + p[1]*(y0-y3) + p[2]*(z0-z3)
    candidates.append(
        -((w3 + p[1]*(y0-y3) + p[2]*(z0-z3) + p[0]*(x0-x3)) - w0) / denom
        if denom != 0.0 else None
    )

    denom = p[0]*x2 + p[1]*y2 + p[2]*z2
    candidates.append(
        -(x2*p[0] + y2*p[1] + z2*p[2] + w3) / denom
        if denom != 0.0 else None
    )

    return candidates


def intersect_and_update_bounds(
    *,
    lower_bound: float,
    upper_bound: float,
    box_values: Sequence[float],
    plane: Sequence[float],
    direction: Sequence[float],
) -> dict[str, Any]:
    """Trace candidate order plus lower/upper updates."""
    candidates = compute_intersection_candidates(box_values, plane, direction)
    lower = float(lower_bound)
    upper = float(upper_bound)
    steps = []
    for index, candidate in enumerate(candidates):
        if candidate is None:
            steps.append({
                "index": index,
                "candidate": None,
                "action": "skip-zero-denominator",
            })
            continue
        before = (lower, upper)
        lower, upper = _update_bounds(lower, upper, candidate)
        steps.append({
            "index": index,
            "candidate": candidate,
            "before": before,
            "after": (lower, upper),
            "action": "upper=min" if candidate >= 0.0 else "lower=max",
        })
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "intersection-bounds",
        "candidates": candidates,
        "lower_bound_after": lower,
        "upper_bound_after": upper,
        "steps": steps,
        "evidence": {
            "function": "FUN_0081f370",
            "candidate_count": 6,
            "box_input_floats": 16,
            "plane_input_floats": 4,
            "direction_input_floats": 3,
        },
        "limitations": [
            "the geometric meaning of the four 4-float records remains unresolved",
        ],
    }
