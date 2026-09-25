from camera_view_cockpit_dynamics_runtime import (
    cockpit_update,
    non_cockpit_update,
)


def test_non_cockpit_profile_not_selected_zeros_all_three_outputs():
    result = non_cockpit_update(
        selected_cockpit_profile=False,
        delta=0.1,
        input_axis_0=1,
        input_axis_1=1,
        current_84=2,
        current_88=3,
        current_8c=4,
        rate_2c0_radians=-1,
        rate_2c4_radians=1,
        rate_2b8_radians=-2,
        rate_700_radians=2,
        direct_scale=1,
        smoothing_scale=1,
        target_84=0,
        target_88=0,
        use_smoothing=False,
    )
    assert result["state_after"] == {"+0x84": 0.0, "+0x88": 0.0, "+0x8c": 0.0}


def test_non_cockpit_direct_path_applies_input_then_clamps():
    result = non_cockpit_update(
        selected_cockpit_profile=True,
        delta=1.0,
        input_axis_0=10,
        input_axis_1=10,
        current_84=0,
        current_88=0,
        current_8c=0,
        rate_2c0_radians=-1,
        rate_2c4_radians=1,
        rate_2b8_radians=-2,
        rate_700_radians=2,
        direct_scale=1,
        smoothing_scale=1,
        target_84=0,
        target_88=0,
        use_smoothing=False,
    )
    assert result["state_after"]["+0x84"] == 1
    assert result["state_after"]["+0x88"] == 2


def test_non_cockpit_smoothing_moves_toward_bdb0_targets():
    result = non_cockpit_update(
        selected_cockpit_profile=True,
        delta=0.25,
        input_axis_0=0,
        input_axis_1=0,
        current_84=0,
        current_88=0,
        current_8c=5,
        rate_2c0_radians=-1,
        rate_2c4_radians=1,
        rate_2b8_radians=-2,
        rate_700_radians=2,
        direct_scale=1,
        smoothing_scale=2,
        target_84=1,
        target_88=2,
        use_smoothing=True,
    )
    assert result["state_after"]["+0x84"] == 0.5
    assert result["state_after"]["+0x88"] == 1.0


def test_cockpit_large_first_input_wraps_and_small_second_can_blend():
    result = cockpit_update(
        delta=0.1,
        input_c=0.2,
        input_8=0.0,
        steering_value=4.0,
        action5_bit0=False,
        param4_low_byte_nonzero=False,
        current_84=0.0,
        current_88=0.5,
        current_8c=0.0,
        target_84=1.0,
        target_88=2.0,
    )
    assert result["predicates"]["abs_input_c_gt_0.1"] is True
    assert result["predicates"]["blend_used"] is False
    assert result["state_after"]["+0x88"] < 0.5


def test_cockpit_both_small_inputs_use_steering_blend():
    result = cockpit_update(
        delta=0.1,
        input_c=0.0,
        input_8=0.0,
        steering_value=4.0,
        action5_bit0=False,
        param4_low_byte_nonzero=False,
        current_84=0.0,
        current_88=0.0,
        current_8c=0.0,
        target_84=1.0,
        target_88=2.0,
    )
    assert result["predicates"]["blend_used"] is True
    assert result["state_after"]["+0x84"] > 0.0
    assert result["state_after"]["+0x88"] > 0.0


def test_cockpit_large_second_input_exposes_0040f3e0_boundary():
    result = cockpit_update(
        delta=0.1,
        input_c=0.0,
        input_8=0.2,
        steering_value=0.0,
        action5_bit0=False,
        param4_low_byte_nonzero=False,
        current_84=0.0,
        current_88=0.0,
        current_8c=0.0,
        target_84=1.0,
        target_88=2.0,
        limit_after_84_helper=0.75,
    )
    assert result["actions"][0]["action"] == "FUN_0040f3e0"
    assert result["state_after"]["+0x84"] == 0.75
