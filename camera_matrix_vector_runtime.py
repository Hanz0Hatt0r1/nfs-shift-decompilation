"""Exact matrix/vector and camera input counter helpers.

Recovered from FUN_00816190, FUN_00815ff0, FUN_008167b0, FUN_00815f50 and
FUN_00815fa0.
"""

from __future__ import annotations

from typing import Any, Sequence

FORMAT = "SHIFT.CameraMatrixVectorRuntime/1"


def _need(values: Sequence[float], n: int, name: str) -> list[float]:
    if len(values) != n:
        raise ValueError(f"{name} requires exactly {n} values")
    return [float(v) for v in values]


def transform_matrix_rows_by_vector(
    matrix_4x4: Sequence[float],
    vector_4: Sequence[float],
) -> list[float]:
    """Reproduce FUN_00816190's four row assignments exactly."""
    m = _need(matrix_4x4, 16, "matrix_4x4")
    v = _need(vector_4, 4, "vector_4")
    out = [0.0] * 16
    for row in range(4):
        base = row * 4
        dot2 = 2.0 * (
            m[base + 0] * v[0]
            + m[base + 1] * v[1]
            + m[base + 2] * v[2]
            + (v[3] if row == 3 else 0.0)
        )
        out[base + 0] = m[base + 0] - dot2 * v[0]
        out[base + 1] = m[base + 1] - dot2 * v[1]
        out[base + 2] = m[base + 2] - dot2 * v[2]
        out[base + 3] = m[base + 3] - dot2 * 0.0
    return out


def build_camera_basis_matrix(
    b10_values: Sequence[float],
    c40_values: Sequence[float],
) -> list[float]:
    """Reproduce FUN_00815ff0's sparse 4x4 source-order writes."""
    a = _need(b10_values, 3, "b10_values")
    c = _need(c40_values, 3, "c40_values")
    f1, f2, f3 = a
    c1, c2, c3 = c
    f4 = -c1
    f5 = -c2
    f6 = -c3
    out = [0.0] * 16
    out[0] = f6 * f4 * f5 + f2 * f3
    out[1] = f4 * f3 * f5 - f6 * f2
    out[2] = f1 * f5
    out[4] = f6 * f1
    out[5] = f3 * f1
    out[6] = -f4
    out[8] = f4 * f2 * f6 - f5 * f3
    out[9] = f4 * f2 * f3 + f6 * f5
    out[10] = f2 * f1
    return out


def build_camera_affine_basis(
    b10_values: Sequence[float],
    c40_values: Sequence[float],
) -> list[float]:
    """Reproduce FUN_008167b0: 15ff0 followed by explicit affine defaults."""
    basis = build_camera_basis_matrix(b10_values, c40_values)
    basis[3] = 0.0
    basis[7] = 0.0
    basis[11] = 0.0
    basis[12] = 0.0
    basis[13] = 0.0
    basis[14] = 0.0
    basis[15] = 1.0
    return basis


def update_camera_signed_counter(
    current: int,
    *,
    increase: bool,
    force: bool = False,
) -> dict[str, Any]:
    """Reproduce FUN_00815f50's bounded [-10,10] counter."""
    value = int(current)
    updated = value
    changed = False
    if not increase:
        if value > -10 or force:
            updated = value - 1
            changed = True
    elif value < 10 or force:
        updated = value + 1
        changed = True
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "signed-counter-update",
        "before": value,
        "after": updated,
        "changed": changed,
        "force": bool(force),
        "increase": bool(increase),
        "evidence": {
            "function": "FUN_00815f50",
            "lower_bound": -10,
            "upper_bound": 10,
        },
    }


def move_camera_counter_toward_zero(current: int) -> dict[str, Any]:
    """Reproduce FUN_00815fa0 including returned sign byte."""
    value = int(current)
    if value > 0:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "signed-counter-toward-zero",
            "before": value,
            "after": value - 1,
            "output": 1,
            "changed": True,
            "evidence": {"function": "FUN_00815fa0"},
        }
    if value < 0:
        return {
            "format": FORMAT,
            "version": 1,
            "operation": "signed-counter-toward-zero",
            "before": value,
            "after": value + 1,
            "output": 0,
            "changed": True,
            "evidence": {"function": "FUN_00815fa0"},
        }
    return {
        "format": FORMAT,
        "version": 1,
        "operation": "signed-counter-toward-zero",
        "before": 0,
        "after": 0,
        "output": 0,
        "changed": False,
        "evidence": {"function": "FUN_00815fa0"},
    }
