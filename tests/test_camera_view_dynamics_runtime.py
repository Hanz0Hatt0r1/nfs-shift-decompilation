from camera_view_dynamics_runtime import (
    compute_input_shake_angles,
    describe_free_look_registry,
    integrate_head_shake_step,
    integrate_profile_shake_step,
    normalize_angle_with_pi,
    resolve_view_input_axes,
    seed_velocity_offset_state,
    set_input_rate_values,
    update_input_direction_counters,
)


def test_direction_counters_increment_or_decrement_together():
    active = update_input_direction_counters(
        counter_0x2bc=0.0, counter_0x2c0=0.0, device_active=True
    )
    assert active["values"] == {"+0x2bc": 1.0, "+0x2c0": 1.0}
    inactive = update_input_direction_counters(
        counter_0x2bc=0.0, counter_0x2c0=0.0, device_active=False
    )
    assert inactive["values"] == {"+0x2bc": -1.0, "+0x2c0": -1.0}


def test_input_rate_values_convert_all_four_state_fields_from_degrees():
    result = set_input_rate_values(
        rate_0x2b8=180.0,
        rate_0x700=90.0,
        rate_0x2c0=45.0,
        rate_0x2c4=30.0,
    )
    assert abs(result["result"]["first_vector_radians"][0] - 3.14159256) < 1e-6
    assert abs(result["result"]["first_vector_radians"][1] - 1.57079628) < 1e-6
    assert abs(result["result"]["second_vector_radians"][0] - 0.78539814) < 1e-6
    assert abs(result["result"]["second_vector_radians"][1] - 0.52359876) < 1e-6


def test_velocity_seed_requires_active_profile():
    result = seed_velocity_offset_state(
        profile_present=False, profile_scale=1.0, vehicle_velocity=[1, 2, 3]
    )
    assert result["status"] == "skipped"


def test_velocity_seed_copies_vehicle_vector_into_a8_ac_b0():
    result = seed_velocity_offset_state(
        profile_present=True, profile_scale=1.0, vehicle_velocity=[1, 2, 3]
    )
    assert result["state"]["+0xa8"] == 1
    assert result["state"]["+0xb0"] == 3


def test_input_axes_apply_service_output_and_direction_adjustment():
    result = resolve_view_input_axes(
        action3_available=True,
        action4_available=True,
        action3_axis=4,
        action4_axis=5,
        service_axis0=3,
        service_axis1=7,
        accumulator_0x2c0=1,
        counter_0x2bc=2,
        counter_0x700=6,
        reverse_direction=False,
    )
    assert result["raw_action_axes"] == [4.0, 5.0]
    assert result["result_axes"] == [2.0, 1.0]


def test_input_shake_rates_use_positive_and_negative_global_rates():
    result = compute_input_shake_angles(
        profile_active=False,
        profile_orientation_flag=False,
        axis0=2,
        axis1=-3,
        positive_pitch_rate_deg=10,
        negative_pitch_rate_deg=20,
        positive_yaw_rate_deg=30,
        negative_yaw_rate_deg=40,
    )
    assert result["angles_degrees"] == [60.0, 90.0]


def test_head_shake_adds_helper_position_and_orientation_vectors():
    result = integrate_head_shake_step(
        delta=0.1,
        position=[1, 2, 3],
        orientation=[4, 5, 6],
        helper_position_delta=[0.1, 0.2, 0.3],
        helper_orientation_delta=[0.4, 0.5, 0.6],
    )
    assert result["position"] == [1.1, 2.2, 3.3]
    assert result["orientation"] == [4.4, 5.5, 6.6]


def test_profile_shake_no_profile_is_noop():
    result = integrate_profile_shake_step(
        profile_present=False,
        profile_frequency_factor=0,
        input_scale=1,
        helper_position_delta=[1, 1, 1],
        helper_orientation_delta=[1, 1, 1],
        position=[2, 3, 4],
        orientation=[5, 6, 7],
    )
    assert result["status"] == "no-profile"
    assert result["position"] == [2.0, 3.0, 4.0]


def test_profile_shake_active_records_exact_setup_helpers():
    result = integrate_profile_shake_step(
        profile_present=True,
        profile_frequency_factor=2,
        input_scale=0.5,
        helper_position_delta=[0, 0, 0],
        helper_orientation_delta=[0, 0, 0],
        position=[0, 0, 0],
        orientation=[0, 0, 0],
    )
    assert result["status"] == "profile-active"
    assert result["helper_boundary"]["setup"][0].startswith("FUN_00823a80")


def test_angle_normalization_matches_sign_branch():
    assert abs(normalize_angle_with_pi(1.0, seed=4.0) - (4.0 - 3.141592653589793)) < 1e-9
    assert abs(normalize_angle_with_pi(-1.0, seed=4.0) + (4.0 - 3.141592653589793)) < 1e-9


def test_free_look_registry_has_four_proven_actions():
    result = describe_free_look_registry()
    assert [x["index"] for x in result["actions"]] == [1, 2, 3, 4]
    assert result["actions"][2]["name"] == "Free Look Left/Right"
