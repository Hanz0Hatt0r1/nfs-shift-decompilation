"""Evidence-backed MATRIX transform semantics used by scene/object runtime."""

from __future__ import annotations

from math import isfinite
from typing import Any, Iterable


FORMAT = "SHIFT.MatrixRuntime/1"


def _vec(values: Iterable[Any], count: int, name: str) -> list[float]:
    result = [float(value) for value in values]
    if len(result) != count:
        raise ValueError(f"{name} requires {count} values, got {len(result)}")
    if not all(isfinite(x) for x in result):
        raise ValueError(f"{name} contains a non-finite value")
    return result


def parse_matrix(
    *,
    offset: Iterable[Any] | None = None,
    orientation_input: Iterable[Any] | None = None,
    scale: Any | None = None,
) -> dict[str, Any]:
    """Reconstruct FUN_00698d50/FUN_00698f40 MATRIX parsing.

    The textual orientation reader consumes four floats and stores them into
    the runtime quaternion as [w, x, y, z]: source values [a,b,c,d] become
    [d,a,b,c]. Scale is optional and defaults to 1.0.
    """
    translation = [0.0, 0.0, 0.0] if offset is None else _vec(offset, 3, "Offset")
    input_orientation = (
        [0.0, 0.0, 0.0, 1.0]
        if orientation_input is None
        else _vec(orientation_input, 4, "Orientation")
    )
    runtime_quaternion_wxyz = [
        input_orientation[3],
        input_orientation[0],
        input_orientation[1],
        input_orientation[2],
    ]
    scalar_scale = 1.0 if scale is None else float(scale)
    if not isfinite(scalar_scale):
        raise ValueError("Scale contains a non-finite value")
    return {
        "format": FORMAT,
        "version": 1,
        "offset": translation,
        "orientation_input": input_orientation,
        "quaternion_internal_wxyz": runtime_quaternion_wxyz,
        "scale": scalar_scale,
        "source": {
            "reader": "FUN_00698d50",
            "object_reader": "FUN_00698f40",
            "orientation_reader": "FUN_00698c40",
            "offset_reader": "FUN_00698bd0",
            "scale_reader": "FUN_00698cc0",
        },
    }


def normalize_matrix_contract(matrix: dict[str, Any]) -> dict[str, Any]:
    """Validate an already-decoded MATRIX contract without reinterpreting it."""
    offset = _vec(matrix.get("offset", [0.0, 0.0, 0.0]), 3, "offset")
    quat = _vec(matrix.get("quaternion_internal_wxyz", [1.0, 0.0, 0.0, 0.0]), 4, "quaternion_internal_wxyz")
    scale = float(matrix.get("scale", 1.0))
    if not isfinite(scale):
        raise ValueError("matrix scale is not finite")
    return {
        "format": FORMAT,
        "version": 1,
        "offset": offset,
        "quaternion_internal_wxyz": quat,
        "scale": scale,
        "validated": True,
        "source_contract_preserved": True,
    }


def matrix_to_4x4(matrix: dict[str, Any]) -> list[float]:
    """Convert only the proven runtime quaternion/translation/scale values."""
    normalized = normalize_matrix_contract(matrix)
    w, x, y, z = normalized["quaternion_internal_wxyz"]
    s = normalized["scale"]
    tx, ty, tz = normalized["offset"]
    return [
        s * (1 - 2 * (y * y + z * z)), s * (2 * (x * y - z * w)), s * (2 * (x * z + y * w)), tx,
        s * (2 * (x * y + z * w)), s * (1 - 2 * (x * x + z * z)), s * (2 * (y * z - x * w)), ty,
        s * (2 * (x * z - y * w)), s * (2 * (y * z + x * w)), s * (1 - 2 * (x * x + y * y)), tz,
        0.0, 0.0, 0.0, 1.0,
    ]
