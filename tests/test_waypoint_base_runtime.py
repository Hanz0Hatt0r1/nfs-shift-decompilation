import math
import struct

import pytest

from waypoint_base_runtime import (
    ACTIVE_MARKER_OFFSET,
    BRANCH_ID_OFFSET,
    BRANCH_INDEX_OFFSET,
    BRANCH_LINK_OFFSET,
    CLASS_NAME,
    LINK_RESOLUTION_FUNCTION,
    NEXT_INDEX_OFFSET,
    NEXT_LINK_OFFSET,
    POSITION_OFFSET,
    PREV_INDEX_OFFSET,
    PREV_LINK_OFFSET,
    REFLECTED_CONSTRUCTOR_DEFAULTS,
    REFLECTED_FIELDS,
    RTTI_DESCRIPTOR,
    RTTI_GETTER,
    SIZE,
    VTABLE,
    decode_link_fields,
    decode_query_fields,
    describe_waypoint_base_runtime,
    nearest_active_waypoint,
    nearest_branch_one_waypoint,
    nearest_branch_zero_waypoint,
    reflected_field_index,
    resolve_waypoint_links,
)


def _record(
    position=(0.0, 0.0, 0.0),
    *,
    branch_id=0,
    active_marker=1,
):
    blob = bytearray(SIZE)
    struct.pack_into("<fff", blob, POSITION_OFFSET, *position)
    struct.pack_into("<i", blob, BRANCH_ID_OFFSET, branch_id)
    struct.pack_into("<H", blob, ACTIVE_MARKER_OFFSET, active_marker)
    return bytes(blob)


def _link_record(
    *,
    active_marker=1,
    prev_index=-1,
    next_index=-1,
    branch_index=-1,
    prev_link=0,
    next_link=0,
    branch_link=0,
):
    blob = bytearray(_record(active_marker=active_marker))
    struct.pack_into("<i", blob, PREV_INDEX_OFFSET, prev_index)
    struct.pack_into("<i", blob, NEXT_INDEX_OFFSET, next_index)
    struct.pack_into("<i", blob, BRANCH_INDEX_OFFSET, branch_index)
    struct.pack_into("<I", blob, PREV_LINK_OFFSET, prev_link)
    struct.pack_into("<I", blob, NEXT_LINK_OFFSET, next_link)
    struct.pack_into("<I", blob, BRANCH_LINK_OFFSET, branch_link)
    return bytes(blob)


def test_waypoint_base_identity_and_exact_array_element_size():
    report = describe_waypoint_base_runtime()
    assert CLASS_NAME == "WayPointBase"
    assert RTTI_DESCRIPTOR == 0x00C1C21C
    assert RTTI_GETTER == 0x00715C70
    assert VTABLE == 0x00B0CAD8
    assert SIZE == 0x1BC
    assert report["identity"]["constructor"] == "FUN_007ae5d0"
    assert report["identity"]["destructor"] == "FUN_007ad680"
    assert report["size"] == 0x1BC


def test_all_twenty_direct_reflection_fields_are_preserved():
    assert len(REFLECTED_FIELDS) == 20
    fields = reflected_field_index()
    assert len(fields) == 20
    assert fields["Position"]["offset"] == 0x10
    assert fields["Road Left/Right"]["offset"] == 0x28
    assert fields["Groove Alpha"]["offset"] == 0x50
    assert fields["Lap Distance"]["offset"] == 0x58
    assert fields["Branch ID"]["offset"] == 0x6C
    assert fields["Prev Index"]["offset"] == 0x74
    assert fields["Next Index"]["offset"] == 0x78
    assert fields["Branch Index"]["offset"] == 0x7C
    assert "previous waypoint" in fields["Prev Index"]["description"]


def test_constructor_defaults_only_claim_explicit_fun_007ae5d0_writes():
    defaults = REFLECTED_CONSTRUCTOR_DEFAULTS
    assert defaults["Position"] == (0.0, 0.0, 0.0)
    assert defaults["Perpendicular"] == (0.0, 0.0, 0.0)
    assert defaults["Corner Speed Mult"] == 1.0
    assert defaults["Branch ID"] == -1
    assert defaults["BitFields"] == 0
    assert defaults["Prev Index"] == -1
    assert defaults["Next Index"] == -1
    assert defaults["Branch Index"] == -1
    assert "Groove Alpha" not in defaults
    assert "Sector" not in defaults
    assert "Event Type" not in defaults
    assert "Event Speed Fraction" not in defaults


def test_query_field_decoder_uses_source_offsets():
    row = decode_query_fields(
        _record((1.25, -2.5, 9.0), branch_id=-1, active_marker=7)
    )
    assert row["position"] == pytest.approx((1.25, -2.5, 9.0))
    assert row["branch_id"] == -1
    assert row["active_marker"] == 7


def test_query_decoder_rejects_short_record():
    with pytest.raises(ValueError, match="0x1bc"):
        decode_query_fields(bytes(SIZE - 1))


def test_branch_zero_query_matches_fun_00718060_rules():
    records = b"".join([
        _record((5.0, 0.0, 0.0), branch_id=0, active_marker=1),
        _record((1.0, 0.0, 0.0), branch_id=1, active_marker=1),
        _record((0.25, 0.0, 0.0), branch_id=0, active_marker=0),
        _record((2.0, 0.0, 0.0), branch_id=0, active_marker=2),
    ])
    row = nearest_branch_zero_waypoint(
        records,
        (0.0, 0.0, 0.0),
        base_address=0x00600000,
    )
    assert row is not None
    assert row["index"] == 3
    assert row["record_offset"] == 3 * SIZE
    assert row["address"] == 0x00600000 + 3 * SIZE
    assert row["branch_id"] == 0
    assert row["active_marker"] == 2
    assert math.isclose(row["distance_sq"], 4.0)


def test_branch_one_query_matches_fun_00718120_rules():
    records = b"".join([
        _record((4.0, 0.0, 0.0), branch_id=1, active_marker=1),
        _record((0.0, 3.0, 0.0), branch_id=1, active_marker=1),
        _record((0.0, 0.0, 2.0), branch_id=0, active_marker=1),
    ])
    row = nearest_branch_one_waypoint(records, (0.0, 0.0, 0.0))
    assert row is not None
    assert row["index"] == 1
    assert row["distance_sq"] == pytest.approx(9.0)


def test_generic_query_can_select_recovered_branch_id_field():
    records = b"".join([
        _record((10.0, 0.0, 0.0), branch_id=7, active_marker=1),
        _record((1.0, 2.0, 2.0), branch_id=7, active_marker=1),
        _record((0.1, 0.0, 0.0), branch_id=8, active_marker=1),
    ])
    row = nearest_active_waypoint(
        records,
        (0.0, 0.0, 0.0),
        branch_id=7,
    )
    assert row is not None
    assert row["index"] == 1
    assert row["distance_sq"] == pytest.approx(9.0)


def test_equal_distance_keeps_first_record_like_source_strict_less_than():
    records = b"".join([
        _record((1.0, 0.0, 0.0), branch_id=0, active_marker=1),
        _record((-1.0, 0.0, 0.0), branch_id=0, active_marker=1),
    ])
    row = nearest_branch_zero_waypoint(records, (0.0, 0.0, 0.0))
    assert row is not None
    assert row["index"] == 0


def test_query_count_is_bounded_by_provided_storage():
    records = _record()
    with pytest.raises(ValueError, match="exceeds"):
        nearest_branch_zero_waypoint(records, (0.0, 0.0, 0.0), count=2)
    with pytest.raises(ValueError, match="exceeds"):
        nearest_branch_zero_waypoint(records, (0.0, 0.0, 0.0), count=-1)


def test_no_matching_active_record_returns_none():
    records = b"".join([
        _record(branch_id=0, active_marker=0),
        _record(branch_id=1, active_marker=1),
    ])
    assert nearest_branch_zero_waypoint(records, (0.0, 0.0, 0.0)) is None


def test_link_decoder_uses_recovered_index_and_pointer_offsets():
    row = decode_link_fields(
        _link_record(
            active_marker=3,
            prev_index=4,
            next_index=5,
            branch_index=6,
            prev_link=0x1000,
            next_link=0x2000,
            branch_link=0x3000,
        )
    )
    assert row == {
        "active_marker": 3,
        "prev_index": 4,
        "next_index": 5,
        "branch_index": 6,
        "prev_link": 0x1000,
        "next_link": 0x2000,
        "branch_link": 0x3000,
    }


def test_link_resolution_matches_fun_00717b90_valid_and_invalid_targets():
    base = 0x00600000
    records = b"".join([
        _link_record(prev_index=-1, next_index=1, branch_index=2),
        _link_record(prev_index=0, next_index=2, branch_index=-1),
        _link_record(
            active_marker=0,
            prev_index=123,
            next_index=124,
            branch_index=125,
            prev_link=0x11111111,
            next_link=0x22222222,
            branch_link=0x33333333,
        ),
        _link_record(prev_index=2, next_index=4, branch_index=-1),
    ])
    resolved = resolve_waypoint_links(records, base_address=base)
    out = resolved["records"]

    row0 = decode_link_fields(out[0 * SIZE:1 * SIZE])
    assert row0["prev_index"] == -1
    assert row0["prev_link"] == 0
    assert row0["next_index"] == 1
    assert row0["next_link"] == base + SIZE
    assert row0["branch_index"] == -1
    assert row0["branch_link"] == 0

    row1 = decode_link_fields(out[1 * SIZE:2 * SIZE])
    assert row1["prev_index"] == 0
    assert row1["prev_link"] == base
    assert row1["next_index"] == -1
    assert row1["next_link"] == 0

    # FUN_00717b90 skips inactive source records entirely.
    row2 = decode_link_fields(out[2 * SIZE:3 * SIZE])
    assert row2["prev_index"] == 123
    assert row2["next_index"] == 124
    assert row2["branch_index"] == 125
    assert row2["prev_link"] == 0x11111111
    assert row2["next_link"] == 0x22222222
    assert row2["branch_link"] == 0x33333333

    row3 = decode_link_fields(out[3 * SIZE:4 * SIZE])
    assert row3["prev_index"] == -1
    assert row3["prev_link"] == 0
    assert row3["next_index"] == -1
    assert row3["next_link"] == 0

    assert resolved["decisions"][0]["links"]["next"]["reason"] == "resolved"
    assert resolved["decisions"][0]["links"]["branch"]["reason"] == "inactive-target"
    assert resolved["decisions"][3]["links"]["next"]["reason"] == "out-of-range"
    assert resolved["decisions"][2]["processed"] is False


def test_link_resolution_uses_requested_database_count_not_storage_tail():
    base = 0x00600000
    records = b"".join([
        _link_record(next_index=1),
        _link_record(),
    ])
    resolved = resolve_waypoint_links(records, base_address=base, count=1)
    row = decode_link_fields(resolved["records"])
    assert row["next_index"] == -1
    assert row["next_link"] == 0
    assert resolved["decisions"][0]["links"]["next"]["reason"] == "out-of-range"


def test_link_resolution_rejects_malformed_negative_index_below_source_sentinel():
    with pytest.raises(ValueError, match="below the retail -1 sentinel"):
        resolve_waypoint_links(
            _link_record(next_index=-2),
            base_address=0x00600000,
        )


def test_link_resolution_requires_real_32_bit_array_base():
    record = _link_record()
    with pytest.raises(ValueError, match="non-zero 32-bit"):
        resolve_waypoint_links(record, base_address=0)
    with pytest.raises(ValueError, match="non-zero 32-bit"):
        resolve_waypoint_links(record, base_address=0x1_0000_0000)


def test_runtime_description_records_link_resolution_contract():
    report = describe_waypoint_base_runtime()
    links = report["link_resolution"]
    assert links["function"] == LINK_RESOLUTION_FUNCTION == "FUN_00717b90"
    assert links["index_offsets"] == {
        "prev": 0x74,
        "next": 0x78,
        "branch": 0x7C,
    }
    assert links["pointer_offsets"] == {
        "prev": 0x17C,
        "next": 0x180,
        "branch": 0x184,
    }
    assert links["invalid_index_sentinel"] == -1


def test_evidence_boundary_keeps_unreflected_marker_structural():
    report = describe_waypoint_base_runtime()
    assert report["query_fields"]["active_marker_offset"] == 0x18E
    assert "structural names only" in report["evidence_boundary"]
