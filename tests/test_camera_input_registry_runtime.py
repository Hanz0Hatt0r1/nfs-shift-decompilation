from camera_input_registry_runtime import (
    clear_input_action_slots,
    describe_input_action_registry_state,
    lookup_input_action,
    register_input_action,
)


def test_clear_requires_exactly_seven_storage_slots():
    assert clear_input_action_slots([1, 2, 3, 4, 5, 6, 7]) == [None] * 7


def test_register_rejects_invalid_indices():
    slots = [None] * 7
    _, result = register_input_action(
        slots,
        action_index=0,
        action_object="x",
        frame_stack_accepts=True,
    )
    assert result["status"] == "rejected-index"


def test_register_accepts_only_empty_valid_slot_with_frame_stack_success():
    slots = [None] * 7
    updated, result = register_input_action(
        slots,
        action_index=3,
        action_object="action3",
        frame_stack_accepts=True,
    )
    assert updated[3] == "action3"
    assert result["storage_offset"] == 0x2A0 + 3 * 4


def test_register_rejects_occupied_slot():
    slots = [None] * 7
    slots[2] = "existing"
    _, result = register_input_action(
        slots,
        action_index=2,
        action_object="new",
        frame_stack_accepts=True,
    )
    assert result["status"] == "rejected-slot-occupied"


def test_register_rejects_when_frame_stack_helper_fails():
    slots = [None] * 7
    _, result = register_input_action(
        slots,
        action_index=2,
        action_object="action2",
        frame_stack_accepts=False,
    )
    assert result["status"] == "rejected-frame-stack"


def test_lookup_returns_fallback_for_empty_or_invalid_slot():
    slots = [None] * 7
    assert lookup_input_action(slots, action_index=6)["value"] == "DAT_00c25f30"
    assert lookup_input_action(slots, action_index=99)["value"] == "DAT_00c25f30"


def test_lookup_returns_exact_registered_object():
    slots = [None] * 7
    slots[4] = "action4"
    result = lookup_input_action(slots, action_index=4)
    assert result["status"] == "found"
    assert result["storage_offset"] == 0x2A0 + 4 * 4


def test_registry_state_exposes_raw_container_shape():
    result = describe_input_action_registry_state([None] * 7)
    assert result["slot_base"] == 0x2A0
    assert result["valid_indices"] == [1, 2, 3, 4, 5, 6]
