from camera_view_input_control_runtime import (
    describe_camera_input_control,
    describe_cockpit_profile_blend,
    low_byte_nonzero,
)


def test_low_byte_predicate_uses_only_low_eight_bits():
    assert low_byte_nonzero(0x100)
    assert not low_byte_nonzero(0x20000)


def test_camera_service_guard_enables_or_disables_frame_stack():
    enabled = describe_camera_input_control(
        camera_service_ready=True,
        profile_present=True,
        profile_cockpit_flag=True,
        action1_bit1=False,
        action2_bit1=False,
        action5_bit0=False,
        param4_low_byte_nonzero=False,
        param5_low_byte_zero=False,
        current_cockpit_state=False,
        profile_has_cockpit_semantics=False,
        global_gate_c25f08=False,
    )
    assert enabled["frame_stack_state"] == "enabled"

    disabled = describe_camera_input_control(
        camera_service_ready=False,
        profile_present=False,
        profile_cockpit_flag=False,
        action1_bit1=False,
        action2_bit1=False,
        action5_bit0=False,
        param4_low_byte_nonzero=False,
        param5_low_byte_zero=True,
        current_cockpit_state=False,
        profile_has_cockpit_semantics=False,
        global_gate_c25f08=False,
    )
    assert disabled["frame_stack_state"] == "disabled"


def test_look_behind_flag_write_requires_exact_three_part_guard():
    result = describe_camera_input_control(
        camera_service_ready=True,
        profile_present=False,
        profile_cockpit_flag=False,
        action1_bit1=True,
        action2_bit1=False,
        action5_bit0=False,
        param4_low_byte_nonzero=False,
        param5_low_byte_zero=True,
        current_cockpit_state=False,
        profile_has_cockpit_semantics=False,
        global_gate_c25f08=False,
    )
    assert any(x["action"] == "write manager +0x2a74" for x in result["actions"])


def test_look_behind_flag_is_blocked_by_global_guard():
    result = describe_camera_input_control(
        camera_service_ready=True,
        profile_present=False,
        profile_cockpit_flag=False,
        action1_bit1=True,
        action2_bit1=False,
        action5_bit0=False,
        param4_low_byte_nonzero=False,
        param5_low_byte_zero=True,
        current_cockpit_state=False,
        profile_has_cockpit_semantics=False,
        global_gate_c25f08=True,
    )
    assert not any(x["action"] == "write manager +0x2a74" for x in result["actions"])


def test_cockpit_output_is_computed_from_action2_param4_and_profile_flag():
    result = describe_camera_input_control(
        camera_service_ready=True,
        profile_present=True,
        profile_cockpit_flag=True,
        action1_bit1=False,
        action2_bit1=True,
        action5_bit0=True,
        param4_low_byte_nonzero=False,
        param5_low_byte_zero=False,
        current_cockpit_state=False,
        profile_has_cockpit_semantics=True,
        global_gate_c25f08=False,
    )
    assert result["cockpit_state_computed"] is True
    assert any(x["action"] == "write manager +0x2a75" for x in result["actions"])


def test_action5_bit_zero_sets_d3_zero():
    result = describe_camera_input_control(
        camera_service_ready=True,
        profile_present=False,
        profile_cockpit_flag=False,
        action1_bit1=False,
        action2_bit1=False,
        action5_bit0=False,
        param4_low_byte_nonzero=False,
        param5_low_byte_zero=False,
        current_cockpit_state=False,
        profile_has_cockpit_semantics=False,
        global_gate_c25f08=False,
    )
    assert result["actions"][1]["action"] == "write +0xd3"
    assert result["actions"][1]["value"] == 0


def test_cockpit_profile_branch_exposes_the_three_numeric_predicates():
    result = describe_cockpit_profile_blend(
        has_cockpit_semantics=True,
        local_c=0.2,
        local_8=0.05,
        current_84=1,
        current_88=2,
        delta=0.1,
    )
    assert result["predicates"]["local_c_abs_gt_0.1"] is True
    assert result["predicates"]["local_8_abs_le_0.1"] is True
    assert len(result["branch_actions"]) == 3


def test_non_cockpit_profile_uses_non_cockpit_branch():
    result = describe_cockpit_profile_blend(
        has_cockpit_semantics=False,
        local_c=0,
        local_8=0,
        current_84=1,
        current_88=2,
        delta=0.1,
    )
    assert result["branch_actions"][0]["action"] == "use non-cockpit branch"
