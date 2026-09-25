from camera_event_queue_runtime import (
    describe_enqueue_boundary,
    describe_record_allocator,
    describe_type3_copy,
    describe_type3_producer,
    describe_type5_producer,
)


def test_type5_allocator_is_24_bytes_with_six_dword_copy_footprint():
    result = describe_record_allocator(5)
    assert result["allocation_size"] == 0x18
    assert result["copy_footprint"]["offsets"] == [0x0C, 0x10, 0x14, 0x18, 0x1C, 0x20]


def test_type3_allocator_is_36_bytes_and_copies_two_dwords_plus_byte():
    result = describe_record_allocator(3)
    assert result["allocation_size"] == 0x24
    assert result["copy_footprint"]["offsets"] == [0x0C, 0x10, 0x14]


def test_type5_producer_preserves_six_raw_u32_words_and_enqueues_after_builder():
    result = describe_type5_producer([-1, -2, 0, 1, 2, 3])
    assert result["actions"][0]["action"] == "FUN_0080c340"
    assert result["actions"][1]["action"] == "FUN_0080b9b0"
    assert result["actions"][1]["payload_words"][:2] == [0xFFFFFFFF, 0xFFFFFFFE]
    assert result["actions"][2]["action"] == "FUN_0080c7e0"


def test_type5_producer_requires_exact_six_words():
    try:
        describe_type5_producer([1, 2])
    except ValueError:
        return
    raise AssertionError("expected six-word requirement")


def test_type3_producer_preserves_payload_and_header_finalization_order():
    result = describe_type3_producer(first=1, second=2, byte_parameter=0xFF)
    assert result["actions"][1]["payload"]["+0x0c"] == 1
    assert result["actions"][1]["payload"]["+0x14"] == 0xFF
    assert result["actions"][2]["type"] == 3
    assert result["actions"][3]["action"] == "FUN_0080cb50"


def test_type3_copy_matches_three_source_fields():
    result = describe_type3_copy(source_payload_words=[11, 22], source_byte=0xFF)
    assert result["actions"][1]["offset"] == 0x0C
    assert result["actions"][2]["offset"] == 0x10
    assert result["actions"][3]["offset"] == 0x14
    assert result["actions"][3]["value"] == 255


def test_same_container_uses_direct_generic_enqueue_boundary():
    result = describe_enqueue_boundary(
        container_is_same_as_record=True,
        record_type=5,
    )
    assert result["enqueue_path"]["action"] == "FUN_006333f0"


def test_different_container_clones_type5_through_c400_before_append():
    result = describe_enqueue_boundary(
        container_is_same_as_record=False,
        record_type=5,
    )
    assert result["enqueue_path"]["sequence"][1] == "FUN_0080c400(local_8,record)"


def test_different_container_clones_type3_through_c8f0_before_append():
    result = describe_enqueue_boundary(
        container_is_same_as_record=False,
        record_type=3,
    )
    assert result["enqueue_path"]["sequence"][1] == "FUN_0080c8f0(local_8,record)"
