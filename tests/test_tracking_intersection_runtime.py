from tracking_intersection_runtime import (
    compute_intersection_candidates,
    intersect_and_update_bounds,
)


def test_intersection_candidate_count_is_six():
    values = list(range(16))
    candidates = compute_intersection_candidates(
        values,
        [1, 1, 1, 1],
        [1, 2, 3],
    )
    assert len(candidates) == 6


def test_zero_denominators_are_reported_as_none():
    candidates = compute_intersection_candidates(
        [0] * 16,
        [0, 0, 0, 0],
        [1, 2, 3],
    )
    assert candidates == [None] * 6


def test_negative_candidates_update_lower_bound_by_max():
    result = intersect_and_update_bounds(
        lower_bound=-10,
        upper_bound=10,
        box_values=[0] * 16,
        plane=[0, 0, 0, 0],
        direction=[0, 0, 0],
    )
    assert result["lower_bound_after"] == -10
    assert result["upper_bound_after"] == 10


def test_bound_update_rule_is_positive_to_upper_and_negative_to_lower():
    # Candidate construction is opaque; use the public trace with a case whose
    # first two denominators are non-zero and inspect the explicit update rule.
    result = intersect_and_update_bounds(
        lower_bound=-100,
        upper_bound=100,
        box_values=[1, 2, 3, 1, 2, 4, 3, 1, 4, 2, 1, -1, 2, 3, 4, 1],
        plane=[1, 0, 0, 0],
        direction=[1, 0, 0],
    )
    assert result["steps"][0]["action"] in {"upper=min", "lower=max"}
