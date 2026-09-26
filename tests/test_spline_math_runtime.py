from spline_math_runtime import (
    cubic_interpolate,
    describe_cubic_interpolation,
    spline_end_gate,
    spline_start_gate,
)


def test_start_gate_blocks_when_factor_is_nonzero_and_index_is_valid():
    assert spline_start_gate(factor=0.5, index=0)["result"] == 0
    assert spline_start_gate(factor=0.0, index=0)["result"] == 1
    assert spline_start_gate(factor=0.5, index=-1)["result"] == 1


def test_end_gate_blocks_before_final_segment():
    assert spline_end_gate(factor=0.5, index=3, count=5)["result"] == 0
    assert spline_end_gate(factor=1.0, index=3, count=5)["result"] == 1
    assert spline_end_gate(factor=0.5, index=4, count=5)["result"] == 1


def test_cubic_interpolation_matches_source_formula_at_zero_and_one():
    assert cubic_interpolate(
        coefficient_a=1,
        coefficient_b=2,
        coefficient_c=3,
        coefficient_d=4,
        t=0,
    ) == 1.0
    assert cubic_interpolate(
        coefficient_a=1,
        coefficient_b=2,
        coefficient_c=3,
        coefficient_d=4,
        t=1,
    ) == 3.0


def test_describe_cubic_interpolation_exposes_raw_coefficients():
    result = describe_cubic_interpolation(
        coefficients=(1, 2, 3, 4),
        t=0.5,
    )
    assert result["coefficients"] == [1.0, 2.0, 3.0, 4.0]
    assert result["value"] == cubic_interpolate(
        coefficient_a=1,
        coefficient_b=2,
        coefficient_c=3,
        coefficient_d=4,
        t=0.5,
    )
