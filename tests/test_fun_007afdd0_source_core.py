import math

import pytest

from fun_007afdd0_source_core import (
    COSINE_HELPER,
    FORMAT,
    MACHINE_PRECISION_GATE_REQUIRED,
    SINE_HELPER,
    Fun007afdd0ScalarBoundary,
    contract,
    execute_fun_007afdd0_source_core,
    f32,
)


def test_contract_keeps_machine_precision_gate_closed():
    payload = contract()
    assert payload["format"] == FORMAT == "SHIFT.Fun007afdd0SourceCore/1"
    assert payload["source_function"] == "FUN_007afdd0"
    assert payload["source_line"] == 810824
    assert SINE_HELPER in payload["external_scalar_boundary"]["sine"]
    assert COSINE_HELPER in payload["external_scalar_boundary"]["cosine"]
    assert payload["in_place_write_stripes"] == [[0, 3, 6], [1, 4, 7], [2, 5, 8]]
    assert payload["host_math_used"] is False
    assert payload["machine_precision_gate_required"] is MACHINE_PRECISION_GATE_REQUIRED is True
    assert payload["native_callback_replacement_ready"] is False


def test_zero_magnitude_test_is_exact_noop_and_does_not_consume_trig_boundary():
    basis = [1.25, -2.5, 3.75, 4.5, -5.25, 6.0, 7.5, 8.25, -9.0]
    result = execute_fun_007afdd0_source_core(
        basis,
        [0.0, 0.0, 0.0],
        Fun007afdd0ScalarBoundary(
            squared_magnitude_test=0.0,
            sqrt_magnitude=float("nan"),
            sine=float("nan"),
            cosine=float("nan"),
        ),
    )
    assert result.applied is False
    assert result.basis == tuple(f32(value) for value in basis)
    assert result.normalized_axis == (0.0, 0.0, 0.0)
    assert result.rotation_coefficients == (
        1.0, 0.0, 0.0,
        0.0, 1.0, 0.0,
        0.0, 0.0, 1.0,
    )


def test_z_axis_quarter_turn_matches_recovered_coefficients_and_stripe_order():
    basis = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
    result = execute_fun_007afdd0_source_core(
        basis,
        [0.0, 0.0, 2.0],
        Fun007afdd0ScalarBoundary(
            squared_magnitude_test=4.0,
            sqrt_magnitude=2.0,
            sine=1.0,
            cosine=0.0,
        ),
    )
    assert result.applied is True
    assert result.normalized_axis == (0.0, 0.0, 1.0)
    assert result.rotation_coefficients == (
        0.0, -1.0, 0.0,
        1.0, 0.0, 0.0,
        0.0, 0.0, 1.0,
    )
    assert result.basis == (
        -4.0, -5.0, -6.0,
        1.0, 2.0, 3.0,
        7.0, 8.0, 9.0,
    )


def test_axis_inputs_are_cast_to_f32_before_normalization_product():
    increment = [3.0000001192092896, 4.000000238418579, 0.0]
    result = execute_fun_007afdd0_source_core(
        [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0],
        increment,
        Fun007afdd0ScalarBoundary(
            squared_magnitude_test=25.0,
            sqrt_magnitude=5.0,
            sine=0.0,
            cosine=1.0,
        ),
    )
    expected_x = f32(f32(1.0 / f32(5.0)) * f32(increment[0]))
    expected_y = f32(f32(increment[1]) * f32(1.0 / f32(5.0)))
    assert result.normalized_axis == (expected_x, expected_y, 0.0)
    assert result.basis == (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0)


def test_nonzero_path_rejects_missing_or_nonfinite_scalar_boundary():
    basis = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    with pytest.raises(ValueError, match="non-zero f32 sqrt"):
        execute_fun_007afdd0_source_core(
            basis,
            [1.0, 0.0, 0.0],
            Fun007afdd0ScalarBoundary(squared_magnitude_test=1.0),
        )
    with pytest.raises(ValueError, match="non-finite"):
        execute_fun_007afdd0_source_core(
            basis,
            [1.0, 0.0, 0.0],
            Fun007afdd0ScalarBoundary(
                squared_magnitude_test=1.0,
                sqrt_magnitude=1.0,
                sine=math.nan,
                cosine=1.0,
            ),
        )


def test_invalid_cardinality_and_nonfinite_inputs_fail_closed():
    boundary = Fun007afdd0ScalarBoundary(
        squared_magnitude_test=1.0,
        sqrt_magnitude=1.0,
        sine=0.0,
        cosine=1.0,
    )
    with pytest.raises(ValueError, match="exactly 9"):
        execute_fun_007afdd0_source_core([1.0] * 8, [1.0, 0.0, 0.0], boundary)
    with pytest.raises(ValueError, match="exactly 3"):
        execute_fun_007afdd0_source_core([1.0] * 9, [1.0, 0.0], boundary)
    with pytest.raises(ValueError, match="non-finite"):
        execute_fun_007afdd0_source_core(
            [1.0] * 9,
            [float("inf"), 0.0, 0.0],
            boundary,
        )
