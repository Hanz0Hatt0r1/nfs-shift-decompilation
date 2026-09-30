import pytest

from sgb_multimatrix import (
    ROOT_SOLVE_FORMAT,
    build_multimatrix_root_solve,
    matrix_from_record,
    matrix_multiply,
    solve_root_world_from_selected_slot,
)


def _record(index, *, parent, offset=(0.0, 0.0, 0.0), scale=1.0):
    return {
        "index": index,
        "offset_xyz": list(offset),
        "orientation_runtime_order": [1.0, 0.0, 0.0, 0.0],
        "scale": scale,
        "parent": parent,
    }


def _translation(x, y, z):
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        x, y, z, 1.0,
    ]


def _owner(records):
    return {
        "format": "SHIFT.SGBObjectRuntime/1",
        "kind": {"text": "LOD"},
        "matrix_number": -1,
        "matrix_records": records,
    }


def test_slot_zero_observation_is_the_root():
    observed = _translation(10.0, 20.0, 30.0)
    report = solve_root_world_from_selected_slot(
        [_record(0, parent=-1, offset=(1.0, 2.0, 3.0))],
        0,
        observed,
    )

    assert report["format"] == ROOT_SOLVE_FORMAT
    assert report["ready"] is True
    assert report["selected_slot_chain_to_root"] == []
    assert report["solved_root_world_matrix"] == pytest.approx(observed)
    assert report["reproduced_selected_world_matrix"] == pytest.approx(
        observed
    )
    assert report["max_abs_reproduction_error"] == pytest.approx(0.0)
    assert (
        report["boundary"]["scenegraph_update_history_recovered"]
        is False
    )


def test_child_slot_recovers_root_from_local_chain():
    records = [
        _record(0, parent=-1, offset=(1.0, 2.0, 3.0)),
        _record(1, parent=0, offset=(4.0, 5.0, 6.0), scale=2.0),
        _record(2, parent=1, offset=(-3.0, 1.0, 2.0), scale=0.5),
    ]
    root = _translation(10.0, 20.0, 30.0)
    cumulative = matrix_multiply(
        matrix_from_record(records[2]),
        matrix_from_record(records[1]),
    )
    observed = matrix_multiply(cumulative, root)

    report = solve_root_world_from_selected_slot(
        records,
        2,
        observed,
    )

    assert report["ready"] is True
    assert report["selected_slot_chain_to_root"] == [2, 1]
    assert report["solved_root_world_matrix"] == pytest.approx(
        root, abs=1.0e-6
    )
    assert report["reproduced_selected_world_matrix"] == pytest.approx(
        observed, abs=1.0e-6
    )
    assert report["max_abs_reproduction_error"] <= 1.0e-6


def test_singular_cumulative_local_fails_closed():
    records = [
        _record(0, parent=-1),
        _record(1, parent=0, scale=0.0),
    ]
    report = solve_root_world_from_selected_slot(
        records,
        1,
        _translation(1.0, 2.0, 3.0),
    )

    assert report["ready"] is False
    assert any(
        "affine linear transform is singular" in reason
        for reason in report["blocking_reasons"]
    )
    assert report["solved_root_world_matrix"] is None


def test_forward_parent_chain_is_not_inverted():
    records = [
        _record(0, parent=-1),
        _record(1, parent=2),
        _record(2, parent=0),
    ]
    report = solve_root_world_from_selected_slot(
        records,
        1,
        _translation(1.0, 2.0, 3.0),
    )

    assert report["ready"] is False
    assert (
        "multimatrix-root-solve:slot-1:parent-not-earlier:2"
        in report["blocking_reasons"]
    )


def test_owner_wrapper_preserves_kind_and_contract():
    records = [
        _record(0, parent=-1),
        _record(1, parent=0, offset=(2.0, 0.0, 0.0)),
    ]
    root = _translation(5.0, 6.0, 7.0)
    observed = matrix_multiply(
        matrix_from_record(records[1]),
        root,
    )

    report = build_multimatrix_root_solve(
        _owner(records),
        1,
        observed,
    )

    assert report["ready"] is True
    assert report["owner_kind"] == "LOD"
    assert report["solved_root_world_matrix"] == pytest.approx(root)
