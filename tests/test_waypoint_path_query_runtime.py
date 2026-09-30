import math
import struct

import pytest

from waypoint_base_runtime import (
    ACTIVE_MARKER_OFFSET,
    BRANCH_ID_OFFSET,
    NEXT_LINK_OFFSET,
    SIZE,
)
from waypoint_path_query_runtime import (
    ANY_BRANCH_ID,
    BRANCH_FILTER_INSTRUCTION,
    FINAL_ORIENTATION_BLOCK,
    FINAL_THRESHOLD_COMPARE,
    INITIAL_SCORE_BITS,
    ORIENTATION_SWITCH_THRESHOLD_BITS,
    ORIENTATION_X_OFFSET,
    ORIENTATION_Z_OFFSET,
    QUERY_POSITION_OFFSET,
    describe_waypoint_path_query_runtime,
    orientation_switch_dot,
    path_query_score,
    select_nearest_path_waypoint,
)


def _record(
    query_position=(0.0, 0.0, 0.0),
    *,
    branch_id=0,
    active_marker=1,
    orientation=(1.0, 0.0),
    next_pointer=0,
):
    blob = bytearray(SIZE)
    struct.pack_into("<fff", blob, QUERY_POSITION_OFFSET, *query_position)
    struct.pack_into("<i", blob, BRANCH_ID_OFFSET, branch_id)
    struct.pack_into("<H", blob, ACTIVE_MARKER_OFFSET, active_marker)
    struct.pack_into("<f", blob, ORIENTATION_X_OFFSET, orientation[0])
    struct.pack_into("<f", blob, ORIENTATION_Z_OFFSET, orientation[1])
    struct.pack_into("<I", blob, NEXT_LINK_OFFSET, next_pointer)
    return bytes(blob)


def test_metric_is_retail_dx2_plus_dz2_plus_dy4_not_euclidean():
    # Euclidean squared distance would prefer the dy=2 row (4 < 9).
    # Retail FUN_007189a0 raises dy^2 to the second power, so 9 < 16.
    assert path_query_score((0, 0, 0), (3, 0, 0)) == pytest.approx(9.0)
    assert path_query_score((0, 0, 0), (0, 2, 0)) == pytest.approx(16.0)

    base = 0x00600000
    records = b"".join([
        _record((3, 0, 0), orientation=(1, 0)),
        _record((0, 2, 0), orientation=(0, 1)),
    ])
    row = select_nearest_path_waypoint(
        records,
        (0, 0, 0),
        base_address=base,
    )
    assert row is not None
    assert row["selected_index"] == 0
    assert row["selected_score"] == pytest.approx(9.0)
    assert row["returned_pointer"] == base


def test_selector_minus_one_accepts_any_branch_but_specific_selector_filters():
    base = 0x00610000
    records = b"".join([
        _record((4, 0, 0), branch_id=3),
        _record((1, 0, 0), branch_id=7),
    ])

    any_row = select_nearest_path_waypoint(
        records,
        (0, 0, 0),
        branch_id=ANY_BRANCH_ID,
        base_address=base,
    )
    assert any_row is not None
    assert any_row["selected_index"] == 1
    assert any_row["selected_branch_id"] == 7

    branch_three = select_nearest_path_waypoint(
        records,
        (0, 0, 0),
        branch_id=3,
        base_address=base,
    )
    assert branch_three is not None
    assert branch_three["selected_index"] == 0
    assert branch_three["selected_branch_id"] == 3


def test_branch_selector_is_integer_abi_not_ghidra_float_signature():
    records = _record()
    with pytest.raises(TypeError):
        select_nearest_path_waypoint(records, (0, 0, 0), branch_id=0.0)
    with pytest.raises(ValueError, match="signed int32"):
        select_nearest_path_waypoint(
            records,
            (0, 0, 0),
            branch_id=0x80000000,
        )


def test_inactive_record_is_rejected_even_when_closest():
    base = 0x00620000
    records = b"".join([
        _record((0.1, 0, 0), active_marker=0),
        _record((5, 0, 0), active_marker=1),
    ])
    row = select_nearest_path_waypoint(
        records,
        (0, 0, 0),
        base_address=base,
    )
    assert row is not None
    assert row["selected_index"] == 1
    assert row["selected_active_marker"] == 1


def test_strict_less_than_keeps_first_equal_score():
    base = 0x00630000
    records = b"".join([
        _record((1, 0, 0)),
        _record((-1, 0, 0)),
    ])
    row = select_nearest_path_waypoint(
        records,
        (0, 0, 0),
        base_address=base,
    )
    assert row is not None
    assert row["selected_index"] == 0


def test_negative_orientation_dot_returns_next_pointer():
    base = 0x00640000
    next_pointer = base + SIZE
    records = b"".join([
        # record_x-query_x = +2, orientation_x=-1 => dot=-2
        _record(
            (2, 0, 0),
            orientation=(-1, 0),
            next_pointer=next_pointer,
        ),
        _record((20, 0, 0)),
    ])
    row = select_nearest_path_waypoint(
        records,
        (0, 0, 0),
        base_address=base,
    )
    assert row is not None
    assert row["selected_index"] == 0
    assert row["orientation_dot"] == pytest.approx(-2.0)
    assert row["switched_to_next"] is True
    assert row["next_pointer"] == next_pointer
    assert row["returned_pointer"] == next_pointer
    assert row["returned_index"] == 1


def test_negative_orientation_dot_returns_null_when_next_link_is_null():
    base = 0x00650000
    records = _record(
        (2, 0, 0),
        orientation=(-1, 0),
        next_pointer=0,
    )
    row = select_nearest_path_waypoint(
        records,
        (0, 0, 0),
        base_address=base,
    )
    assert row is not None
    assert row["switched_to_next"] is True
    assert row["returned_pointer"] == 0
    assert row["returned_index"] is None


def test_zero_or_positive_orientation_dot_keeps_selected_record():
    base = 0x00660000
    zero_dot = select_nearest_path_waypoint(
        _record((0, 0, 0), orientation=(-1, 0), next_pointer=0x12345678),
        (0, 0, 0),
        base_address=base,
    )
    assert zero_dot is not None
    assert zero_dot["orientation_dot"] == 0.0
    assert zero_dot["switched_to_next"] is False
    assert zero_dot["returned_pointer"] == base

    positive_dot = select_nearest_path_waypoint(
        _record((2, 0, 0), orientation=(1, 0), next_pointer=0x12345678),
        (0, 0, 0),
        base_address=base,
    )
    assert positive_dot is not None
    assert positive_dot["orientation_dot"] == pytest.approx(2.0)
    assert positive_dot["switched_to_next"] is False
    assert positive_dot["returned_pointer"] == base


def test_orientation_dot_uses_only_x_z_components():
    assert orientation_switch_dot(
        (0, 999, 0),
        (2, -999, 3),
        -2,
        4,
    ) == pytest.approx(8.0)


def test_count_bounds_and_no_candidate_behavior():
    records = _record(active_marker=0)
    assert select_nearest_path_waypoint(records, (0, 0, 0)) is None
    with pytest.raises(ValueError, match="exceeds"):
        select_nearest_path_waypoint(records, (0, 0, 0), count=2)
    with pytest.raises(ValueError, match="exceeds"):
        select_nearest_path_waypoint(records, (0, 0, 0), count=-1)


def test_descriptor_freezes_pe_constants_and_instruction_anchors():
    report = describe_waypoint_path_query_runtime()
    assert report["function_address"] == 0x007189A0
    assert report["score"]["expression"] == "dx^2 + dz^2 + dy^4"
    assert report["score"]["initial_limit_bits"] == INITIAL_SCORE_BITS == 0x7CF0BDC2
    assert report["branch_selector"]["any_value"] == -1
    assert BRANCH_FILTER_INSTRUCTION in report["branch_selector"]["instruction_addresses"]
    assert report["final_switch"]["threshold_bits"] == ORIENTATION_SWITCH_THRESHOLD_BITS == 0
    assert report["final_switch"]["condition"] == "dot < 0.0"
    assert report["final_switch"]["block_address"] == FINAL_ORIENTATION_BLOCK == 0x00718C9A
    assert report["final_switch"]["compare_address"] == FINAL_THRESHOLD_COMPARE == 0x00718CD7
    assert report["final_switch"]["null_next_is_returned_as_null"] is True
    assert "intentionally structural" in report["evidence_boundary"]
