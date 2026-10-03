from __future__ import annotations

import math

import pytest

import native_vehicle_world_transform_script as mod


def _identity(tx=0.0, ty=0.0, tz=0.0):
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        tx, ty, tz, 1.0,
    ]


def test_vehicle_transform_script_roundtrips_complete_fixed_steps():
    matrices = [_identity(), _identity(1.5, -2.0, 3.25)]
    text = mod.serialize_vehicle_world_transform_script(matrices)
    assert text.splitlines()[0] == mod.FORMAT
    report = mod.parse_vehicle_world_transform_script(text)
    assert report["ready"] is True
    assert report["step_count"] == 2
    assert report["matrices"][1][12:15] == [1.5, -2.0, 3.25]
    assert report["boundary"]["body_pose_to_matrix_inference"] is False


def test_vehicle_transform_script_rejects_nonfinite_nonaffine_and_singular():
    nonfinite = _identity()
    nonfinite[12] = math.inf
    with pytest.raises(ValueError, match="non-finite"):
        mod.validate_vehicle_world_transform_script([nonfinite])

    nonaffine = _identity()
    nonaffine[3] = 1.0
    with pytest.raises(ValueError, match="affine D3D row-vector"):
        mod.validate_vehicle_world_transform_script([nonaffine])

    singular = _identity()
    singular[0] = 0.0
    with pytest.raises(ValueError, match="singular"):
        mod.validate_vehicle_world_transform_script([singular])


def test_vehicle_transform_script_rejects_gaps_and_short_rows():
    row = " ".join(["1"] * 16)
    with pytest.raises(ValueError, match="contiguous"):
        mod.parse_vehicle_world_transform_script(
            mod.FORMAT + "\n1 " + row + "\n"
        )
    with pytest.raises(ValueError, match="16 scalars"):
        mod.parse_vehicle_world_transform_script(
            mod.FORMAT + "\n0 1 2 3\n"
        )


def test_scene_groups_are_exactly_aligned_with_draw_order():
    manifest = {
        "format": mod.SET_FORMAT,
        "ready": True,
        "draw_count": 3,
        "draws": [
            {"draw_order": 0, "source_group": "track"},
            {"draw_order": 1, "source_group": "track"},
            {"draw_order": 2, "source_group": "vehicle"},
        ],
    }
    report = mod.scene_draw_groups(manifest)
    assert report["groups"] == ["track", "track", "vehicle"]
    assert report["vehicle_draw_indices"] == [2]
    assert mod.serialize_scene_draw_groups(manifest) == "track\ntrack\nvehicle\n"


def test_scene_groups_reject_unknown_missing_vehicle_and_order_drift():
    base = {
        "format": mod.SET_FORMAT,
        "ready": True,
        "draw_count": 1,
        "draws": [{"draw_order": 0, "source_group": "track"}],
    }
    with pytest.raises(ValueError, match="no vehicle draw"):
        mod.scene_draw_groups(base)

    unknown = {**base, "draws": [{"draw_order": 0, "source_group": "garage"}]}
    with pytest.raises(ValueError, match="unsupported source_group"):
        mod.scene_draw_groups(unknown)

    drift = {
        **base,
        "draws": [{"draw_order": 1, "source_group": "vehicle"}],
    }
    with pytest.raises(ValueError, match="draw_order"):
        mod.scene_draw_groups(drift)
