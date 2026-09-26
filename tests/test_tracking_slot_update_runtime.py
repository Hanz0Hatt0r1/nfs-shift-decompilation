from tracking_slot_update_runtime import (
    update_tracking_slot,
    validate_collection_slot,
)


def test_invalid_collection_slot_is_reset_to_zero():
    result = validate_collection_slot(
        selected_index=5,
        per_mode_count=3,
    )
    assert result["selected_index"] == 0
    assert result["reset_to_zero"] is True


def test_valid_collection_slot_is_preserved():
    result = validate_collection_slot(
        selected_index=2,
        per_mode_count=3,
    )
    assert result["selected_index"] == 2


def test_tracking_slot_updates_controller_then_endpoints_in_order():
    result = update_tracking_slot(
        selected_index=2,
        per_mode_count=4,
        object_controller_id=3,
        object_secondary_spline_id=4,
        object_metadata=[1,2,3],
        reverse_mode=False,
        controller_present=True,
        needs_resync=True,
        primary_endpoint_result={"record":[10,11,12], "scalar":13},
        secondary_endpoint_result={"record":[20,21,22], "scalar":23},
    )
    names = [a["action"] for a in result["actions"]]
    assert names.index("FUN_008164f0") < names.index("FUN_00817120")
    assert names.index("FUN_00817120") < names.index("FUN_00816120")
    assert result["state_writes"]["+0x2dc"] == 10
    assert result["state_writes"]["+0x318"] == 20


def test_reverse_mode_uses_11640_for_both_endpoints():
    result = update_tracking_slot(
        selected_index=0,
        per_mode_count=1,
        object_controller_id=1,
        object_secondary_spline_id=2,
        object_metadata=[0,0,0],
        reverse_mode=True,
        controller_present=True,
        needs_resync=False,
        primary_endpoint_result={"record":[1,2,3], "scalar":4},
        secondary_endpoint_result={"record":[5,6,7], "scalar":8},
    )
    endpoint_actions = [
        a for a in result["actions"]
        if a["action"] == "FUN_00811640"
    ]
    assert len(endpoint_actions) == 2


def test_wheel_angle_is_degrees_to_radians_and_valid_flag():
    result = update_tracking_slot(
        selected_index=0,
        per_mode_count=1,
        object_controller_id=1,
        object_secondary_spline_id=-1,
        object_metadata=[0,0,0],
        reverse_mode=False,
        controller_present=True,
        needs_resync=False,
        wheel_property_name="WheelAngle",
        wheel_property_value_degrees=180,
    )
    assert abs(result["wheel_angle_radians"] - 3.14159256) < 1e-6
    assert result["wheel_angle_valid"] is True


def test_non_wheel_property_is_invalid():
    result = update_tracking_slot(
        selected_index=0,
        per_mode_count=1,
        object_controller_id=1,
        object_secondary_spline_id=-1,
        object_metadata=[0,0,0],
        reverse_mode=False,
        controller_present=True,
        needs_resync=False,
        wheel_property_name="Other",
    )
    assert result["wheel_angle_valid"] is False
