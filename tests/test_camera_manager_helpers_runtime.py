from camera_manager_helpers_runtime import (
    describe_camera_input_command,
    describe_camera_service_gate,
    describe_external_source_to_slot,
    describe_secondary_camera_dispatch,
    describe_slot_is_static_camera,
    describe_slot_ready_predicate,
    describe_slot_refresh_request,
    slot_address,
    slot_camera_source,
    slot_ready_state,
    slot_sync_object,
)


def test_slot_address_uses_exact_manager_offset_and_stride():
    assert slot_address(0x1000, 2) == 0x1000 + 0x290 + 2 * 0x2AA0


def test_slot_queries_keep_distinct_source_sync_and_ready_offsets():
    assert slot_camera_source("mgr", 1)["field"] == "+0x2568"
    assert slot_sync_object("mgr", 1)["field"] == "+0x2580"
    assert slot_ready_state("mgr", 1)["field"] == "+0x2688"


def test_secondary_dispatch_is_blocked_when_global_service_flag_is_zero():
    result = describe_secondary_camera_dispatch(
        service_enabled=False,
        requested_first=1,
        requested_second=2,
        requested_camera_id=3,
        slot_index=0,
    )
    assert result["status"] == "service-disabled"
    assert result["actions"] == []


def test_secondary_dispatch_forwards_exact_arguments_when_enabled():
    result = describe_secondary_camera_dispatch(
        service_enabled=True,
        requested_first=1,
        requested_second=2,
        requested_camera_id=3,
        slot_index=2,
    )
    assert result["actions"][0]["action"] == "FUN_0080e1b0"
    assert result["actions"][0]["arguments"]["slot_index"] == 2
    assert result["actions"][0]["arguments"]["camera_id"] == 3


def test_external_source_to_slot_targets_requested_slot():
    result = describe_external_source_to_slot(source="ext", parameter=1, slot_index=2)
    assert result["actions"][0]["target"] == "slot[2]"
    assert result["actions"][0]["arguments"]["source"] == "ext"


def test_refresh_request_sets_payload_field_then_refresh_bit():
    result = describe_slot_refresh_request(value=7, slot_index=1)
    assert result["actions"] == [
        {"action": "write +0x268c", "value": 7},
        {"action": "write +0x2698", "value": 1},
    ]


def test_ready_predicate_requires_not_busy_and_state_one():
    assert describe_slot_ready_predicate(busy=False, lifecycle_state=1)["result"]
    assert not describe_slot_ready_predicate(busy=True, lifecycle_state=1)["result"]
    assert not describe_slot_ready_predicate(busy=False, lifecycle_state=0)["result"]


def test_camera_input_command_keeps_be50_follow_up_in_order():
    result = describe_camera_input_command(command_id=4, command_data={"x": 1})
    assert result["actions"][0]["action"] == "FUN_008127c0"
    assert result["actions"][1]["action"] == "FUN_0080be50"


def test_static_camera_predicate_preserves_opaque_type_result():
    result = describe_slot_is_static_camera(busy=False, camera_type_result=1)
    assert result["result"] is True
    result = describe_slot_is_static_camera(busy=False, camera_type_result=2)
    assert result["result"] is False
