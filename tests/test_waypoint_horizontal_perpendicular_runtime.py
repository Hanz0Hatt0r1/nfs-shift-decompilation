import struct

import pytest

from waypoint_base_runtime import SIZE
from waypoint_horizontal_perpendicular_runtime import (
    CROSS_PRODUCT_FUNCTION,
    DEGENERATE_FALLBACK,
    FUNCTION,
    FUNCTION_ADDRESS,
    KNOWN_CALLERS,
    NORMALIZE_THRESHOLD,
    NORMALIZE_THRESHOLD_BITS,
    SOURCE_VECTOR_OFFSET,
    WORLD_UP,
    cross_product,
    derive_waypoint_horizontal_perpendicular,
    describe_waypoint_horizontal_perpendicular_runtime,
    horizontal_perpendicular,
)


def _record(direction):
    blob = bytearray(SIZE)
    struct.pack_into("<fff", blob, SOURCE_VECTOR_OFFSET, *direction)
    return bytes(blob)


def test_cross_product_helper_matches_recovered_three_float_formula():
    assert cross_product((0, 1, 0), (3, 4, 5)) == pytest.approx((5, 0, -3))
    assert cross_product((1, 0, 0), (0, 1, 0)) == pytest.approx((0, 0, 1))


def test_world_up_cross_is_normalized_for_non_degenerate_horizontal_direction():
    row = horizontal_perpendicular((3.0, 17.0, 4.0))
    assert row["cross"] == pytest.approx((4.0, 0.0, -3.0))
    assert row["length"] == pytest.approx(5.0)
    assert row["mode"] == "normalized-cross"
    assert row["result"] == pytest.approx((0.8, 0.0, -0.6))


def test_vertical_source_vector_uses_retail_fallback():
    row = horizontal_perpendicular((0.0, 25.0, 0.0))
    assert row["cross"] == pytest.approx((0.0, 0.0, 0.0))
    assert row["length"] == pytest.approx(0.0)
    assert row["mode"] == "fallback"
    assert row["result"] == DEGENERATE_FALLBACK == (1.0, 0.0, 0.0)


def test_length_below_threshold_uses_fallback_and_above_threshold_normalizes():
    below = horizontal_perpendicular((0.005, 0.0, 0.0))
    above = horizontal_perpendicular((0.02, 0.0, 0.0))

    assert below["length"] < NORMALIZE_THRESHOLD
    assert below["mode"] == "fallback"
    assert below["result"] == DEGENERATE_FALLBACK

    assert above["length"] > NORMALIZE_THRESHOLD
    assert above["mode"] == "normalized-cross"
    assert above["result"] == pytest.approx((0.0, 0.0, -1.0))


def test_y_component_does_not_change_world_up_cross_result():
    flat = horizontal_perpendicular((2.0, 0.0, -6.0))
    raised = horizontal_perpendicular((2.0, 1000.0, -6.0))
    assert raised["cross"] == flat["cross"]
    assert raised["result"] == flat["result"]


def test_record_decoder_reads_exact_0x13c_source_vector():
    row = derive_waypoint_horizontal_perpendicular(_record((0.0, 0.0, 2.0)))
    assert row["source_direction"] == pytest.approx((0.0, 0.0, 2.0))
    assert row["result"] == pytest.approx((1.0, 0.0, 0.0))


def test_short_record_is_rejected():
    with pytest.raises(ValueError, match="requires"):
        derive_waypoint_horizontal_perpendicular(bytes(SIZE - 1))


def test_descriptor_freezes_x86_threshold_helper_and_callers():
    report = describe_waypoint_horizontal_perpendicular_runtime()
    assert report["function"] == FUNCTION == "FUN_007ade70"
    assert report["function_address"] == FUNCTION_ADDRESS == 0x007ADE70
    assert report["source_vector_offset"] == SOURCE_VECTOR_OFFSET == 0x13C
    assert tuple(report["known_callers"]) == KNOWN_CALLERS == (
        "FUN_00759210",
        "FUN_007adf30",
    )
    assert report["world_up"] == WORLD_UP == (0.0, 1.0, 0.0)
    assert report["cross_product_helper"] == CROSS_PRODUCT_FUNCTION == "FUN_0047bdb0"
    assert report["normalization"]["condition"] == "length > 0.01"
    assert report["normalization"]["threshold_bits"] == NORMALIZE_THRESHOLD_BITS == 0x3C23D70A
    assert report["normalization"]["threshold"] == pytest.approx(NORMALIZE_THRESHOLD)
    assert report["normalization"]["fallback"] == DEGENERATE_FALLBACK
    assert report["simplified_cross"] == "(source.z, 0, -source.x)"
