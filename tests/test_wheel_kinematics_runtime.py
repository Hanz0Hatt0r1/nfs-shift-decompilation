import pytest

from wheel_kinematics_runtime import (
    DISTANCE_ERROR_OFFSET,
    DISTANCE_REFERENCE_OFFSET,
    FORMAT,
    HELPER_OUTPUT_OFFSET,
    PROJECTION_VALUE_OFFSET,
    WHEEL_ACTIVE_FLAG_OFFSET,
    WHEEL_RUNTIME_BASE,
    WHEEL_RUNTIME_STRIDE,
    WHEEL_STATE_BASE,
    WHEEL_STATE_STRIDE,
    build_pair_adjustment_observation,
    build_wheel_kinematics_contract,
    normalize_relative_vector,
    prepare_wheel_kinematic_observation,
)


def test_contract_freezes_four_wheel_layout_and_handoff():
    c = build_wheel_kinematics_contract()
    assert c["format"] == FORMAT == "SHIFT.WheelKinematicsRuntime/1"
    assert c["function"] == "FUN_00758b50"
    assert c["caller"] == "FUN_0076d100"
    assert c["wheel_state"]["base"] == WHEEL_STATE_BASE == 0x848
    assert c["wheel_state"]["stride"] == WHEEL_STATE_STRIDE == 0xA80
    assert c["wheel_state"]["active_flag_offset"] == WHEEL_ACTIVE_FLAG_OFFSET == 0xF8
    assert c["wheel_runtime"]["base"] == WHEEL_RUNTIME_BASE == 0x400
    assert c["wheel_runtime"]["stride"] == WHEEL_RUNTIME_STRIDE == 0xA80
    assert c["wheel_runtime"]["fields"]["distance_reference"] == DISTANCE_REFERENCE_OFFSET == 0x138
    assert c["wheel_runtime"]["fields"]["distance_error"] == DISTANCE_ERROR_OFFSET == 0x128
    assert c["wheel_runtime"]["fields"]["projection_value"] == PROJECTION_VALUE_OFFSET == 0x130
    assert c["wheel_runtime"]["fields"]["helper_output"] == HELPER_OUTPUT_OFFSET == 0x148


def test_relative_vector_normalization_matches_source_shape():
    length, unit = normalize_relative_vector((3.0, 4.0, 12.0))
    assert length == 13.0
    assert unit == pytest.approx((3.0 / 13.0, 4.0 / 13.0, 12.0 / 13.0))


def test_prepare_observation_reproduces_fun_00755950_inputs():
    obs = prepare_wheel_kinematic_observation(
        wheel_index=2,
        relative_vector=(0.0, 3.0, 4.0),
        reference_length=6.5,
        projection_input=1.75,
    )
    assert obs.wheel_state_offset == 0x848 + 2 * 0xA80
    assert obs.wheel_runtime_offset == 0x400 + 2 * 0xA80
    assert obs.relative_length == 5.0
    assert obs.distance_error == 1.5
    assert obs.stored_projection_value == -1.75


def test_pair_delta_matches_exact_source_formula():
    pair = build_pair_adjustment_observation(
        pair="front",
        source_a_left=10.0,
        source_b_left=2.0,
        source_a_right=7.0,
        source_b_right=1.0,
        scale=0.25,
    )
    assert pair.delta == pytest.approx(0.5)
    assert pair.left_after == pytest.approx(0.5)
    assert pair.right_after == pytest.approx(-0.5)


def test_invalid_wheel_index_and_zero_length_close_fail():
    with pytest.raises(ValueError):
        prepare_wheel_kinematic_observation(
            wheel_index=4,
            relative_vector=(1.0, 0.0, 0.0),
            reference_length=1.0,
            projection_input=0.0,
        )
    with pytest.raises(ValueError):
        normalize_relative_vector((0.0, 0.0, 0.0))



def test_fun_00755950_chain_reaches_decoded_spring_helper():
    from spring_helper_runtime import SpringHelperCoefficients

    coeffs = SpringHelperCoefficients(
        c_1d0=10.0, c_1d8=1.0, c_1e0=2.0, c_1e8=100.0,
        c_1f0=0.0, c_1f8=3.0, c_200=4.0, c_208=50.0,
        c_210=5.0, c_218=1.0, c_220=2.0, c_228=3.0,
        c_230=4.0, c_238=2.0, c_240=5.0,
    )
    step = evaluate_wheel_spring_helper(
        distance_reference=8.0,
        relative_length=5.0,
        projection_input=-1.0,
        previous_gap=-0.5,
        coefficients=coeffs,
    )
    assert step.displacement == 3.0
    assert step.velocity_projection == 1.0
    assert step.crossing_triggered is True


def test_final_transform_boundary_is_preserved_without_semantic_guess():
    c = build_wheel_kinematics_contract()["final_per_wheel_transform"]
    assert c["guard_flag_offset"] == 0x11C
    assert c["scale_field_offset"] == 0x124
    assert c["wheel_transform_helper"] == "FUN_007baa70"
    assert c["vehicle_transform_helper"] == "FUN_007baaf0"
