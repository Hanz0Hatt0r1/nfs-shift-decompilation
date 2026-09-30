import pytest

from sgb_root_transform import (
    FORMAT,
    build_root_transform_state,
    constructor_root_matrix,
)


def _record(*, offset=(0, 0, 0), scale=1.0, parent=-1):
    return {
        "offset_xyz": list(offset),
        "orientation_runtime_order": [1, 0, 0, 0],
        "scale": scale,
        "parent": parent,
    }


def _owner(kind="LOD"):
    return {
        "format": "SHIFT.SGBObjectRuntime/1",
        "kind": {"text": kind},
        "matrix_records": [
            _record(offset=(1, 2, 3), parent=-1),
            _record(offset=(4, 0, 0), parent=0),
        ],
    }


def test_constructor_root_is_serialized_local_slot_zero():
    root = constructor_root_matrix(_owner())
    assert root[12:15] == pytest.approx([1, 2, 3])


def test_unknown_update_history_is_fail_closed_but_keeps_initial_evidence():
    state = build_root_transform_state(_owner())
    assert state["format"] == FORMAT
    assert state["ready"] is False
    assert state["constructor_root_matrix"][12:15] == pytest.approx([1, 2, 3])
    assert state["current_root_world_matrix"] is None
    assert (
        "sgb-root:scenegraph-update-history-unknown"
        in state["blocking_reasons"]
    )


def test_known_empty_update_history_promotes_constructor_state():
    state = build_root_transform_state(_owner(), scenegraph_updates=[])
    assert state["ready"] is True
    assert state["current_root_source"] == "constructor-initial-world-slot-0"
    assert state["current_root_world_matrix"][12:15] == pytest.approx([1, 2, 3])


def test_last_scenegraph_update_replaces_constructor_root_exactly():
    first = [
        1, 0, 0, 0,
        0, 1, 0, 0,
        0, 0, 1, 0,
        10, 20, 30, 1,
    ]
    second = [
        2, 0, 0, 0,
        0, 2, 0, 0,
        0, 0, 2, 0,
        40, 50, 60, 1,
    ]
    state = build_root_transform_state(
        _owner(), scenegraph_updates=[first, second]
    )
    assert state["ready"] is True
    assert state["scenegraph_update_count"] == 2
    assert state["current_root_source"] == "scenegraph-transform-update"
    assert state["current_root_world_matrix"] == pytest.approx(second)


def test_malformed_update_is_blocked():
    state = build_root_transform_state(
        _owner(), scenegraph_updates=[[1, 2, 3]]
    )
    assert state["ready"] is False
    assert state["current_root_world_matrix"] is None
    assert any(
        "must contain 16 values" in row
        for row in state["blocking_reasons"]
    )


def test_only_lod_and_hierarchy_are_valid_owners():
    with pytest.raises(ValueError, match="LOD or HIERARCHY"):
        constructor_root_matrix(_owner("OBJECT"))
