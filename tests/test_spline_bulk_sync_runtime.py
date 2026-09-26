from spline_bulk_sync_runtime import (
    BulkSyncState,
    ReferencedSpline,
    SplineRecordPayload,
    append_referenced_spline,
    copy_spline_records,
    describe_bulk_sync,
    normalize_spline_scalar_window,
    rebase_referenced_spline,
)


def _record(base: int) -> SplineRecordPayload:
    return SplineRecordPayload({
        0x10: base,
        0x14: base + 1,
        0x18: base + 2,
        0x1C: base + 3,
        0x20: base + 4,
    })


def test_record_copy_uses_exact_0x24_stride():
    copied, cursor = copy_spline_records(
        [_record(1), _record(10)],
        destination_base=0x1000,
        cursor=2,
    )
    assert copied[0]["destination_address"] == 0x1000 + 2 * 0x24
    assert copied[1]["destination_address"] == 0x1000 + 3 * 0x24
    assert cursor == 4


def test_record_copy_preserves_only_the_five_observed_fields():
    copied, _ = copy_spline_records(
        [SplineRecordPayload({0x10:1,0x14:2,0x18:3,0x1c:4,0x20:5,0x24:99})],
        destination_base=0,
        cursor=0,
    )
    assert copied[0]["fields"] == {0x10:1,0x14:2,0x18:3,0x1c:4,0x20:5}


def test_append_referenced_spline_updates_first_cursor_only():
    state = BulkSyncState(first_base=0x2000, second_base=0x3000)
    state, result = append_referenced_spline(
        state,
        referenced=ReferencedSpline(
            spline_id=2,
            records=[_record(1), _record(2)],
            length=12,
            allocation_pointer="old",
        ),
        destination="first",
    )
    assert state.first_cursor == 2
    assert state.second_cursor == 0
    assert result["record_count"] == 2


def test_rebase_preserves_old_pointer_count_length_and_writes_new_buffer_fields():
    result = rebase_referenced_spline(
        destination_base=0x4000,
        destination_cursor=3,
        referenced=ReferencedSpline(
            spline_id=5,
            records=[_record(1), _record(2)],
            length=20,
            allocation_pointer="ptr",
        ),
    )
    assert result["writes_to_collection_entry"]["saved_pointer"] == "ptr"
    assert result["writes_to_collection_entry"]["saved_count"] == 2
    assert result["writes_to_collection_entry"]["saved_length"] == 20
    assert result["writes_to_spline"]["+0x14"] == 0x4000 + 3 * 0x24
    assert result["writes_to_spline"]["+0x10"] == 1
    assert result["actions"][0]["action"] == "FUN_008226a0"


def test_bulk_sync_skips_inactive_entries():
    result = describe_bulk_sync(
        first_splines=[ReferencedSpline(1, [_record(1)], 1, "a")],
        second_splines=[ReferencedSpline(2, [_record(2)], 1, "b")],
        first_base=0x1000,
        second_base=0x2000,
        active_entry_flags=[False],
    )
    assert result["status"] == "updated"
    assert result["first_cursor"] == 0
    assert result["second_cursor"] == 0


def test_bulk_sync_updates_both_cursors_for_active_entries():
    result = describe_bulk_sync(
        first_splines=[ReferencedSpline(1, [_record(1), _record(2)], 1, "a")],
        second_splines=[ReferencedSpline(2, [_record(3)], 1, "b")],
        first_base=0x1000,
        second_base=0x2000,
        active_entry_flags=[True],
        scalar_window_result={"min": 1, "max": 3},
    )
    assert result["first_cursor"] == 2
    assert result["second_cursor"] == 1
    assert result["scalar_window_result"]["min"] == 1


def test_scalar_window_finds_global_max_and_left_right_descents():
    result = normalize_spline_scalar_window([10, 9, 8, 7, 7, 6, 5])
    assert result["global_max"] == 10.0
    assert result["left"] == 1
    assert result["right"] == 5
    assert result["written_indices"] == [1,2,3,4,5]
    assert result["values_after"] == [10.0,10.0,10.0,10.0,10.0,10.0,5.0]


def test_scalar_window_does_not_write_when_span_is_three_or_less():
    result = normalize_spline_scalar_window([3, 2, 1])
    assert result["written_indices"] == []
    assert result["values_after"] == [3.0,2.0,1.0]


def test_scalar_window_keeps_values_when_no_descending_edges_exist():
    result = normalize_spline_scalar_window([1,2,3,4,5])
    assert result["left"] == -1
    assert result["right"] == -1
    assert result["status"] == "unchanged"
