import struct

import pytest

from waypoint_base_runtime import (
    ACTIVE_MARKER_OFFSET,
    NEXT_LINK_OFFSET,
    POSITION_OFFSET,
    PREV_LINK_OFFSET,
    SIZE,
)
from waypoint_link_direction_runtime import (
    CALLERS,
    DEFAULT_DIRECTION,
    FUNCTION,
    FUNCTION_ADDRESS,
    LINK_RESOLUTION_FUNCTION,
    OUTPUT_DIRECTION_OFFSET,
    VECTOR_SUBTRACT_FUNCTION,
    apply_waypoint_link_direction_pass,
    derive_waypoint_link_direction,
    describe_waypoint_link_direction_runtime,
    update_waypoint_link_direction,
)


BASE = 0x00600000


def _ptr(index):
    return BASE + index * SIZE


def _record(
    position=(0.0, 0.0, 0.0),
    *,
    next_pointer=0,
    prev_pointer=0,
    active_marker=1,
    output=(99.0, 98.0, 97.0),
):
    blob = bytearray(SIZE)
    struct.pack_into("<fff", blob, POSITION_OFFSET, *position)
    struct.pack_into("<I", blob, NEXT_LINK_OFFSET, next_pointer)
    struct.pack_into("<I", blob, PREV_LINK_OFFSET, prev_pointer)
    struct.pack_into("<H", blob, ACTIVE_MARKER_OFFSET, active_marker)
    struct.pack_into("<fff", blob, OUTPUT_DIRECTION_OFFSET, *output)
    return bytes(blob)


def _direction(record):
    return struct.unpack_from("<fff", record, OUTPUT_DIRECTION_OFFSET)


def test_next_link_has_priority_over_previous_link():
    records = b"".join([
        _record((1, 2, 3), next_pointer=_ptr(1), prev_pointer=_ptr(2)),
        _record((4, 8, 10)),
        _record((-20, -20, -20)),
    ])
    row = derive_waypoint_link_direction(
        records,
        index=0,
        base_address=BASE,
    )
    assert row["mode"] == "next-minus-self"
    assert row["target_index"] == 1
    assert row["next_index"] == 1
    assert row["previous_index"] is None
    assert row["direction"] == pytest.approx((3.0, 6.0, 7.0))


def test_previous_link_is_used_as_self_minus_previous_when_next_is_null():
    records = b"".join([
        _record((1, 2, 3)),
        _record((5, 7, 11), prev_pointer=_ptr(0)),
    ])
    row = derive_waypoint_link_direction(
        records,
        index=1,
        base_address=BASE,
    )
    assert row["mode"] == "self-minus-previous"
    assert row["target_index"] == 0
    assert row["previous_index"] == 0
    assert row["direction"] == pytest.approx((4.0, 5.0, 8.0))


def test_missing_both_links_uses_fixed_negative_z_default():
    row = derive_waypoint_link_direction(
        _record((7, 8, 9)),
        index=0,
        base_address=BASE,
    )
    assert row["mode"] == "default"
    assert row["target_index"] is None
    assert row["target_pointer"] == 0
    assert row["direction"] == DEFAULT_DIRECTION == (0.0, 0.0, -1.0)


def test_single_record_update_writes_only_direction_output():
    records = b"".join([
        _record((1, 1, 1), next_pointer=_ptr(1)),
        _record((2, 4, 8)),
    ])
    before = records
    row = update_waypoint_link_direction(
        records,
        index=0,
        base_address=BASE,
    )
    out = row["records"]

    assert _direction(out[:SIZE]) == pytest.approx((1.0, 3.0, 7.0))
    assert out[POSITION_OFFSET:POSITION_OFFSET + 12] == before[
        POSITION_OFFSET:POSITION_OFFSET + 12
    ]
    assert struct.unpack_from("<I", out, NEXT_LINK_OFFSET)[0] == _ptr(1)
    assert out[SIZE:] == before[SIZE:]


def test_batch_pass_processes_every_logical_record_without_active_marker_gate():
    records = b"".join([
        _record(
            (0, 0, 0),
            next_pointer=_ptr(1),
            active_marker=0,
        ),
        _record((0, 0, 5)),
    ])
    row = apply_waypoint_link_direction_pass(
        records,
        base_address=BASE,
    )
    assert row["count"] == 2
    assert row["updates"][0]["mode"] == "next-minus-self"
    assert _direction(row["records"][:SIZE]) == pytest.approx((0, 0, 5))
    assert struct.unpack_from(
        "<H", row["records"], ACTIVE_MARKER_OFFSET
    )[0] == 0


def test_batch_pass_preserves_storage_after_logical_count():
    records = b"".join([
        _record((0, 0, 0)),
        _record((10, 20, 30), output=(1, 2, 3)),
    ])
    row = apply_waypoint_link_direction_pass(
        records,
        base_address=BASE,
        count=1,
    )
    assert row["count"] == 1
    assert _direction(row["records"][:SIZE]) == pytest.approx(DEFAULT_DIRECTION)
    assert row["records"][SIZE:] == records[SIZE:]


def test_non_null_misaligned_and_out_of_range_links_fail_closed():
    misaligned = _record((0, 0, 0), next_pointer=BASE + 1)
    with pytest.raises(ValueError, match="not aligned"):
        derive_waypoint_link_direction(
            misaligned,
            index=0,
            base_address=BASE,
        )

    outside = _record((0, 0, 0), next_pointer=_ptr(2))
    with pytest.raises(ValueError, match="outside"):
        derive_waypoint_link_direction(
            outside,
            index=0,
            base_address=BASE,
        )


def test_invalid_base_index_and_count_are_rejected():
    record = _record()
    with pytest.raises(ValueError, match="non-zero 32-bit"):
        derive_waypoint_link_direction(record, index=0, base_address=0)
    with pytest.raises(ValueError, match="outside the logical"):
        derive_waypoint_link_direction(record, index=1, base_address=BASE)
    with pytest.raises(ValueError, match="exceeds"):
        apply_waypoint_link_direction_pass(
            record,
            base_address=BASE,
            count=2,
        )


def test_descriptor_freezes_source_function_callers_and_offsets():
    report = describe_waypoint_link_direction_runtime()
    assert report["function"] == FUNCTION == "FUN_007ad8c0"
    assert report["function_address"] == FUNCTION_ADDRESS == 0x007AD8C0
    assert CALLERS == ("FUN_0071e3ba", "FUN_0071f099")
    assert tuple(report["callers"]) == CALLERS
    assert report["required_prior_pass"] == LINK_RESOLUTION_FUNCTION == "FUN_00717b90"
    assert report["inputs"] == {
        "position_offset": 0x10,
        "previous_link_offset": 0x17C,
        "next_link_offset": 0x180,
    }
    assert report["output_direction_offset"] == 0xF0
    assert report["selection_order"] == [
        "next.Position - self.Position",
        "self.Position - previous.Position",
        "default (0, 0, -1)",
    ]
    assert report["vector_subtract_helper"] == VECTOR_SUBTRACT_FUNCTION == "FUN_004a7870"
    assert report["active_marker_gate"] is False
