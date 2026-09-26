from camera_dynamic_array_runtime import (
    grow_dword11_array,
    grow_uint16_array,
    next_dword11_element_address,
    next_uint16_element_address,
)


def test_uint16_growth_preserves_elementwise_copy_mode():
    result = grow_uint16_array(
        element_stride=2,
        old_count=3,
        old_capacity=3,
        source_storage=[1, 2, 3],
        copy_memcpy_mode=False,
        new_capacity=6,
    )
    assert result["copy_method"] == "elementwise_uint16"
    assert result["copied_elements"] == [1, 2, 3]


def test_uint16_growth_preserves_memcpy_mode():
    result = grow_uint16_array(
        element_stride=2,
        old_count=2,
        old_capacity=2,
        source_storage=[10, 11],
        copy_memcpy_mode=True,
        new_capacity=4,
    )
    assert result["copy_method"] == "memcpy_s"


def test_uint16_next_address_is_stride_times_index_plus_base():
    result = next_uint16_element_address(
        element_stride=2,
        current_index=4,
        base_offset=0x20,
    )
    assert result["address_offset"] == 0x28


def test_dword11_growth_requires_exactly_eleven_dwords_per_element():
    result = grow_dword11_array(
        element_stride=0x2c,
        old_count=1,
        old_capacity=1,
        source_storage=[[0] * 11],
        copy_memcpy_mode=False,
        new_capacity=2,
    )
    assert result["copy_method"] == "elementwise_11_dword"
    assert result["copied_elements"] == [[0] * 11]


def test_dword11_growth_preserves_memcpy_mode():
    result = grow_dword11_array(
        element_stride=0x2c,
        old_count=1,
        old_capacity=1,
        source_storage=[[1] * 11],
        copy_memcpy_mode=True,
        new_capacity=2,
    )
    assert result["copy_method"] == "memcpy_s"


def test_dword11_next_address_uses_same_formula():
    result = next_dword11_element_address(
        element_stride=0x2c,
        current_index=3,
        base_offset=0x10,
    )
    assert result["address_offset"] == 0x94
