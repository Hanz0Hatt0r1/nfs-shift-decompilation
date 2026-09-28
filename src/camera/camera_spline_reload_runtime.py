"""Source-backed spline reference maintenance for TrackCameraMan reloads.

FUN_00811ae0 stores the pre-load spline and trackside-camera counts at +0xc4 and
+0xc0. After loading XML, it marks newly appended spline objects, validates the
pre-existing tracking-camera SplineID/TargetSplineID references against the new
spline count, and rebases references belonging to newly appended tracking cameras
by the old spline count.

Only the reference maintenance is modeled here. The opaque runtime marker at
camera field index 0x3b is not given a semantic name.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable

FORMAT = "SHIFT.CameraSplineReloadRuntime/1"


def _validate_count(name: str, value: int) -> int:
    value = int(value)
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
    return value


def _normalize_id(value: Any) -> int:
    value = int(value)
    return value if value >= 0 else -1


def _clip_existing_id(value: Any, new_spline_count: int) -> int:
    value = _normalize_id(value)
    if value >= new_spline_count:
        return -1
    return value


def _rebase_new_id(value: Any, old_spline_count: int, new_spline_count: int) -> int:
    value = _normalize_id(value)
    if value < 0:
        return -1
    rebased = value + old_spline_count
    return -1 if rebased >= new_spline_count else rebased


def _camera_result(source: dict[str, Any], spline_id: int, target_spline_id: int, *, newly_loaded: bool) -> dict[str, Any]:
    row = deepcopy(source)
    row["SplineID"] = spline_id
    row["TargetSplineID"] = target_spline_id
    row["runtime"] = {
        "newly_loaded_camera": newly_loaded,
        "reference_fields_rebased": newly_loaded,
        "opaque_runtime_marker_field_index": 0x3B,
        "opaque_runtime_marker_set": newly_loaded,
    }
    return row


def rebase_tracking_camera_spline_ids(
    existing_cameras: Iterable[dict[str, Any]],
    newly_loaded_cameras: Iterable[dict[str, Any]],
    *,
    old_spline_count: int,
    new_spline_count: int,
) -> dict[str, Any]:
    """Reproduce FUN_00811ae0 spline-reference maintenance across an XML reload.

    Existing tracking cameras keep their local spline indices, but references that
    are no longer inside the post-load spline array are set to -1. Newly loaded
    tracking cameras interpret SplineID/TargetSplineID relative to the newly loaded
    spline subset, so both non-negative values receive old_spline_count before the
    same range check.
    """
    old_count = _validate_count("old_spline_count", old_spline_count)
    new_count = _validate_count("new_spline_count", new_spline_count)
    if new_count < old_count:
        raise ValueError("new_spline_count cannot be smaller than old_spline_count")

    existing = list(existing_cameras)
    newly_loaded = list(newly_loaded_cameras)
    existing_rows = [
        _camera_result(
            camera,
            _clip_existing_id(camera.get("SplineID", -1), new_count),
            _clip_existing_id(camera.get("TargetSplineID", -1), new_count),
            newly_loaded=False,
        )
        for camera in existing
    ]
    new_rows = [
        _camera_result(
            camera,
            _rebase_new_id(camera.get("SplineID", -1), old_count, new_count),
            _rebase_new_id(camera.get("TargetSplineID", -1), old_count, new_count),
            newly_loaded=True,
        )
        for camera in newly_loaded
    ]
    return {
        "format": FORMAT,
        "version": 1,
        "old_spline_count": old_count,
        "new_spline_count": new_count,
        "appended_spline_count": new_count - old_count,
        "existing_cameras": existing_rows,
        "newly_loaded_cameras": new_rows,
        "evidence": {
            "reload_runtime": "FUN_00811ae0",
            "old_trackside_camera_count_field": "this+0xc0",
            "old_spline_count_field": "this+0xc4",
            "tracking_spline_id_offsets": ["+0xf8", "+0xfc"],
        },
        "limitations": [
            "only tracking-camera spline reference maintenance is modeled",
            "the camera runtime marker at field index 0x3b remains opaque",
            "XML loading, class inheritance and camera behavior are outside this contract",
        ],
    }