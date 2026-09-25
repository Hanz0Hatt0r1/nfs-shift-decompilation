from camera_view_data_runtime import (
    camera_view_property_offsets,
    copy_camera_view_data,
    initialize_camera_view_data,
    reset_camera_view_data,
)


def test_init_preserves_special_sentinel_defaults():
    result = initialize_camera_view_data()
    assert result["writes"]["+0x40"] == 0xFFFFFFFF
    assert result["writes"]["+0x44"] == 0xFFFFFFFF
    assert result["writes"]["+0x48"] == 0xFFFFFFFF
    assert result["writes"]["+0x4c"] == 0
    assert result["writes"]["+0x50"] == 1
    assert result["writes"]["+0x54"] == 0


def test_init_delegates_two_container_regions_to_23bc0():
    result = initialize_camera_view_data()
    assert result["writes"]["+0x60_container"] == "FUN_00823bc0"
    assert result["writes"]["+0xac_container"] == "FUN_00823bc0"


def test_reset_clears_exact_0x100_bytes_then_selected_object_and_stack_fields():
    result = reset_camera_view_data(frame_stack_base="+0x60")
    assert result["actions"][0]["size"] == 0x100
    assert result["actions"][1] == {"action": "write +0x80", "value": 0}
    assert result["actions"][2] == {"action": "write +0x60", "value": 0}


def test_copy_matches_dword_byte_and_tail_boundaries():
    source_words = {offset: offset for offset in range(0, 0x50, 4)}
    source_words[0x54] = 0x12345678
    result = copy_camera_view_data(
        source_words,
        source_bytes={0x50: 1, 0x51: 2, 0x52: 3, 0x53: 4},
    )
    assert result["dword_copies"]["+0x00"] == 0
    assert result["dword_copies"]["+0x4c"] == 0x4C
    assert result["byte_copies"] == {"+0x50": 1, "+0x51": 2, "+0x52": 3, "+0x53": 4}
    assert result["tail_dword"]["value"] == 0x12345678


def test_copy_exposes_both_opaque_14340_regions():
    source_words = {offset: offset for offset in range(0, 0x50, 4)}
    result = copy_camera_view_data(
        source_words,
        source_bytes={0x50: 0, 0x51: 0, 0x52: 0, 0x53: 0},
    )
    assert result["helper_copies"][0]["destination"] == "+0x58"
    assert result["helper_copies"][1]["destination"] == "+0xac"


def test_property_offsets_keep_semantic_registration_names():
    offsets = camera_view_property_offsets()
    assert offsets["FOV"] == 0x54
    assert offsets["AspectRatio"] == 0x60
    assert offsets["FarZ"] == 0x68
    assert offsets["HideCar"] == 0xAC
    assert offsets["RenderCockpit"] == 0xAE
