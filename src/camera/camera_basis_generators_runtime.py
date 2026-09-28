"""Exact 3x3 basis generators FUN_0081b400/FUN_0081b500.

The executable obtains scalar factors from FUN_00900b10 and FUN_00900c40 and
then evaluates fixed multiplication/addition expressions into nine floats.
This module takes those observed helper outputs directly; it does not infer
their underlying angle or quaternion source.
"""

from __future__ import annotations

from typing import Sequence

FORMAT = "SHIFT.CameraBasisGeneratorsRuntime/1"


def _triplet(values: Sequence[float], name: str) -> tuple[float, float, float]:
    if len(values) != 3:
        raise ValueError(f"{name} requires three values")
    return float(values[0]), float(values[1]), float(values[2])


def basis_400(
    b10_values: Sequence[float],
    c40_values: Sequence[float],
) -> list[float]:
    """Reproduce the nine assignments in FUN_0081b400."""
    f1, f2, f3 = _triplet(b10_values, "b10_values")
    c1, c2, c3 = _triplet(c40_values, "c40_values")
    f4 = -c1
    f5 = -c2
    fstack = -c3
    return [
        f2 * f3 - f5 * f4 * fstack,
        -f1 * f5,
        fstack * f3 + f4 * f2 * f5,
        f5 * f2 + f4 * f3 * fstack,
        f1 * f3,
        fstack * -f1,
        f2 * f1,
        f4,
        f2 * f1,
    ]


def basis_500(
    b10_values: Sequence[float],
    c40_values: Sequence[float],
) -> list[float]:
    """Reproduce the nine assignments in FUN_0081b500."""
    f1, f2, f3 = _triplet(b10_values, "b10_values")
    c1, c2, c3 = _triplet(c40_values, "c40_values")
    f4 = -c1
    f5 = -c2
    f6 = -c3
    return [
        f2 * f3,
        f4 * f5 * f3 - f6 * f1,
        f6 * f4 + f1 * f5 * f3,
        f6 * f2,
        f3 * f1 + f4 * f5 * f6,
        f6 * f1 * f5 - f4 * f3,
        -f5,
        f2 * f4,
        f2 * f1,
    ]


def describe_basis_generator(
    *,
    variant: str,
    b10_values: Sequence[float],
    c40_values: Sequence[float],
) -> dict:
    """Return exact source arithmetic plus opaque helper provenance."""
    key = str(variant)
    if key == "400":
        matrix = basis_400(b10_values, c40_values)
        function = "FUN_0081b400"
    elif key == "500":
        matrix = basis_500(b10_values, c40_values)
        function = "FUN_0081b500"
    else:
        raise ValueError("variant must be '400' or '500'")

    return {
        "format": FORMAT,
        "version": 1,
        "operation": "basis-generation",
        "variant": key,
        "matrix_3x3_row_major": matrix,
        "helper_inputs": {
            "FUN_00900b10": list(map(float, b10_values)),
            "FUN_00900c40": list(map(float, c40_values)),
        },
        "evidence": {
            "function": function,
            "output_count": 9,
            "output_type": "float[9]",
        },
        "limitations": [
            "FUN_00900b10/FUN_00900c40 source semantics are unresolved",
            "the matrix layout is reported as source assignment order, not given an engine-wide row/column convention",
        ],
    }
