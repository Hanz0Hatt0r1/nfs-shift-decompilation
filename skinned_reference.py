"""CPU reference for validated SHIFT.SkinnedDraw/1 packets.

The reference renderer consumes an explicit SHIFT.SkinPose/1. It deliberately
does not derive pose matrices from BAB/BAS local bind transforms.
"""
from __future__ import annotations

from typing import Any, Iterable
import math

from skinning import skin_points, skin_directions, validate_influences


FORMAT = "SHIFT.SkinnedReference/1"


def _require_pose(draw: dict[str, Any]) -> tuple[list[list[float]], int]:
    if draw.get("format") != "SHIFT.SkinnedDraw/1":
        raise ValueError("expected SHIFT.SkinnedDraw/1")
    if not draw.get("ready"):
        raise ValueError(
            "skinned draw is not ready: "
            + ", ".join(draw.get("blocking_reasons", []))
        )
    pose = draw.get("skin_pose") or {}
    if pose.get("format") != "SHIFT.SkinPose/1":
        raise ValueError("missing SHIFT.SkinPose/1")
    if pose.get("matrix_space") != "skinning":
        raise ValueError("skin pose must use matrix_space=skinning")
    bone_count = int(pose.get("bone_count", 0) or 0)
    matrices = list(pose.get("matrices_3x4", []) or [])
    if bone_count <= 0:
        raise ValueError("skin pose has no bones")
    if len(matrices) != bone_count:
        raise ValueError("skin pose matrix count does not match bone count")
    for index, matrix in enumerate(matrices):
        if not isinstance(matrix, list) or len(matrix) != 12:
            raise ValueError(f"skin pose matrix {index} is not a 3x4 matrix")
    return ([[float(x) for x in matrix] for matrix in matrices], bone_count)


def skin_draw_points(
    draw: dict[str, Any],
    positions: Iterable[Iterable[float]],
    bone_indices: Iterable[Iterable[int]],
    bone_weights: Iterable[Iterable[float]],
    *,
    normalize_weights: bool = False,
    strict_indices: bool = True,
) -> dict[str, Any]:
    """Apply the explicit skin pose to positions and return a reference IR."""
    matrices, bone_count = _require_pose(draw)
    pos = [tuple(float(x) for x in row) for row in positions]
    ids = [tuple(int(x) for x in row) for row in bone_indices]
    weights = [tuple(float(x) for x in row) for row in bone_weights]

    validation = validate_influences(
        ids,
        weights,
        bone_count,
        strict_indices=strict_indices,
    )
    if not validation["valid"]:
        raise ValueError(f"invalid skin influences: {validation['issues']}")

    result = skin_points(
        pos,
        ids,
        weights,
        [{"matrix_3x4": matrix} for matrix in matrices],
        normalize_weights=normalize_weights,
        strict_indices=strict_indices,
    )
    pose = draw.get("skin_pose") or {}
    return {
        "format": FORMAT,
        "source": "SHIFT.SkinPose/1",
        "frame": pose.get("frame"),
        "vertex_count": len(result),
        "positions": [list(row) for row in result],
        "influence_validation": validation,
    }


def validate_bind_pose(
    draw: dict[str, Any],
    positions: Iterable[Iterable[float]],
    bone_indices: Iterable[Iterable[int]],
    bone_weights: Iterable[Iterable[float]],
    *,
    tolerance: float = 1.0e-5,
    normalize_weights: bool = False,
    strict_indices: bool = True,
) -> dict[str, Any]:
    """Check whether an explicit SkinPose reproduces the supplied bind positions."""
    if tolerance < 0.0:
        raise ValueError("tolerance must be non-negative")
    source = [tuple(float(x) for x in row) for row in positions]
    result = skin_draw_points(
        draw,
        source,
        bone_indices,
        bone_weights,
        normalize_weights=normalize_weights,
        strict_indices=strict_indices,
    )
    mismatches: list[dict[str, Any]] = []
    max_error = 0.0
    for index, (expected, actual) in enumerate(zip(source, result["positions"])):
        error = math.sqrt(sum((float(actual[i]) - expected[i]) ** 2 for i in range(3)))
        max_error = max(max_error, error)
        if error > tolerance:
            mismatches.append({
                "vertex": index,
                "expected": list(expected),
                "actual": list(actual),
                "error": error,
            })
    return {
        "format": "SHIFT.SkinBindPoseCheck/1",
        "valid": not mismatches,
        "vertex_count": len(source),
        "max_error": max_error,
        "tolerance": tolerance,
        "mismatches": mismatches,
        "influence_validation": result["influence_validation"],
        "frame": result.get("frame"),
    }


def skin_draw_directions(
    draw: dict[str, Any],
    vectors: Iterable[Iterable[float]],
    bone_indices: Iterable[Iterable[int]],
    bone_weights: Iterable[Iterable[float]],
    *,
    normalize_weights: bool = False,
    strict_indices: bool = True,
) -> dict[str, Any]:
    """Apply the explicit skin pose to direction vectors such as normals."""
    matrices, bone_count = _require_pose(draw)
    vec = [tuple(float(x) for x in row) for row in vectors]
    ids = [tuple(int(x) for x in row) for row in bone_indices]
    weights = [tuple(float(x) for x in row) for row in bone_weights]

    validation = validate_influences(
        ids,
        weights,
        bone_count,
        strict_indices=strict_indices,
    )
    if not validation["valid"]:
        raise ValueError(f"invalid skin influences: {validation['issues']}")

    result = skin_directions(
        vec,
        ids,
        weights,
        [{"matrix_3x4": matrix} for matrix in matrices],
        normalize_weights=normalize_weights,
        strict_indices=strict_indices,
    )
    return {
        "format": FORMAT,
        "source": "SHIFT.SkinPose/1",
        "frame": (draw.get("skin_pose") or {}).get("frame"),
        "vector_count": len(result),
        "vectors": [list(row) for row in result],
        "influence_validation": validation,
    }
