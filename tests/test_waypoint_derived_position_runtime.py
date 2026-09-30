import struct

import pytest

from waypoint_base_runtime import ACTIVE_MARKER_OFFSET, POSITION_OFFSET, SIZE
from waypoint_derived_position_runtime import (
    BATCH_CALLER,
    DERIVED_LATERAL_OFFSET,
    DRY_LAT_OFFSET,
    FUNCTION,
    FUNCTION_ADDRESS,
    PERPENDICULAR_OFFSET,
    SECOND_GEOMETRY_PASS,
    VECTOR_ADD_FUNCTION,
    VECTOR_SCALE_FUNCTION,
    WET_LAT_OFFSET,
    apply_waypoint_derived_position_pass,
    derive_waypoint_query_position,
    describe_waypoint_derived_position_runtime,
    update_waypoint_derived_position,
)
from waypoint_path_query_runtime import QUERY_POSITION_OFFSET


def _record(
    *,
    position=(0.0, 0.0, 0.0),
    perpendicular=(1.0, 0.0, 0.0),
    dry_lat=0.0,
    wet_lat=0.0,
    active_marker=1,
):
    blob = bytearray(SIZE)
    struct.pack_into("<fff", blob, POSITION_OFFSET, *position)
    struct.pack_into("<fff", blob, PERPENDICULAR_OFFSET, *perpendicular)
    struct.pack_into("<f", blob, DRY_LAT_OFFSET, dry_lat)
    struct.pack_into("<f", blob, WET_LAT_OFFSET, wet_lat)
    struct.pack_into("<H", blob, ACTIVE_MARKER_OFFSET, active_marker)
    return bytes(blob)


def test_blend_formula_and_vector_scale_add_match_fun_007ade00():
    row = derive_waypoint_query_position(
        position=(10.0, 2.0, 3.0),
        perpendicular=(2.0, 0.0, -1.0),
        dry_lat=0.75,
        wet_lat=-0.25,
        blend_factor=0.75,
    )
    assert row["lateral_offset"] == pytest.approx(0.5)
    assert row["scaled_perpendicular"] == pytest.approx((1.0, 0.0, -0.5))
    assert row["derived_query_position"] == pytest.approx((11.0, 2.0, 2.5))


def test_factor_zero_uses_wet_lat_and_factor_one_uses_dry_lat():
    wet = derive_waypoint_query_position(
        position=(0, 0, 0),
        perpendicular=(1, 0, 0),
        dry_lat=4.0,
        wet_lat=-2.0,
        blend_factor=0.0,
    )
    dry = derive_waypoint_query_position(
        position=(0, 0, 0),
        perpendicular=(1, 0, 0),
        dry_lat=4.0,
        wet_lat=-2.0,
        blend_factor=1.0,
    )
    assert wet["lateral_offset"] == pytest.approx(-2.0)
    assert wet["derived_query_position"] == pytest.approx((-2.0, 0.0, 0.0))
    assert dry["lateral_offset"] == pytest.approx(4.0)
    assert dry["derived_query_position"] == pytest.approx((4.0, 0.0, 0.0))


def test_source_does_not_clamp_blend_factor():
    row = derive_waypoint_query_position(
        position=(0, 0, 0),
        perpendicular=(0, 0, 1),
        dry_lat=4.0,
        wet_lat=0.0,
        blend_factor=1.5,
    )
    assert row["lateral_offset"] == pytest.approx(6.0)
    assert row["derived_query_position"] == pytest.approx((0.0, 0.0, 6.0))


def test_single_record_update_writes_0x138_and_query_position_only():
    record = bytearray(_record(
        position=(1.0, 2.0, 3.0),
        perpendicular=(0.0, 2.0, 0.0),
        dry_lat=1.0,
        wet_lat=0.0,
    ))
    struct.pack_into("<I", record, 0x120, 0x12345678)
    before = bytes(record)

    row = update_waypoint_derived_position(record, 0.5)
    out = row["records"]

    assert struct.unpack_from("<f", out, DERIVED_LATERAL_OFFSET)[0] == pytest.approx(0.5)
    assert struct.unpack_from("<fff", out, QUERY_POSITION_OFFSET) == pytest.approx(
        (1.0, 3.0, 3.0)
    )
    assert struct.unpack_from("<I", out, 0x120)[0] == 0x12345678
    assert out[POSITION_OFFSET:POSITION_OFFSET + 12] == before[
        POSITION_OFFSET:POSITION_OFFSET + 12
    ]
    assert out[PERPENDICULAR_OFFSET:PERPENDICULAR_OFFSET + 12] == before[
        PERPENDICULAR_OFFSET:PERPENDICULAR_OFFSET + 12
    ]


def test_batch_pass_processes_inactive_records_and_preserves_storage_tail():
    records = b"".join([
        _record(
            position=(1, 0, 0),
            perpendicular=(1, 0, 0),
            dry_lat=2,
            wet_lat=0,
            active_marker=0,
        ),
        _record(
            position=(10, 0, 0),
            perpendicular=(1, 0, 0),
            dry_lat=4,
            wet_lat=0,
        ),
    ])
    row = apply_waypoint_derived_position_pass(records, 0.5, count=1)
    assert row["count"] == 1
    assert len(row["records"]) == 2 * SIZE
    assert row["updates"][0]["derived_query_position"] == pytest.approx(
        (2.0, 0.0, 0.0)
    )
    assert struct.unpack_from(
        "<H", row["records"], ACTIVE_MARKER_OFFSET
    )[0] == 0

    # The logical count bounds the source-equivalent loop; storage after it is
    # retained byte-for-byte.
    assert row["records"][SIZE:] == records[SIZE:]


def test_batch_default_count_updates_every_complete_record():
    records = b"".join([
        _record(position=(0, 0, 0), perpendicular=(1, 0, 0), dry_lat=2),
        _record(position=(10, 0, 0), perpendicular=(0, 1, 0), dry_lat=4),
    ])
    row = apply_waypoint_derived_position_pass(records, 1.0)
    assert row["count"] == 2
    assert row["updates"][0]["derived_query_position"] == pytest.approx((2, 0, 0))
    assert row["updates"][1]["derived_query_position"] == pytest.approx((10, 4, 0))


def test_short_record_and_invalid_count_fail_closed():
    with pytest.raises(ValueError, match="requires"):
        update_waypoint_derived_position(bytes(SIZE - 1), 0.5)
    with pytest.raises(ValueError, match="exceeds"):
        apply_waypoint_derived_position_pass(_record(), 0.5, count=2)
    with pytest.raises(ValueError, match="exceeds"):
        apply_waypoint_derived_position_pass(_record(), 0.5, count=-1)


def test_descriptor_freezes_source_functions_offsets_and_pass_order():
    report = describe_waypoint_derived_position_runtime()
    assert report["function"] == FUNCTION == "FUN_007ade00"
    assert report["function_address"] == FUNCTION_ADDRESS == 0x007ADE00
    assert report["batch_caller"] == BATCH_CALLER == "FUN_00719ea0"
    assert report["inputs"] == {
        "position_offset": 0x10,
        "perpendicular_offset": 0x1C,
        "dry_lat_offset": 0x48,
        "wet_lat_offset": 0x4C,
        "blend_factor": "function argument",
    }
    assert report["outputs"] == {
        "derived_lateral_offset": 0x138,
        "derived_query_position_offset": 0x8C,
    }
    assert report["formula"]["lateral"] == "(1-factor)*WetLat + factor*DryLat"
    assert VECTOR_SCALE_FUNCTION == "FUN_004368e0"
    assert VECTOR_ADD_FUNCTION == "FUN_00432c00"
    assert report["vector_helpers"] == {
        "scale": VECTOR_SCALE_FUNCTION,
        "add": VECTOR_ADD_FUNCTION,
    }
    assert report["caller_order"] == {
        "first_pass": "FUN_007ade00",
        "second_pass": SECOND_GEOMETRY_PASS == "FUN_007ada70",
    }
