import pytest

from sgb_multimatrix import (
    FORMAT,
    build_multimatrix_evaluation,
    evaluate_matrix_records,
    matrix_from_record,
    matrix_multiply,
)


def _record(
    *,
    offset=(0, 0, 0),
    scale=1.0,
    parent=-1,
    q=(1, 0, 0, 0),
):
    return {
        "offset_xyz": list(offset),
        "orientation_runtime_order": list(q),
        "scale": scale,
        "parent": parent,
    }


def _identity():
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]


def test_local_matrix_matches_fun_0068cbb0_storage():
    matrix = matrix_from_record(
        _record(offset=(1, 2, 3), scale=2.0)
    )
    assert matrix == pytest.approx([
        2, 0, 0, 0,
        0, 2, 0, 0,
        0, 0, 2, 0,
        1, 2, 3, 1,
    ])


def test_matrix_multiply_uses_row_vector_d3d_order():
    translate_x = matrix_from_record(
        _record(offset=(10, 0, 0))
    )
    scale_two = matrix_from_record(_record(scale=2.0))
    combined = matrix_multiply(translate_x, scale_two)
    assert combined[12:15] == pytest.approx(
        [20.0, 0.0, 0.0]
    )


def test_static_mode_evaluates_local_times_parent_world():
    records = [
        _record(offset=(99, 0, 0), parent=-1),
        _record(offset=(1, 0, 0), parent=0),
        _record(offset=(0, 2, 0), parent=1),
    ]
    root = matrix_from_record(
        _record(offset=(10, 0, 0))
    )
    result = evaluate_matrix_records(
        records,
        root_world_matrix=root,
    )

    assert result["format"] == FORMAT
    assert result["ready"] is True
    assert result["slots"][0]["world_matrix"] == pytest.approx(
        root
    )
    assert result["slots"][1]["world_matrix"][12:15] == (
        pytest.approx([11, 0, 0])
    )
    assert result["slots"][2]["world_matrix"][12:15] == (
        pytest.approx([11, 2, 0])
    )


def test_parent_uses_low_byte_of_serialized_dword():
    records = [
        _record(parent=-1),
        _record(offset=(3, 0, 0), parent=0x100),
    ]
    result = evaluate_matrix_records(
        records,
        root_world_matrix=_identity(),
    )
    assert result["ready"] is True
    assert result["slots"][1]["runtime_parent_index"] == 0
    assert result["slots"][1]["world_matrix"][12] == (
        pytest.approx(3.0)
    )


def test_missing_root_is_explicit_blocker():
    result = evaluate_matrix_records([
        _record(parent=-1),
        _record(parent=0),
    ])
    assert result["ready"] is False
    assert (
        "multimatrix:root-world-matrix-required"
        in result["blocking_reasons"]
    )
    assert all(
        slot["world_matrix"] is None
        for slot in result["slots"]
    )
    assert result["slots"][1]["local_matrix"] is not None


def test_out_of_range_parent_blocks_fail_closed():
    result = evaluate_matrix_records(
        [_record(parent=-1), _record(parent=7)],
        root_world_matrix=_identity(),
    )
    assert result["ready"] is False
    assert (
        "multimatrix:slot-1:parent-out-of-range:7:count=2"
        in result["blocking_reasons"]
    )
    assert result["slots"][1]["world_matrix"] is None


def test_owner_contract_accepts_lod_and_hierarchy_only():
    owner = {
        "format": "SHIFT.SGBObjectRuntime/1",
        "kind": {"text": "HIERARCHY"},
        "matrix_number": 0,
        "matrix_records": [_record(parent=-1)],
    }
    result = build_multimatrix_evaluation(
        owner,
        root_world_matrix=_identity(),
    )
    assert result["ready"] is True
    assert result["owner_kind"] == "HIERARCHY"

    with pytest.raises(
        ValueError,
        match="LOD or HIERARCHY",
    ):
        build_multimatrix_evaluation({
            "format": "SHIFT.SGBObjectRuntime/1",
            "kind": {"text": "OBJECT"},
            "matrix_records": [],
        })
