from tracking_camera_runtime import (
    clear_tracking_input_slots,
    copy_tracking_camera_state,
    describe_tracking_camera_constructor,
    describe_tracking_free_look_factory,
    register_tracking_input,
    tracking_data_defaults,
    tracking_property_registration,
)


def test_tracking_data_defaults_preserve_sentinels_and_units():
    result = tracking_data_defaults()
    assert result["writes"]["+0x00"] == 0x3F800000
    assert result["writes"]["+0x44"] == 0
    assert result["writes"]["+0x48"] == 0x3F800000
    assert result["writes"]["+0x50"] == 0xFFFFFFFF
    assert result["writes"]["+0x54"] == 0xFFFFFFFF
    assert result["writes"]["+0x60"] == 0x3F800000


def test_tracking_constructor_sets_exact_spline_defaults():
    result = describe_tracking_camera_constructor()
    assert result["writes"]["+0xf8"] == 0xFFFFFFFF
    assert result["writes"]["+0xfc"] == 0
    assert result["writes"]["+0x100"] == 0
    assert result["writes"]["+0x108"] == 0


def test_tracking_copy_contains_tracking_fields_and_resets_runtime_accumulators():
    source = {offset: offset for offset in (
        0xf0, 0xf4, 0xf8, 0xfc, 0x100, 0x101,
        0x104, 0x108, 0x128, 0x12c, 0x130, 0x134,
        0x138, 0x13c, 0x140, 0x144, 0x148,
    )}
    result = copy_tracking_camera_state(source)
    assert result["copies"]["+0xf8"] == 0xf8
    assert "+0x114" in result["reset_fields"]


def test_tracking_property_registration_matches_all_seventeen_fields():
    result = tracking_property_registration()
    assert len(result["properties"]) == 17
    props = {p["name"]: p for p in result["properties"]}
    assert props["MovementRate"]["offset"] == 0xf0
    assert props["SplineID"]["type_id"] == 0x0D
    assert props["bAutoZoom"]["type_id"] == 0x20
    assert props["OnTargetSplineEndReached"]["offset"] == 0x148


def test_tracking_input_slots_are_seven_and_valid_indices_one_to_six():
    slots = clear_tracking_input_slots([1,2,3,4,5,6,7])
    slots, result = register_tracking_input(
        slots, action_index=3, action_object="free-look", frame_stack_accepts=True
    )
    assert slots[3] == "free-look"
    assert result["storage_offset"] == 0x44C


def test_tracking_free_look_factory_registers_slots_three_and_four():
    result = describe_tracking_free_look_factory()
    assert [x["registered_index"] for x in result["actions"]] == [3, 4]
