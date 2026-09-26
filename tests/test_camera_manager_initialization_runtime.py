from camera_manager_initialization_runtime import (
    describe_camera_manager_global_init,
    describe_camera_manager_slot_init,
    describe_double_buffer_selector,
)


def test_global_init_resets_double_buffer_and_dirty_fields():
    result = describe_camera_manager_global_init(generated_hash_value=7)
    assert result["writes"]["+0x2560"] == 0
    assert result["writes"]["+0x2574"] == 0xFFFFFFFF
    assert result["writes"]["+0x269c"] == 0
    assert result["writes"]["+0x269d"] == 0
    assert result["actions"][2]["condition"] == "+0x2688 == 0"


def test_slot_init_clears_both_views_and_reselects_profile_minus_one():
    result = describe_camera_manager_slot_init()
    assert [a["target"] for a in result["actions"] if a["action"] == "FUN_0081c8f0"] == [
        "+0x20", "+0xbe0"
    ]
    assert [a["target"] for a in result["actions"] if a["action"] == "FUN_0081caa0"] == [
        "+0x20", "+0xbe0"
    ]


def test_slot_init_runs_source_vtable_reset_on_four_camera_objects():
    result = describe_camera_manager_slot_init()
    source_action = next(a for a in result["actions"] if a["action"] == "camera-source.vtable +0x90")
    assert source_action["targets"] == ["+0x17a0", "+0x1a20", "+0x1ca0", "+0x2100"]


def test_slot_init_has_four_profile_blocks():
    result = describe_camera_manager_slot_init()
    profile_action = next(a for a in result["actions"] if a["action"] == "initialize profile blocks")
    assert profile_action["targets"] == ["+0x26b8", "+0x2780", "+0x2848", "+0x2910"]


def test_buffer_selector_flips_zero_to_one_and_one_to_zero():
    assert describe_double_buffer_selector(old_index=0)["new_index"] == 1
    assert describe_double_buffer_selector(old_index=1)["new_index"] == 0
