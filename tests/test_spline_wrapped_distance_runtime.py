from spline_wrapped_distance_runtime import (
    accumulate_distance,
    wrapped_distance,
    wrapped_y,
)


def test_wrapped_y_uses_truncated_wrap_index_times_eight():
    assert wrapped_y(10.0, 1.9) == 2.0
    assert wrapped_y(10.0, -1.9) == 2.0


def test_wrapped_distance_corrects_only_y_component():
    result = wrapped_distance(
        [1, 10, 3],
        1,
        [5, 20, 7],
        2,
    )
    assert result["corrected_points"]["a"] == [1.0, 2.0, 3.0]
    assert result["corrected_points"]["b"] == [5.0, 4.0, 7.0]
    assert result["delta"] == [-4.0, -2.0, -4.0]
    assert result["distance"] == 6.0


def test_accumulate_distance_applies_explicit_scale_after_sqrt():
    result = accumulate_distance(
        accumulator=2.0,
        point_a=[0, 0, 0],
        wrap_a=0,
        point_b=[3, 4, 0],
        wrap_b=0,
        scale=0.5,
    )
    assert result["distance"] == 5.0
    assert result["after"] == 4.5
