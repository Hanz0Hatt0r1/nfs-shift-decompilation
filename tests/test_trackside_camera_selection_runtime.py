import pytest

from trackside_camera_selection_runtime import FLT_MAX, select_min_score, select_min_score_values


def test_empty_trackside_camera_collection_returns_minus_one():
    result = select_min_score_values([])
    assert result["selected_index"] == -1
    assert result["selected_score"] is None
    assert result["evaluated_count"] == 0


def test_minimum_score_wins_with_zero_based_runtime_index():
    result = select_min_score_values([4.0, 2.0, 3.0, 1.0])
    assert result["selected_index"] == 3
    assert result["selected_score"] == 1.0
    assert result["evaluated_count"] == 4
    assert result["early_exit_on_negative_score"] is False


def test_negative_score_stops_scan_after_current_candidate():
    result = select_min_score_values([4.0, -0.5, -10.0])
    assert result["selected_index"] == 1
    assert result["selected_score"] == -0.5
    assert result["evaluated_count"] == 2
    assert result["early_exit_on_negative_score"] is True


def test_custom_score_function_keeps_query_opaque():
    cameras = [{"value": 3}, {"value": 1}, {"value": 2}]
    result = select_min_score(cameras, query={"opaque": True}, score_fn=lambda cam, q: cam["value"])
    assert result["selected_index"] == 1
    assert result["query_preserved"] == {"opaque": True}


def test_non_finite_score_is_rejected():
    with pytest.raises(ValueError):
        select_min_score_values([FLT_MAX, float("nan")])