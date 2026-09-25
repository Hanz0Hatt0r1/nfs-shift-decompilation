from camera_transition_runtime import (
    CameraTransitionState,
    describe_external_view_source,
    describe_static_camera_activation,
    describe_static_view_switch,
    describe_tracking_camera_activation,
    describe_tracking_flag_update,
)


def test_static_view_switch_deactivates_old_group_before_gate_when_needed():
    result = describe_static_view_switch(
        CameraTransitionState(active_group=4, camera_id=9),
        requested_group=7,
        requested_sub_index=3,
        sub_flag=0xFF,
    )
    actions = result["actions"]
    assert actions[0]["action"] == "FUN_0080ce10"
    assert actions[1]["action"] == "FUN_0080cdf0"
    assert actions[2]["action"] == "FUN_0080d3d0"
    assert actions[2]["arguments"]["mode"] == 1
    assert actions[-2]["action"] == "FUN_0080d500"
    assert actions[-1]["value"] == -1


def test_static_view_switch_does_not_deactivate_missing_or_same_group():
    for group in (-1, 4):
        result = describe_static_view_switch(
            CameraTransitionState(active_group=group),
            requested_group=4,
            requested_sub_index=0,
            sub_flag=0,
        )
        assert result["actions"][0]["action"] == "FUN_0080d3d0"


def test_tracking_activation_uses_mode_two_and_tracking_buffer():
    result = describe_tracking_camera_activation(runtime_argument="tracking*", camera_id=5)
    assert result["mode"] == 2
    assert result["actions"][0]["arguments"]["sub_index"] == -1
    assert result["actions"][1]["action"].startswith("active_buffer +0x1ca0")


def test_static_activation_uses_mode_three_and_static_buffer():
    result = describe_static_camera_activation(runtime_argument="static*", camera_id=6)
    assert result["mode"] == 3
    assert result["actions"][1]["action"].startswith("active_buffer +0x17a0")


def test_external_source_parameter_zero_rolls_back_before_any_source_switch():
    result = describe_external_view_source(
        source="external-A", parameter=0, current_source="external-B"
    )
    assert result["status"] == "rollback"
    assert result["actions"][1]["action"] == "FUN_0080d4a0"


def test_external_source_same_pointer_stops_after_preapply_helper():
    result = describe_external_view_source(
        source="external-A", parameter=1, current_source="external-A"
    )
    assert result["status"] == "same-source-no-switch"
    assert len(result["actions"]) == 1


def test_external_source_change_uses_mode_four_then_apply():
    result = describe_external_view_source(
        source="external-A", parameter=1, current_source="external-B"
    )
    assert result["actions"][1]["arguments"]["mode"] == 4
    assert result["actions"][2]["arguments"]["mode"] == 4


def test_tracking_flag_is_blocked_during_swap_and_applied_otherwise():
    busy = describe_tracking_flag_update(
        update_flag=1,
        manager_busy=True,
        active_camera_source_present=True,
        active_sub_index=4,
    )
    assert busy["status"] == "busy-no-op"

    ready = describe_tracking_flag_update(
        update_flag=0xFF,
        manager_busy=False,
        active_camera_source_present=True,
        active_sub_index=7,
    )
    assert ready["actions"][1]["arguments"]["sub_flag"] == 0xFF
    assert ready["actions"][2]["arguments"]["sub_index"] == 7
