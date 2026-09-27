import pytest

from wheel_contact_factor_runtime import (
    ANGLE_LIMIT,
    ANGLE_PI_DENOMINATOR,
    ANGLE_PI_NUMERATOR,
    COS_BIAS,
    COS_SCALE,
    FACTOR_VALUE_BASE,
    PREVIOUS_VALUE_BASE,
    WHEEL_COUNT,
    WHEEL_STRIDE,
    build_contract,
    build_four_wheel_contact_factors,
    compute_contact_factor,
)


def test_contract_freezes_exact_helper_constants_and_layout():
    c = build_contract()
    assert c["function"] == "FUN_00758ad0"
    assert c["caller"] == "FUN_00765c40"
    assert c["input"]["threshold_offset"] == 0xC10F94
    assert c["helper_arithmetic"]["clamp"] == "[0, 6]"
    assert ANGLE_LIMIT == 6.0
    assert ANGLE_PI_NUMERATOR == pytest.approx(3.1415927410125732)
    assert ANGLE_PI_DENOMINATOR == 6.0
    assert COS_SCALE == pytest.approx(0.02500000037252903)
    assert COS_BIAS == pytest.approx(0.9750000238418579)


def test_zero_input_and_full_clamp_match_endpoints():
    zero = compute_contact_factor(projected_value=0.0, threshold_value=0.0)
    assert zero.clamped_value == 0.0
    assert zero.factor == pytest.approx(1.0, abs=2e-7)

    high = compute_contact_factor(projected_value=100.0, threshold_value=0.0)
    assert high.clamped_value == 6.0
    assert high.factor == pytest.approx(0.95, abs=2e-6)


def test_midpoint_is_cosine_at_pi_over_two():
    midpoint = compute_contact_factor(projected_value=3.0, threshold_value=0.0)
    assert midpoint.angle_radians == pytest.approx(ANGLE_PI_NUMERATOR / 2.0)
    assert abs(midpoint.cosine) < 2e-7
    assert midpoint.factor == pytest.approx(COS_BIAS, abs=2e-7)


def test_threshold_shifts_preclamp_before_the_six_unit_clamp():
    result = compute_contact_factor(projected_value=4.0, threshold_value=2.0)
    assert result.pre_clamp == pytest.approx(3.0)
    assert result.clamped_value == 3.0


def test_four_wheel_storage_matches_source_order_and_reference_branch():
    rows = build_four_wheel_contact_factors(
        [0.0, 1.0, 2.0, 3.0],
        threshold_value=0.0,
        enabled=True,
        frame_equal=True,
        frame_reference=17.5,
    )
    assert len(rows) == WHEEL_COUNT
    assert [r.wheel_index for r in rows] == [0, 1, 2, 3]
    assert [r.factor for r in rows] == pytest.approx(
        [1.0, 0.9966506, 0.9875, 0.975], abs=2e-6
    )
    assert [r.previous_value for r in rows] == [17.5] * 4
    assert rows[2].wheel_factor_offset == FACTOR_VALUE_BASE + 2 * WHEEL_STRIDE
    assert rows[2].previous_value_offset == PREVIOUS_VALUE_BASE + 2 * WHEEL_STRIDE


def test_disabled_path_forces_one_and_zeroes_previous_reference():
    rows = build_four_wheel_contact_factors(
        [1.0, 2.0, 3.0, 4.0],
        threshold_value=2.0,
        enabled=False,
        frame_equal=False,
        frame_reference=99.0,
    )
    assert [r.factor for r in rows] == [1.0] * 4
    assert [r.previous_value for r in rows] == [0.0] * 4


def test_invalid_cardinality_rejected():
    with pytest.raises(ValueError):
        build_four_wheel_contact_factors(
            [1.0, 2.0, 3.0],
            threshold_value=0.0,
            enabled=True,
            frame_equal=True,
            frame_reference=0.0,
        )
