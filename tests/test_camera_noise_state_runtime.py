from camera_noise_state_runtime import (
    advance_camera_noise_state,
    resolve_and_advance_camera_noise,
)


def test_noise_frequency_is_normalized_time_times_b8():
    result = advance_camera_noise_state(
        normalized_time=0.25,
        noise_scale=4.0,
        profile_scale=2.0,
    )
    assert result["frequency"] == 1.0
    assert result["amplitude"] == 2.0


def test_noise_actions_keep_exact_helper_order():
    result = advance_camera_noise_state(
        normalized_time=0.5,
        noise_scale=2.0,
        profile_scale=3.0,
    )
    assert result["actions"][0]["action"] == "FUN_006bbf10"
    assert result["actions"][1]["action"] == "FUN_00823a80"


def test_composed_noise_uses_c090_clamp_before_caf0():
    result = resolve_and_advance_camera_noise(
        sample_time=20.0,
        profile_start=0.0,
        profile_end=10.0,
        noise_scale=2.0,
        profile_scale=3.0,
    )
    assert result["normalized_time"] == 1.0
    assert result["frequency"] == 2.0
    assert result["amplitude"] == 6.0


def test_composed_noise_clamps_negative_normalized_time_to_zero():
    result = resolve_and_advance_camera_noise(
        sample_time=-10.0,
        profile_start=0.0,
        profile_end=10.0,
        noise_scale=2.0,
        profile_scale=3.0,
    )
    assert result["normalized_time"] == 0.0
    assert result["frequency"] == 0.0
