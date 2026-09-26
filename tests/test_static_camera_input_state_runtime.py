from static_camera_input_state_runtime import (
    clamp_static_camera_direction_input,
    copy_static_camera_runtime_state,
    load_static_camera_entry,
    lookup_static_camera_slot,
    reset_static_camera_input_state,
    update_static_camera_controller,
)


def test_static_entry_loader_preserves_factory_and_manager_methods():
    result = load_static_camera_entry(
        source_entry="entry",
        manager_service_present=True,
        property_setup_succeeded=True,
    )
    assert result["status"] == "loaded"
    assert any(a["action"] == "manager vtable +0x20" for a in result["actions"])


def test_runtime_state_copy_contains_exactly_eleven_dwords():
    result = copy_static_camera_runtime_state(list(range(20)))
    assert result["count"] == 11
    assert result["offset_range"] == ["+0x00", "+0x28"]
    assert result["values"] == list(range(11))


def test_controller_update_selects_forward_or_reverse_method():
    forward = update_static_camera_controller(
        controller_present=True,
        parameter="p",
        reverse_flag=False,
        controller_result="r",
        mode_value=2,
    )
    reverse = update_static_camera_controller(
        controller_present=True,
        parameter="p",
        reverse_flag=True,
    )
    assert forward["actions"][1]["action"] == "controller vtable +0x98"
    assert reverse["actions"][1]["action"] == "controller vtable +0x94"


def test_slot_lookup_uses_0x34_stride():
    result = lookup_static_camera_slot(state_offset=3)
    assert result["source_offset"] == 0xD4 + 3 * 0x34


def test_reset_writes_minus_one_based_on_slot_count():
    result = reset_static_camera_input_state(
        camera_slot_index=2,
        slot_count=7,
    )
    assert result["writes"]["+0x37c"] == 6


def test_direction_input_clamps_both_values_to_one():
    result = clamp_static_camera_direction_input(
        camera_type=4,
        value=2.0,
        opposite_value=2.0,
    )
    assert result["writes"]["+0x33c"] == 1.0
    assert result["writes"]["+0x340"] == -1.0


def test_unsupported_camera_type_clears_direction_state():
    result = clamp_static_camera_direction_input(
        camera_type=7,
        value=0.4,
        opposite_value=0.2,
    )
    assert result["status"] == "unsupported-camera-type"
    assert result["writes"] == {"+0x33c": 0, "+0x340": 0}
