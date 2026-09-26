from tracking_camera_constructor_runtime import (
    SPLINE_ALLOCATION_BYTES,
    SPLINE_NODE_COUNT,
    SPLINE_RECORD_STRIDE,
    describe_tracking_camera_constructor_complete,
    describe_tracking_constructor_copy,
    initialize_spline_pool,
    tracking_camera_constructor_layout,
)


def test_constructor_layout_preserves_refcount_vtable_sequence():
    result = tracking_camera_constructor_layout()
    assert result["refcount"]["final_vtable"] == "PTR_FUN_00b16158"
    assert result["refcount"]["final_aux_vtable"] == "PTR_LAB_00b16138"
    assert result["refcount"]["+0x08"] == 1


def test_constructor_has_seven_nested_7f6690_blocks():
    result = tracking_camera_constructor_layout()
    assert len(result["nested_initializers"]) == 7


def test_constructor_preserves_mode_and_sentinel_defaults():
    result = tracking_camera_constructor_layout()
    assert result["raw_initializers"]["+0x244"] == 0x7FFFFFFF
    assert result["raw_initializers"]["+0x2c0"] == 0xFFFFFFFF
    assert result["raw_initializers"]["+0x2c4"] == 0xFFFFFFFF
    assert result["raw_initializers"]["+0x2d0"] == 0x3F800000
    assert result["sentinels"]["+0x37c"] == 0xFFFFFFFF


def test_constructor_copies_exact_16_global_camera_dwords():
    source = {0x270 + i * 4: i for i in range(16)}
    result = describe_tracking_constructor_copy(source)
    assert len(result["values"]) == 16
    assert result["destination_range"] == ["+0x270", "+0x2ac"]


def test_each_spline_pool_is_4_plus_128_times_24_bytes():
    assert SPLINE_ALLOCATION_BYTES == 4 + 0x80 * 0x24
    result = initialize_spline_pool(
        allocation_succeeded=True,
        record_constructor_succeeded=True,
    )
    assert result["record_count"] == 0x80
    assert result["record_stride"] == 0x24
    assert result["bytes"] == SPLINE_ALLOCATION_BYTES


def test_failed_second_pool_is_reported_as_partial_constructor():
    result = describe_tracking_camera_constructor_complete(
        second_pool_allocated=False,
    )
    assert result["status"] == "partial"


def test_complete_constructor_keeps_shake_initialization_order():
    result = describe_tracking_camera_constructor_complete()
    names = [a["action"] for a in result["actions"]]
    assert names.index("FUN_00812c00") < names.index("FUN_00823a80")
    assert result["actions"][1]["rate_bits"] == 0x40C00000
    assert result["actions"][3]["rate_bits"] == 0x41800000
