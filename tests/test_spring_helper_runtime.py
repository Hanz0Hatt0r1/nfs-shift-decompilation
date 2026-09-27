import pytest

from spring_helper_runtime import (
    HARD_STOP_VALUE,
    SpringHelperCoefficients,
    build_spring_helper_contract,
    compute_damping_term_exact,
    compute_gap,
    compute_spring_helper_step,
    compute_stop_polynomial,
)


def _coefficients() -> SpringHelperCoefficients:
    return SpringHelperCoefficients(
        c_1d0=10.0, c_1d8=1.0, c_1e0=2.0, c_1e8=100.0,
        c_1f0=0.0, c_1f8=3.0, c_200=4.0, c_208=50.0,
        c_210=5.0, c_218=1.0, c_220=2.0, c_228=3.0,
        c_230=4.0, c_238=2.0, c_240=5.0,
    )


def test_contract_proves_x87_return_consumed_by_caller():
    c = build_spring_helper_contract()
    assert c["return_abi"]["register"] == "x87 ST0"
    assert c["state"]["current_gap_offset"] == 0x248
    assert c["state"]["previous_gap_offset"] == 0x250
    assert c["state"]["crossing_flag_offset"] == 0x260
    assert c["constants"]["hard_stop_value"] == -80000.0


def test_gap_uses_upper_or_lower_boundary_exactly():
    assert compute_gap(displacement=5.0, c_238=2.0, c_240=5.0) == 0.0
    assert compute_gap(displacement=4.0, c_238=2.0, c_240=5.0) == 1.0
    assert compute_gap(displacement=7.0, c_238=2.0, c_240=5.0) == 5.0


def test_damping_branch_selects_positive_midband_or_other_path():
    assert compute_damping_term_exact(
        velocity_projection=3.0, c_1e0=2.0, c_1e8=100.0,
        c_1f8=3.0, c_200=4.0, c_208=50.0, c_210=5.0
    ) == 6.0
    assert compute_damping_term_exact(
        velocity_projection=110.0, c_1e0=2.0, c_1e8=100.0,
        c_1f8=3.0, c_200=4.0, c_208=50.0, c_210=5.0
    ) == 440.0
    assert compute_damping_term_exact(
        velocity_projection=-2.0, c_1e0=2.0, c_1e8=100.0,
        c_1f8=3.0, c_200=4.0, c_208=50.0, c_210=5.0
    ) == -1.0


def test_positive_stop_polynomial_applies_hard_stop():
    polynomial = compute_stop_polynomial(
        gap=2.0, velocity_projection=1.0,
        c_218=1.0, c_220=2.0, c_228=3.0, c_230=4.0
    )
    assert polynomial == 17.0
    step = compute_spring_helper_step(
        displacement=3.0,
        velocity_projection=1.0,
        previous_gap=-1.0,
        coefficients=_coefficients(),
    )
    assert step.gap == 2.0
    assert step.base_response == 32.0
    assert step.hard_stop_applied is True
    assert step.response == 32.0 + HARD_STOP_VALUE


def test_nonpositive_stop_polynomial_does_not_apply_hard_stop():
    c = _coefficients()
    step = compute_spring_helper_step(
        displacement=5.0,
        velocity_projection=-2.0,
        previous_gap=0.5,
        coefficients=c,
    )
    assert step.gap == 0.0
    assert step.hard_stop_applied is False
    assert step.response == step.base_response


def test_crossing_latches_velocity_and_rejects_nonfinite_inputs():
    step = compute_spring_helper_step(
        displacement=3.0,
        velocity_projection=7.5,
        previous_gap=-0.25,
        coefficients=_coefficients(),
    )
    assert step.crossing_triggered is True
    assert step.trigger_value == 7.5

    with pytest.raises(ValueError):
        compute_gap(displacement=float("nan"), c_238=1.0, c_240=2.0)
