import pytest

from camera_spline_reload_runtime import rebase_tracking_camera_spline_ids


def test_existing_tracking_camera_references_are_checked_against_new_total():
    result = rebase_tracking_camera_spline_ids(
        [{"SplineID": 1, "TargetSplineID": 4}, {"SplineID": 5, "TargetSplineID": -1}],
        [],
        old_spline_count=5,
        new_spline_count=5,
    )
    assert result["existing_cameras"][0]["SplineID"] == 1
    assert result["existing_cameras"][0]["TargetSplineID"] == 4
    assert result["existing_cameras"][1]["SplineID"] == -1


def test_new_tracking_camera_spline_ids_are_rebased_by_old_count():
    result = rebase_tracking_camera_spline_ids(
        [],
        [{"SplineID": 0, "TargetSplineID": 2}],
        old_spline_count=5,
        new_spline_count=8,
    )
    row = result["newly_loaded_cameras"][0]
    assert row["SplineID"] == 5
    assert row["TargetSplineID"] == 7
    assert row["runtime"]["newly_loaded_camera"] is True


def test_new_reference_outside_appended_spline_range_is_invalidated():
    result = rebase_tracking_camera_spline_ids(
        [],
        [{"SplineID": 0, "TargetSplineID": 3}],
        old_spline_count=5,
        new_spline_count=7,
    )
    row = result["newly_loaded_cameras"][0]
    assert row["SplineID"] == 5
    assert row["TargetSplineID"] == -1


def test_negative_spline_references_remain_unset():
    result = rebase_tracking_camera_spline_ids(
        [{"SplineID": -1, "TargetSplineID": -1}],
        [{"SplineID": -1, "TargetSplineID": -1}],
        old_spline_count=2,
        new_spline_count=3,
    )
    assert result["existing_cameras"][0]["SplineID"] == -1
    assert result["newly_loaded_cameras"][0]["TargetSplineID"] == -1


def test_new_spline_count_cannot_shrink():
    with pytest.raises(ValueError):
        rebase_tracking_camera_spline_ids([], [], old_spline_count=4, new_spline_count=3)