"""Fail-closed dynamic vehicle world-transform transport for native scene sets.

Phase 646 deliberately transports already-proven D3D row-vector matrices.  It
never derives a matrix from a BODY pose and never claims BODY-local == MEB-local.
The text script is intentionally trivial to parse from the native runtime:

    SHIFT.NativeVehicleWorldTransformScript/1
    <step> <m00> ... <m33>

Every step carries one complete affine, non-singular 4x4 transform.  Scene draw
groups are transported separately through ``bundle_set.groups`` so a renderer
can update only ``vehicle`` draws while leaving ``track`` geometry untouched.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

FORMAT = "SHIFT.NativeVehicleWorldTransformScript/1"
GROUP_FORMAT = "SHIFT.NativeSceneDrawGroups/1"
SET_FORMAT = "SHIFT.NativeSceneVulkanSet/1"
_ALLOWED_GROUPS = {"track", "vehicle"}


def _matrix16(value: Sequence[float | int]) -> tuple[float, ...]:
    if isinstance(value, (str, bytes)) or len(value) != 16:
        raise ValueError("vehicle world transform must contain exactly 16 scalars")
    matrix = tuple(float(item) for item in value)
    if not all(math.isfinite(item) for item in matrix):
        raise ValueError("vehicle world transform contains non-finite scalar")
    tolerance = 1.0e-5
    if any(abs(matrix[index]) > tolerance for index in (3, 7, 11)):
        raise ValueError("vehicle world transform is not affine D3D row-vector form")
    if abs(matrix[15] - 1.0) > tolerance:
        raise ValueError("vehicle world transform homogeneous component is not one")
    a, b, c = matrix[0], matrix[1], matrix[2]
    d, e, f = matrix[4], matrix[5], matrix[6]
    g, h, i = matrix[8], matrix[9], matrix[10]
    determinant = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    if not math.isfinite(determinant) or abs(determinant) <= 1.0e-8:
        raise ValueError("vehicle world transform affine linear block is singular")
    return matrix


def validate_vehicle_world_transform_script(
    matrices: Iterable[Sequence[float | int]],
) -> dict[str, Any]:
    steps = [_matrix16(matrix) for matrix in matrices]
    if not steps:
        raise ValueError("vehicle world transform script requires at least one step")
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready",
        "ready": True,
        "blocking_reasons": [],
        "step_count": len(steps),
        "matrices": [list(matrix) for matrix in steps],
        "boundary": {
            "matrix_convention": "row-major-d3d-row-vector",
            "full_matrix_per_fixed_step": True,
            "body_pose_to_matrix_inference": False,
            "body_local_to_meb_local_bind_claimed": False,
        },
    }


def serialize_vehicle_world_transform_script(
    matrices: Iterable[Sequence[float | int]],
) -> str:
    report = validate_vehicle_world_transform_script(matrices)
    lines = [FORMAT]
    for step, matrix in enumerate(report["matrices"]):
        values = " ".join(format(float(value), ".9g") for value in matrix)
        lines.append(f"{step} {values}")
    return "\n".join(lines) + "\n"


def parse_vehicle_world_transform_script(text: str) -> dict[str, Any]:
    lines = [
        line.strip()
        for line in str(text).splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not lines or lines[0] != FORMAT:
        raise ValueError(f"vehicle world transform script header must be {FORMAT}")
    matrices: list[list[float]] = []
    for expected_step, line in enumerate(lines[1:]):
        parts = line.split()
        if len(parts) != 17:
            raise ValueError(
                f"vehicle world transform row {expected_step} must contain step + 16 scalars"
            )
        try:
            step = int(parts[0], 10)
            matrix = [float(value) for value in parts[1:]]
        except ValueError as exc:
            raise ValueError(
                f"vehicle world transform row {expected_step} contains invalid number"
            ) from exc
        if step != expected_step:
            raise ValueError("vehicle world transform steps must be contiguous from zero")
        matrices.append(matrix)
    return validate_vehicle_world_transform_script(matrices)


def write_vehicle_world_transform_script(
    path: str | Path,
    matrices: Iterable[Sequence[float | int]],
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        serialize_vehicle_world_transform_script(matrices),
        encoding="utf-8",
    )
    return target


def scene_draw_groups(manifest: Mapping[str, Any]) -> dict[str, Any]:
    if manifest.get("format") != SET_FORMAT:
        raise ValueError(f"scene manifest must be {SET_FORMAT}")
    if manifest.get("ready") is not True:
        raise ValueError("scene manifest is not ready")
    draws = manifest.get("draws")
    if not isinstance(draws, list) or not draws:
        raise ValueError("scene manifest contains no draws")
    try:
        expected = int(manifest.get("draw_count"))
    except (TypeError, ValueError) as exc:
        raise ValueError("scene manifest draw_count is invalid") from exc
    if expected != len(draws):
        raise ValueError("scene manifest draw_count does not match draws")

    groups: list[str] = []
    vehicle_indices: list[int] = []
    for index, raw in enumerate(draws):
        if not isinstance(raw, Mapping):
            raise ValueError(f"scene draw {index} is not an object")
        try:
            draw_order = int(raw.get("draw_order"))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"scene draw {index} has invalid draw_order") from exc
        if draw_order != index:
            raise ValueError("scene draw_order must be contiguous and match bundle_set.paths")
        group = str(raw.get("source_group") or "")
        if group not in _ALLOWED_GROUPS:
            raise ValueError(f"scene draw {index} has unsupported source_group {group!r}")
        groups.append(group)
        if group == "vehicle":
            vehicle_indices.append(index)
    if not vehicle_indices:
        raise ValueError("scene manifest contains no vehicle draw")

    return {
        "format": GROUP_FORMAT,
        "version": 1,
        "status": "ready",
        "ready": True,
        "blocking_reasons": [],
        "draw_count": len(groups),
        "vehicle_draw_count": len(vehicle_indices),
        "vehicle_draw_indices": vehicle_indices,
        "groups": groups,
        "boundary": {
            "aligned_with_bundle_set_paths": True,
            "track_draws_mutable_by_vehicle_transport": False,
            "vehicle_draws_explicitly_identified": True,
        },
    }


def serialize_scene_draw_groups(manifest: Mapping[str, Any]) -> str:
    report = scene_draw_groups(manifest)
    return "\n".join(report["groups"]) + "\n"


def write_scene_draw_groups(
    scene_root: str | Path,
    manifest: Mapping[str, Any],
) -> Path:
    root = Path(scene_root)
    target = root / "bundle_set.groups"
    target.write_text(serialize_scene_draw_groups(manifest), encoding="utf-8")
    return target
