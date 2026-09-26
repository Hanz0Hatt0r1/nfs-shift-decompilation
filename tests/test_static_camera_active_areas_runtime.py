from static_camera_active_areas_runtime import (
    append_active_area,
    deserialize_active_areas,
    initialize_static_camera_runtime,
    serialize_active_areas,
)


def test_active_area_append_masks_to_uint16():
    result = append_active_area([], 0x12345)
    assert result["stored_value"] == 0x2345
    assert result["stored_indices"] == [0x2345]


def test_static_camera_runtime_initializer_has_two_shake_resets():
    result = initialize_static_camera_runtime()
    assert result["writes"]["+0x48"] == 6
    assert result["writes"]["+0x4c"] == 6
    assert [x["target"] for x in result["shake_resets"]] == ["+0x3c", "+0x90"]


def test_active_areas_save_uses_zero_based_property_names():
    result = serialize_active_areas(indices=[1, 2, 3])
    assert [x["name"] for x in result["elements"]] == [
        "areaIndex0", "areaIndex1", "areaIndex2"
    ]
    assert result["elements"][1]["value"] == 2


def test_active_areas_load_uses_one_based_property_names_from_source_loop():
    result = deserialize_active_areas(values=[1, 65537])
    assert [x["name"] for x in result["elements"]] == [
        "areaIndex1", "areaIndex2"
    ]
    assert result["stored_indices"] == [1, 1]
