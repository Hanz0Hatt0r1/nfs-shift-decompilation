from camera_event_handlers_runtime import (
    describe_event_type_0,
    describe_event_type_1,
    describe_event_type_2,
    describe_event_type_3,
)


def test_type_zero_writes_outer_camera_command_field_then_static_switch():
    result = describe_event_type_0(argument_a=7, argument_b=3)
    assert result["actions"][0]["value"] == 7
    assert result["actions"][1]["action"] == "FUN_0080de00"
    assert result["actions"][1]["slot_index"] == 0


def test_type_one_falls_back_to_static_handler_outside_modes_two_and_three():
    result = describe_event_type_1(
        argument_a=7, argument_b=8, active_mode=1, active_camera_id=5
    )
    assert result["path"] == "fallback-static"
    assert result["actions"][0]["action"] == "FUN_0080b910"
    assert result["actions"][0]["arguments"]["second"] == -2


def test_type_one_uses_be50_in_modes_two_and_three():
    result = describe_event_type_1(
        argument_a=7, argument_b=8, active_mode=3, active_camera_id=9
    )
    assert result["path"] == "mode-2-or-3"
    assert result["actions"][0]["arguments"]["camera_id"] == 9


def test_type_two_forwards_group_change_in_modes_two_and_three():
    result = describe_event_type_2(argument_a=4, argument_b=5, active_mode=2)
    assert result["path"] == "mode-2-or-3"
    assert result["actions"][0]["action"] == "FUN_0080b910"


def test_type_two_non_mode_path_resets_service_flag_and_records_timestamp_update():
    result = describe_event_type_2(argument_a=4, argument_b=5, active_mode=1)
    assert result["path"] == "non-mode-2/3"
    assert result["actions"][1]["value"] == 0
    assert "+0x2ec" in result["actions"][2]["action"]


def test_type_two_minus_one_skips_be50_but_keeps_mode_side_effects():
    result = describe_event_type_2(argument_a=-1, argument_b=5, active_mode=1)
    assert result["actions"][0]["status"] == "skipped"
    assert result["actions"][1]["value"] == 0


def test_type_three_keeps_extraout_dl_opaque_when_source_is_not_resolved():
    result = describe_event_type_3(
        argument_a=1, argument_b=2, active_mode=2, incoming_mode_flag=None
    )
    assert result["path"] == "opaque-flag-compare"
    assert result["condition"]["right"] == "extraout_DL (unresolved)"


def test_type_three_selects_bf30_when_mode_flag_matches():
    result = describe_event_type_3(
        argument_a=1, argument_b=2, active_mode=3, incoming_mode_flag=True
    )
    assert result["next_handler"] == "FUN_0080bf30"


def test_type_three_selects_c230_when_mode_flag_differs():
    result = describe_event_type_3(
        argument_a=1, argument_b=2, active_mode=3, incoming_mode_flag=False
    )
    assert result["next_handler"] == "FUN_0080c230"
