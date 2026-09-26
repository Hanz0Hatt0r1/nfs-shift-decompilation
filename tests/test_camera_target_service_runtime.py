from camera_target_service_runtime import (
    clear_tracking_input_slots,
    combine_shake_orientation,
    create_tracking_free_look_actions,
    find_and_assign_tracking_target,
    forward_target_value,
    parse_camera_type_selector,
    query_target_metadata,
    register_tracking_input_action,
    register_tracking_runtime_properties,
    resolve_active_target_data,
    resolve_target_transform,
    set_tracking_target,
)


def test_set_tracking_target_writes_e8():
    result = set_tracking_target({}, "target")
    assert result["state"]["+0xe8"] == "target"


def test_input_registry_uses_valid_indices_one_through_six():
    slots = clear_tracking_input_slots([1,2,3,4,5,6,7])
    slots, result = register_tracking_input_action(
        slots, action_index=5, action_object="look", frame_stack_accepts=True
    )
    assert slots[5] == "look"
    assert result["storage_offset"] == 0x274


def test_target_acquisition_prefers_rtti_matching_candidate():
    result = find_and_assign_tracking_target(
        target_handle_present=True,
        target_handle_nonempty=True,
        candidates=[
            {"contains_rtti_0xc25fb8": False, "field_0x60_matches_target": True},
            {"contains_rtti_0xc25fb8": True, "field_0x60_matches_target": True},
        ],
    )
    assert result["status"] == "assigned"
    assert result["selected"] == 1


def test_target_acquisition_falls_back_to_string_when_no_match():
    result = find_and_assign_tracking_target(
        target_handle_present=True,
        target_handle_nonempty=True,
        candidates=[],
    )
    assert result["status"] == "fallback-selector"


def test_runtime_properties_match_needs_reset_and_is_shaking():
    result = register_tracking_runtime_properties()
    props = {p["name"]: p for p in result["properties"]}
    assert props["NeedsReset"]["offset"] == 0x68
    assert props["IsShaking"]["offset"] == 0x69


def test_free_look_factory_registers_three_actions():
    result = create_tracking_free_look_actions()
    assert [a["registered_index"] for a in result["actions"]] == [3, 4, 5]
    assert result["actions"][2]["binding"] == [3,0,1,7]


def test_camera_type_parser_rejects_0f_and_writes_6c_otherwise():
    assert parse_camera_type_selector(
        text_value="x", opaque_selector_result=0x0F
    )["result"] == 0
    accepted = parse_camera_type_selector(
        text_value="x", opaque_selector_result=4
    )
    assert accepted["write_offset"] == 0x6C


def test_target_transform_uses_id_query_then_local_fallback():
    result = resolve_target_transform(
        service_available=True,
        target_id=2,
        param3="a",
        param4="b",
        this_has_fallback_position=False,
        fallback_position=[1,2,3],
        service_call_result="typed",
    )
    assert result["status"] == "id-query"

    fallback = resolve_target_transform(
        service_available=True,
        target_id=-1,
        param3="a",
        param4="b",
        this_has_fallback_position=True,
        fallback_position=[1,2,3],
    )
    assert fallback["result"] == [1.0,2.0,3.0]


def test_target_value_and_metadata_helpers_keep_service_outputs_opaque():
    forwarded = forward_target_value(
        service_available=True, target_id=2, value="v", service_result="out"
    )
    assert forwarded["result"] == "out"
    metadata = query_target_metadata(
        service_available=True, target_id=2, metadata=[1,2,3]
    )
    assert metadata["result"] == [1.0,2.0,3.0]


def test_shake_orientation_adds_two_vec3_outputs():
    result = combine_shake_orientation(
        first_output=[1,2,3],
        second_output=[4,5,6],
    )
    assert result["combined"] == [5.0,7.0,9.0]


def test_active_target_data_follows_e8_redirect():
    result = resolve_active_target_data(target_data="primary", nested_target_data="nested")
    assert result["result"] == "nested"
