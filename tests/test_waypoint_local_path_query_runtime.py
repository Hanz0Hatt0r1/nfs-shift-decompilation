import struct

import pytest

from waypoint_base_runtime import (
    ACTIVE_MARKER_OFFSET,
    BRANCH_ID_OFFSET,
    BRANCH_LINK_OFFSET,
    NEXT_LINK_OFFSET,
    PREV_LINK_OFFSET,
    SIZE,
)
from waypoint_local_path_query_runtime import (
    BRANCH_REDIRECT_BLOCK,
    FINAL_ORIENTATION_BLOCK,
    FUNCTION,
    FUNCTION_ADDRESS,
    GLOBAL_FALLBACK_BLOCK,
    GLOBAL_FALLBACK_FUNCTION,
    NEXT_SCAN_BLOCK,
    NULL_CURRENT_FALLBACK_CALL,
    PREVIOUS_SCAN_BLOCK,
    describe_waypoint_local_path_query_runtime,
    local_query_distance_sq,
    select_local_path_waypoint,
)
from waypoint_path_query_runtime import (
    ORIENTATION_X_OFFSET,
    ORIENTATION_Z_OFFSET,
    QUERY_POSITION_OFFSET,
)


BASE = 0x00600000


def _ptr(index):
    return BASE + index * SIZE


def _record(
    position=(0.0, 0.0, 0.0),
    *,
    branch_id=0,
    active_marker=1,
    prev_pointer=0,
    next_pointer=0,
    branch_pointer=0,
    orientation=(1.0, 0.0),
):
    blob = bytearray(SIZE)
    struct.pack_into("<fff", blob, QUERY_POSITION_OFFSET, *position)
    struct.pack_into("<i", blob, BRANCH_ID_OFFSET, branch_id)
    struct.pack_into("<H", blob, ACTIVE_MARKER_OFFSET, active_marker)
    struct.pack_into("<I", blob, PREV_LINK_OFFSET, prev_pointer)
    struct.pack_into("<I", blob, NEXT_LINK_OFFSET, next_pointer)
    struct.pack_into("<I", blob, BRANCH_LINK_OFFSET, branch_pointer)
    struct.pack_into("<f", blob, ORIENTATION_X_OFFSET, orientation[0])
    struct.pack_into("<f", blob, ORIENTATION_Z_OFFSET, orientation[1])
    return bytes(blob)


def test_local_metric_is_ordinary_euclidean_squared_not_fun_007189a0_metric():
    assert local_query_distance_sq((0, 0, 0), (3, 0, 0)) == pytest.approx(9.0)
    assert local_query_distance_sq((0, 0, 0), (0, 2, 0)) == pytest.approx(4.0)


def test_null_current_immediately_uses_global_fun_007189a0_fallback():
    records = _record((1, 0, 0), branch_id=3)
    row = select_local_path_waypoint(
        records,
        (0, 0, 0),
        current_pointer=0,
        branch_id=3,
        base_address=BASE,
    )
    assert row is not None
    assert row["strategy"] == "global-fallback"
    assert row["fallback_reason"] == "null-current"
    assert row["fallback_function"] == GLOBAL_FALLBACK_FUNCTION
    assert row["returned_pointer"] == BASE
    assert row["returned_index"] == 0


def test_branch_link_redirects_anchor_only_when_target_branch_matches():
    records = b"".join([
        _record((20, 0, 0), branch_id=0, branch_pointer=_ptr(2)),
        _record((30, 0, 0), branch_id=1),
        _record((1, 0, 0), branch_id=1),
    ])
    row = select_local_path_waypoint(
        records,
        (0, 0, 0),
        current_pointer=_ptr(0),
        branch_id=1,
        base_address=BASE,
    )
    assert row is not None
    assert row["strategy"] == "local"
    assert row["start_index"] == 0
    assert row["search_anchor_index"] == 2
    assert row["branch_redirected"] is True
    assert row["selected_index"] == 2
    assert row["returned_pointer"] == _ptr(2)


def test_backward_walk_keeps_closest_matching_branch_record():
    records = b"".join([
        _record((3, 0, 0), branch_id=0),
        _record((1, 0, 0), branch_id=0, prev_pointer=_ptr(0)),
        _record((5, 0, 0), branch_id=0, prev_pointer=_ptr(1)),
    ])
    row = select_local_path_waypoint(
        records,
        (0, 0, 0),
        current_pointer=_ptr(2),
        branch_id=0,
        base_address=BASE,
    )
    assert row is not None
    assert row["strategy"] == "local"
    assert row["backward_visited"] == [1]
    assert row["selected_index"] == 1
    assert row["selected_distance_sq"] == pytest.approx(1.0)


def test_backward_walk_rejects_closer_record_with_wrong_branch():
    records = b"".join([
        _record((8, 0, 0), branch_id=0),
        _record((1, 0, 0), branch_id=7, prev_pointer=_ptr(0)),
        _record((5, 0, 0), branch_id=0, prev_pointer=_ptr(1)),
    ])
    row = select_local_path_waypoint(
        records,
        (0, 0, 0),
        current_pointer=_ptr(2),
        branch_id=0,
        base_address=BASE,
    )
    assert row is not None
    assert row["strategy"] == "local"
    assert row["backward_visited"] == [1]
    assert row["selected_index"] == 2


def test_decreasing_backward_chain_ending_at_null_falls_back_globally():
    records = b"".join([
        _record((1, 0, 0), branch_id=0),
        _record((5, 0, 0), branch_id=0, prev_pointer=_ptr(0)),
    ])
    row = select_local_path_waypoint(
        records,
        (0, 0, 0),
        current_pointer=_ptr(1),
        branch_id=0,
        base_address=BASE,
    )
    assert row is not None
    assert row["strategy"] == "global-fallback"
    assert row["fallback_reason"] == "previous-chain-ended"
    assert row["backward_visited"] == [0]
    assert row["global_query"]["selected_index"] == 0


def test_forward_walk_uses_anchor_next_and_has_no_branch_filter():
    records = b"".join([
        _record((5, 0, 0), branch_id=0, next_pointer=_ptr(1)),
        _record((1, 0, 0), branch_id=7, next_pointer=_ptr(2)),
        _record((3, 0, 0), branch_id=9),
    ])
    row = select_local_path_waypoint(
        records,
        (0, 0, 0),
        current_pointer=_ptr(0),
        branch_id=0,
        base_address=BASE,
    )
    assert row is not None
    assert row["strategy"] == "local"
    assert row["forward_visited"] == [1]
    assert row["selected_index"] == 1
    assert row["selected_distance_sq"] == pytest.approx(1.0)


def test_decreasing_forward_chain_ending_at_null_falls_back_globally():
    records = b"".join([
        _record((5, 0, 0), branch_id=0, next_pointer=_ptr(1)),
        _record((1, 0, 0), branch_id=0),
    ])
    row = select_local_path_waypoint(
        records,
        (0, 0, 0),
        current_pointer=_ptr(0),
        branch_id=0,
        base_address=BASE,
    )
    assert row is not None
    assert row["strategy"] == "global-fallback"
    assert row["fallback_reason"] == "next-chain-ended"
    assert row["forward_visited"] == [1]
    assert row["global_query"]["selected_index"] == 1


def test_optional_orientation_step_advances_only_to_non_null_next():
    records = b"".join([
        _record(
            (2, 0, 0),
            branch_id=0,
            next_pointer=_ptr(1),
            orientation=(-1, 0),
        ),
        _record((10, 0, 0), branch_id=0),
    ])
    row = select_local_path_waypoint(
        records,
        (0, 0, 0),
        current_pointer=_ptr(0),
        branch_id=0,
        advance_forward=True,
        base_address=BASE,
    )
    assert row is not None
    assert row["strategy"] == "local"
    assert row["selected_index"] == 0
    assert row["orientation_dot"] == pytest.approx(-2.0)
    assert row["advanced_after_orientation"] is True
    assert row["returned_pointer"] == _ptr(1)
    assert row["returned_index"] == 1

    no_next = select_local_path_waypoint(
        _record((2, 0, 0), branch_id=0, orientation=(-1, 0)),
        (0, 0, 0),
        current_pointer=BASE,
        branch_id=0,
        advance_forward=True,
        base_address=BASE,
    )
    assert no_next is not None
    assert no_next["orientation_dot"] == pytest.approx(-2.0)
    assert no_next["advanced_after_orientation"] is False
    assert no_next["returned_pointer"] == BASE


def test_local_search_does_not_add_an_active_marker_gate():
    records = _record((1, 0, 0), branch_id=0, active_marker=0)
    row = select_local_path_waypoint(
        records,
        (0, 0, 0),
        current_pointer=BASE,
        branch_id=0,
        base_address=BASE,
    )
    assert row is not None
    assert row["strategy"] == "local"
    assert row["selected_index"] == 0


def test_traversed_non_array_pointer_is_rejected_fail_closed():
    records = _record((1, 0, 0), branch_id=0, prev_pointer=BASE + 1)
    with pytest.raises(ValueError, match="not aligned"):
        select_local_path_waypoint(
            records,
            (0, 0, 0),
            current_pointer=BASE,
            branch_id=0,
            base_address=BASE,
        )


def test_branch_selector_uses_integer_abi_and_count_is_bounded():
    records = _record()
    with pytest.raises(TypeError):
        select_local_path_waypoint(
            records,
            (0, 0, 0),
            current_pointer=BASE,
            branch_id=0.0,
            base_address=BASE,
        )
    with pytest.raises(ValueError, match="signed int32"):
        select_local_path_waypoint(
            records,
            (0, 0, 0),
            current_pointer=BASE,
            branch_id=0x80000000,
            base_address=BASE,
        )
    with pytest.raises(ValueError, match="exceeds"):
        select_local_path_waypoint(
            records,
            (0, 0, 0),
            current_pointer=BASE,
            branch_id=0,
            count=2,
            base_address=BASE,
        )


def test_descriptor_freezes_retail_blocks_and_rules():
    report = describe_waypoint_local_path_query_runtime()
    assert report["function"] == FUNCTION == "FUN_00718d00"
    assert report["function_address"] == FUNCTION_ADDRESS == 0x00718D00
    assert report["global_fallback_function"] == "FUN_007189a0"
    assert report["metric"]["expression"] == "dx^2 + dy^2 + dz^2"
    assert report["blocks"] == {
        "null_current_fallback_call": NULL_CURRENT_FALLBACK_CALL,
        "branch_redirect": BRANCH_REDIRECT_BLOCK,
        "previous_scan": PREVIOUS_SCAN_BLOCK,
        "next_scan": NEXT_SCAN_BLOCK,
        "final_orientation": FINAL_ORIENTATION_BLOCK,
        "global_fallback": GLOBAL_FALLBACK_BLOCK,
    }
    assert report["fields"]["previous_link_offset"] == 0x17C
    assert report["fields"]["next_link_offset"] == 0x180
    assert report["fields"]["branch_link_offset"] == 0x184
    assert "does not apply a Branch-ID check" in report["source_rules"]["next_scan"]
    assert "falls back" in report["source_rules"]["terminal_decreasing_chain"]
