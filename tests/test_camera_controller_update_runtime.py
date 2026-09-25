from camera_controller_update_runtime import (
    CameraControllerInstance,
    describe_camera_controller_update,
    elapsed_float_from_u32,
)


def _instances(mode=2):
    return [
        CameraControllerInstance(
            slot_index=i,
            enabled=True,
            busy=False,
            refresh_requested=(i == 0),
            mode=mode,
            camera_source=f"cam-{i}",
            active_buffer_sub_index=0xFF,
            active_group=5,
            view_check_c4=(i == 0),
            view_check_sub_index=False if mode == 1 else None,
        )
        for i in range(3)
    ]


def test_u32_elapsed_conversion_matches_source_signed_fixup():
    result = elapsed_float_from_u32(0xFFFFFFF6)
    assert result["elapsed_u32"] == 0xFFFFFFF6
    assert result["signed_int_view"] == -10
    assert result["float_elapsed"] == float(0xFFFFFFF6)


def test_controller_iterates_exactly_three_slots_and_keeps_stride():
    result = describe_camera_controller_update(
        _instances(), elapsed_u32=100, feedback_flag=False, timer=1.0
    )
    assert result["slot_count"] == 3
    assert result["slot_stride"] == 0x2AA0
    assert [row["slot_offset"] for row in result["instances"]] == [0, 0x2AA0, 0x5540]


def test_disabled_or_busy_slot_is_skipped_before_mode_logic():
    instances = _instances()
    instances[1] = CameraControllerInstance(
        slot_index=1,
        enabled=False,
        busy=False,
        refresh_requested=True,
        mode=2,
    )
    result = describe_camera_controller_update(
        instances, elapsed_u32=20, feedback_flag=False, timer=1.0
    )
    assert result["instances"][1]["status"] == "skipped"
    assert result["instances"][1]["actions"] == []


def test_refresh_for_mode_one_uses_signed_low_byte_and_other_modes_use_minus_one():
    mode1 = _instances(mode=1)[0]
    mode1 = CameraControllerInstance(
        **{**mode1.__dict__, "active_buffer_sub_index": 0xFF}
    )
    result1 = describe_camera_controller_update(
        [mode1, _instances(mode=1)[1], _instances(mode=1)[2]],
        elapsed_u32=1,
        feedback_flag=False,
        timer=1.0,
    )
    refresh = result1["instances"][0]["actions"][0]
    assert refresh["action"] == "FUN_0080d300"
    assert refresh["arguments"]["sub_index"] == -1

    result2 = describe_camera_controller_update(
        _instances(mode=2), elapsed_u32=1, feedback_flag=False, timer=1.0
    )
    refresh2 = result2["instances"][0]["actions"][0]
    assert refresh2["arguments"]["sub_index"] == -1


def test_mode_two_with_feedback_flag_records_c230_reissue_and_12050_branch():
    result = describe_camera_controller_update(
        _instances(mode=2), elapsed_u32=100, feedback_flag=True, timer=1.0
    )
    mode_action = result["instances"][0]["actions"][1]
    assert mode_action["conditional_reissue"]["action"] == "FUN_0080c230(outer_manager, +0x26a4, +0x26a4)"
    assert mode_action["post_reissue_branches"][0]["action"].startswith("FUN_00812050")


def test_mode_one_successful_view_check_leaves_feedback_flag_cleared():
    instances = _instances(mode=1)
    instances = [
        CameraControllerInstance(
            **{**instance.__dict__, "view_check_sub_index": True}
        )
        for instance in instances
    ]
    result = describe_camera_controller_update(
        instances, elapsed_u32=100, feedback_flag=True, timer=1.0
    )
    assert result["feedback_flag_after_observed_mode1_fallback"] is False
    mode_action = result["instances"][0]["actions"][1]
    assert mode_action["fallback"]["action"] == "no FUN_0080c230 fallback"


def test_mode_one_clears_feedback_and_sets_it_after_failed_view_check():
    result = describe_camera_controller_update(
        _instances(mode=1), elapsed_u32=100, feedback_flag=True, timer=1.0
    )
    assert result["feedback_flag_before"] is True
    assert result["feedback_flag_after_observed_mode1_fallback"] is True
    mode_action = result["instances"][0]["actions"][1]
    assert mode_action["actions"] == ["+0x82e = 0"]
    assert "+0x82e = 1" in mode_action["fallback"]["then"]


def test_timer_subtracts_scaled_elapsed_and_clamps_at_zero():
    result = describe_camera_controller_update(
        _instances(mode=2), elapsed_u32=1500, feedback_flag=False, timer=1.0
    )
    assert result["timer"]["after_subtract"] == -0.5
    assert result["timer"]["after_clamp"] == 0.0
    assert result["timer"]["clamped_to_zero"] is True


def test_special_binding_emits_both_proven_helpers_only_when_symbol_is_present():
    result = describe_camera_controller_update(
        _instances(), elapsed_u32=10, feedback_flag=False, timer=1.0,
        special_binding_present=True,
    )
    assert result["special_binding"]["actions"] == [
        "FUN_0081b340(FUN_0080bdd0(this,0), +0x810)",
        "FUN_0081b330(FUN_0080bdd0(this,0), +0x814)",
    ]
