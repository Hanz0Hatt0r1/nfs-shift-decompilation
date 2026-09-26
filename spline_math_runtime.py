"""Exact TrackingCamera spline math from FUN_00821870/21890/218b0.

21870 and 21890 are boundary predicates over a scalar interpolation factor and
an integer frame/index range. 218b0 evaluates the exact four-coefficient cubic
polynomial visible in the decompiler.
"""

from __future__ import annotations

from typing import Any

FORMAT = "SHIFT.SplineMathRuntime/1"


def spline_start_gate(*, factor: float, index: int) -> dict[str, Any]:
    """Reproduce FUN_00821870."""
    blocked = float(factor) != 0.0 and int(index) >= 0
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "spline-start-gate",
        "blocked": blocked,
        "result": 0 if blocked else 1,
        "condition": "(+0x0c != 0) and (+0x10 >= 0)",
        "evidence": {"function": "FUN_00821870"},
    }


def spline_end_gate(*, factor: float, index: int, count: int) -> dict[str, Any]:
    """Reproduce FUN_00821890."""
    blocked = float(factor) != 1.0 and int(index) <= int(count) - 2
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "spline-end-gate",
        "blocked": blocked,
        "result": 0 if blocked else 1,
        "condition": "(+0x0c != 1) and (+0x10 <= +0x14 - 2)",
        "evidence": {"function": "FUN_00821890"},
    }


def cubic_interpolate(
    *,
    coefficient_a: float,
    coefficient_b: float,
    coefficient_c: float,
    coefficient_d: float,
    t: float,
) -> float:
    """Reproduce the polynomial in FUN_008218b0 exactly."""
    p1 = float(coefficient_a)
    p2 = float(coefficient_b)
    p3 = float(coefficient_c)
    p4 = float(coefficient_d)
    x = float(t)
    x2 = x * x
    x3 = x2 * x
    return (
        (x3 - x2) * 0.5 * p4
        + ((x2 * 4.0 + x) - x3 * 3.0) * 0.5 * p3
        + ((x2 * 2.0 - x) - x3) * 0.5 * p1
        + ((2.0 - x2 * 5.0) + x3 * 3.0) * 0.5 * p2
    )


def describe_cubic_interpolation(
    *,
    coefficients: tuple[float, float, float, float],
    t: float,
) -> dict[str, Any]:
    if len(coefficients) != 4:
        raise ValueError("coefficients requires exactly four values")
    value = cubic_interpolate(
        coefficient_a=coefficients[0],
        coefficient_b=coefficients[1],
        coefficient_c=coefficients[2],
        coefficient_d=coefficients[3],
        t=t,
    )
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "cubic-interpolation",
        "coefficients": list(map(float, coefficients)),
        "t": float(t),
        "value": value,
        "evidence": {
            "function": "FUN_008218b0",
            "powers": ["t", "t^2", "t^3"],
        },
    }
