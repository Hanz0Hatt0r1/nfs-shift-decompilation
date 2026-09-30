import math
import struct

import pytest

from waypoint_base_runtime import (
    ACTIVE_MARKER_OFFSET,
    BRANCH_ID_OFFSET,
    CLASS_NAME,
    POSITION_OFFSET,
    REFLECTED_CONSTRUCTOR_DEFAULTS,
    REFLECTED_FIELDS,
    RTTI_DESCRIPTOR,
    RTTI_GETTER,
    SIZE,
    VTABLE,
    decode_query_fields,
    describe_waypoint_base_runtime,
    nearest_active_waypoint,
    nearest_branch_one_waypoint,
    nearest_branch_zero_waypoint,
    reflected_field_index,
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


def test_evidence_boundary_keeps_unreflected_marker_structural():
    report = describe_waypoint_base_runtime()
    assert report["query_fields"]["active_marker_offset"] == 0x18E
    assert "structural names only" in report["evidence_boundary"]
