import pytest

from sgb_multimatrix_runtime import (
    FORMAT,
    build_sgb_multimatrix_world_transforms,
    evaluate_multimatrix_records,
    matrix_from_wxyz_transform,
    matrix_multiply,
)


def _matrix_record(
    *,
    offset=(0.0, 0.0, 0.0),
    orientation=(1.0, 0.0, 0.0, 0.0),
    scale=1.0,
    parent=-1,
):
    return {
        "offset_xyz": list(offset),
        "orientation_runtime_order": list(orientation),
        "scale": scale,
        "parent": parent,
    }


def _object(matrix_number, *, resource="tracks/test/object.meb"):
    report = {
        "format": "SHIFT.SGBObjectRuntime/1",
        "decoded": True,
        "kind": {"text": "OBJECT"},
        "matrix_number": matrix_number,
        "resource_filename": {"text": resource},
    }
    if matrix_number == -1:
        report["explicit_matrix"] = {
            "orientation_runtime_order": [1.0, 0.0, 0.0, 0.0],
            "offset_xyz": [7.0, 8.0, 9.0],
            "scale": 1.5,
        }
    return report


def _container(kind, matrix_number, matrices, children):
    return {
        "format": "SHIFT.SGBObjectRuntime/1",
        "decoded": True,
        "kind": {"text": kind},
        "matrix_number": matrix_number,
        "matrices": len(matrices),
        "subobjects": len(children),
        "matrix_records": matrices,
        "subobject_references": [
            {"index": index, "decoded": True, "report": child}
            for index, child in enumerate(children)
        ],
    }


def _wrapper(report, *, tag="SUMM", index=0):
    return {
        "index": index,
        "offset": 0x100 + index * 0x40,
        "name": {"text": f"{tag}_{index}"},
        "resource": {"text": f"tracks/test/{tag.lower()}_{index}.vhf"},
        "object_payload": {"decoded": True, "report": report},
    }


def _sgb(*records):
    return {
        "format": "SHIFT.SGBRuntime/1",
        "ready": True,
        "chunks": [{"tag": "SUMM", "records": list(records)}],
    }


def test_matrix_multiply_uses_retail_local_times_parent_order():
    local = matrix_from_wxyz_transform(
        [1.0, 0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        2.0,
    )
    parent = matrix_from_wxyz_transform(
        [1.0, 0.0, 0.0, 0.0],
        [10.0, 0.0, 0.0],
        1.0,
    )

    local_parent = matrix_multiply(local, parent)
    parent_local = matrix_multiply(parent, local)

    assert local_parent[12:15] == pytest.approx([11.0, 0.0, 0.0])
    assert parent_local[12:15] == pytest.approx([21.0, 0.0, 0.0])
    assert local_parent != pytest.approx(parent_local)


def test_multimatrix_case1_updates_child_world_from_parent_world():
    report = evaluate_multimatrix_records([
        _matrix_record(offset=(10.0, 0.0, 0.0), parent=-1),
        _matrix_record(offset=(1.0, 0.0, 0.0), scale=2.0, parent=0),
    ])

    assert report["ready"] is True
    assert report["slot_count"] == 2
    assert report["slots"][0]["world_update"] == "initial-local-copy"
    assert report["slots"][0]["world_matrix"][12:15] == pytest.approx(
        [10.0, 0.0, 0.0]
    )
    slot1 = report["slots"][1]
    assert slot1["operation_type"] == 1
    assert slot1["parent_byte"] == 0
    assert slot1["source_slot"] == 1
    assert slot1["world_update"] == (
        "case1:local[source_slot]*world[parent_byte]"
    )
    assert slot1["world_matrix"][12:15] == pytest.approx(
        [11.0, 0.0, 0.0]
    )


def test_root_hierarchy_materializes_world_slots_for_object_children():
    root = _container(
        "HIERARCHY",
        0,
        [
            _matrix_record(offset=(10.0, 0.0, 0.0), parent=-1),
            _matrix_record(offset=(1.0, 0.0, 0.0), parent=0),
            _matrix_record(offset=(0.0, 2.0, 0.0), parent=0),
        ],
        [_object(1), _object(2)],
    )
    report = build_sgb_multimatrix_world_transforms(_sgb(_wrapper(root)))

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["context_count"] == 1
    assert report["object_count"] == 2
    assert report["multimatrix_object_count"] == 2
    assert report["objects"][0]["transform"]["world_matrix"][12:15] == pytest.approx(
        [11.0, 0.0, 0.0]
    )
    assert report["objects"][1]["transform"]["world_matrix"][12:15] == pytest.approx(
        [10.0, 2.0, 0.0]
    )


def test_inherited_lod_uses_parent_context_and_ignores_own_matrix_table_for_context():
    nested_lod = _container(
        "LOD",
        1,
        [_matrix_record(offset=(999.0, 0.0, 0.0), parent=-1)],
        [_object(1)],
    )
    root = _container(
        "HIERARCHY",
        0,
        [
            _matrix_record(offset=(10.0, 0.0, 0.0), parent=-1),
            _matrix_record(offset=(1.0, 0.0, 0.0), parent=0),
        ],
        [nested_lod],
    )
    report = build_sgb_multimatrix_world_transforms(_sgb(_wrapper(root)))

    assert report["ready"] is True
    assert report["context_count"] == 1
    nested = next(
        row for row in report["containers"]
        if row["object_kind"] == "LOD"
    )
    assert nested["context_ownership"] == "inherited"
    assert nested["serialized_matrix_table_used_for_context"] is False
    assert nested["inherited_selector"]["matrix_number"] == 1
    assert nested["inherited_selector"]["world_matrix"][12:15] == pytest.approx(
        [11.0, 0.0, 0.0]
    )
    obj = report["objects"][0]
    assert obj["transform"]["context_id"] == report["contexts"][0]["context_id"]
    assert obj["transform"]["world_matrix"][12:15] == pytest.approx(
        [11.0, 0.0, 0.0]
    )


def test_explicit_object_world_matrix_remains_independent_of_multimatrix():
    report = build_sgb_multimatrix_world_transforms(
        _sgb(_wrapper(_object(-1)))
    )

    assert report["ready"] is True
    assert report["context_count"] == 0
    assert report["explicit_object_count"] == 1
    matrix = report["objects"][0]["transform"]["world_matrix"]
    assert matrix == pytest.approx([
        1.5, 0.0, 0.0, 0.0,
        0.0, 1.5, 0.0, 0.0,
        0.0, 0.0, 1.5, 0.0,
        7.0, 8.0, 9.0, 1.0,
    ])


def test_invalid_multimatrix_parent_blocks_context_and_object():
    root = _container(
        "HIERARCHY",
        0,
        [
            _matrix_record(parent=-1),
            _matrix_record(parent=7),
        ],
        [_object(1)],
    )
    report = build_sgb_multimatrix_world_transforms(_sgb(_wrapper(root)))

    assert report["ready"] is False
    assert any(
        "multimatrix:slot-1:parent-out-of-range:7" in reason
        for reason in report["blocking_reasons"]
    )
    assert report["objects"][0]["ready"] is False


def test_inherited_container_selector_out_of_range_blocks():
    nested = _container(
        "LOD",
        3,
        [_matrix_record(parent=-1)],
        [_object(0)],
    )
    root = _container(
        "HIERARCHY",
        0,
        [_matrix_record(parent=-1)],
        [nested],
    )
    report = build_sgb_multimatrix_world_transforms(_sgb(_wrapper(root)))

    assert report["ready"] is False
    assert any(
        "inherited-selector-out-of-range:3:count=1" in reason
        for reason in report["blocking_reasons"]
    )


def test_wrong_sgb_format_is_rejected():
    with pytest.raises(ValueError, match="SGBRuntime"):
        build_sgb_multimatrix_world_transforms({"format": "wrong"})
