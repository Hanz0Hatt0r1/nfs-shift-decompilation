import pytest

from sgb_multimatrix_evaluation import (
    FORMAT,
    build_sgb_multimatrix_evaluation,
    evaluate_multimatrix_records,
)


def _identity():
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]


def _translation(x, y=0.0, z=0.0):
    value = _identity()
    value[12] = float(x)
    value[13] = float(y)
    value[14] = float(z)
    return value


def _matrix_record(x, *, parent):
    return {
        "offset_xyz": [float(x), 0.0, 0.0],
        "orientation_runtime_order": [1.0, 0.0, 0.0, 0.0],
        "scale": 1.0,
        "parent": parent,
    }


def _object(matrix_number, *, resource="tracks/test/object.meb", x=0.0):
    report = {
        "format": "SHIFT.SGBObjectRuntime/1",
        "decoded": True,
        "kind": {"text": "OBJECT"},
        "matrix_number": matrix_number,
        "resource_filename": {"text": resource},
    }
    if matrix_number == -1:
        report["explicit_matrix"] = {
            "offset_xyz": [float(x), 0.0, 0.0],
            "orientation_runtime_order": [1.0, 0.0, 0.0, 0.0],
            "scale": 1.0,
        }
    return report


def _hierarchy(
    records,
    children,
    *,
    kind="HIERARCHY",
    matrix_number=-1,
):
    return {
        "format": "SHIFT.SGBObjectRuntime/1",
        "decoded": True,
        "kind": {"text": kind},
        "matrix_number": matrix_number,
        "matrix_records": records,
        "subobject_references": [
            {
                "index": index,
                "decoded": True,
                "report": child,
            }
            for index, child in enumerate(children)
        ],
    }


def _sgb(root, *, tag="SUMM", index=0):
    return {
        "format": "SHIFT.SGBRuntime/1",
        "ready": True,
        "chunks": [{
            "tag": tag,
            "records": [{
                "index": index,
                "offset": 0x100,
                "name": {"text": f"{tag}_{index}"},
                "object_payload": {
                    "decoded": True,
                    "report": root,
                },
            }],
        }],
    }


def _base_set(matrix, *, tag="SUMM", index=0, source_backed=True):
    return {
        "format": "SHIFT.SGBMultiMatrixBaseSet/1",
        "bases": [{
            "chunk": tag,
            "source_record_index": index,
            "matrix": matrix,
            "source_backed": source_backed,
            "source": "test-source",
        }],
    }


def test_multimatrix_replaces_root_world_and_multiplies_local_by_parent_world():
    records = [
        _matrix_record(100.0, parent=-1),
        _matrix_record(2.0, parent=0),
        _matrix_record(3.0, parent=1),
    ]
    result = evaluate_multimatrix_records(
        records,
        base_matrix=_translation(10.0),
        base_source_backed=True,
        base_source="source-backed-test",
    )

    assert result["ready"] is True
    assert result["source_backed_world_ready"] is True
    assert result["slots"][0]["local_matrix"] == pytest.approx(
        _translation(100.0)
    )
    assert result["slots"][0]["runtime_world_matrix"] == pytest.approx(
        _translation(10.0)
    )
    assert result["slots"][1]["runtime_world_matrix"] == pytest.approx(
        _translation(12.0)
    )
    assert result["slots"][2]["runtime_world_matrix"] == pytest.approx(
        _translation(15.0)
    )
    assert result["runtime_update_boundary"]["dependent_formula"] == (
        "world[i] = local[i] * world[parent[i]]"
    )


def test_multimatrix_without_base_is_structurally_decoded_but_not_numeric_runtime_world():
    result = evaluate_multimatrix_records([
        _matrix_record(10.0, parent=-1),
        _matrix_record(2.0, parent=0),
    ])

    assert result["status"] == "base-required"
    assert result["ready"] is False
    assert result["base"]["provided"] is False
    assert result["slots"][0]["construction_world_matrix"] == pytest.approx(
        _translation(10.0)
    )
    assert result["slots"][0]["runtime_world_matrix"] is None


def test_nested_lod_inherits_root_multimatrix_and_ignores_own_matrix_table():
    child = _object(2, resource="tracks/test/nested.meb")
    nested_lod = _hierarchy(
        [_matrix_record(999.0, parent=-1)],
        [child],
        kind="LOD",
        matrix_number=1,
    )
    root = _hierarchy(
        [
            _matrix_record(100.0, parent=-1),
            _matrix_record(2.0, parent=0),
            _matrix_record(3.0, parent=1),
        ],
        [nested_lod],
        kind="HIERARCHY",
        matrix_number=0,
    )

    report = build_sgb_multimatrix_evaluation(
        _sgb(root),
        base_set=_base_set(_translation(10.0)),
    )

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["summary"]["object_count"] == 1
    assert report["summary"]["source_backed_world_matrix_ready_count"] == 1

    nested = next(
        row for row in report["hierarchies"]
        if row["object_path"] == [0]
    )
    assert nested["context_inherited"] is True
    assert nested["serialized_matrix_table_ignored_for_runtime_context"] is True
    assert nested["selected_world_matrix"] == pytest.approx(
        _translation(12.0)
    )

    obj = report["objects"][0]
    assert obj["object_path"] == [0, 0]
    assert obj["matrix_number"] == 2
    assert obj["world_matrix"] == pytest.approx(_translation(15.0))
    assert obj["source_backed_world_matrix_ready"] is True
    assert obj["render_binding_admission"] is True


def test_explicit_object_is_source_backed_without_multimatrix_base():
    report = build_sgb_multimatrix_evaluation(
        _sgb(_object(-1, x=42.0))
    )

    assert report["ready"] is True
    assert report["summary"]["root_multimatrix_context_count"] == 0
    obj = report["objects"][0]
    assert obj["transform_mode"] == "explicit-object-transform"
    assert obj["world_matrix"] == pytest.approx(_translation(42.0))
    assert obj["source_backed_world_matrix_ready"] is True
    assert obj["render_binding_admission"] is True


def test_matrix_number_object_remains_blocked_until_root_base_is_supplied():
    root = _hierarchy(
        [_matrix_record(7.0, parent=-1)],
        [_object(0)],
        kind="LOD",
    )
    report = build_sgb_multimatrix_evaluation(_sgb(root))

    assert report["ready"] is False
    assert report["status"] == "partial"
    assert report["summary"]["base_required_object_count"] == 1
    obj = report["objects"][0]
    assert obj["numeric_world_matrix_ready"] is False
    assert "multimatrix-base-required" in obj["blocking_reasons"]
    assert obj["render_binding_admission"] is False


def test_numeric_base_without_source_provenance_does_not_open_render_admission():
    root = _hierarchy(
        [_matrix_record(7.0, parent=-1)],
        [_object(0)],
        kind="LOD",
    )
    report = build_sgb_multimatrix_evaluation(
        _sgb(root),
        base_set=_base_set(_identity(), source_backed=False),
    )

    assert report["numeric_complete"] is True
    assert report["ready"] is False
    obj = report["objects"][0]
    assert obj["numeric_world_matrix_ready"] is True
    assert obj["source_backed_world_matrix_ready"] is False
    assert obj["render_binding_admission"] is False


def test_invalid_dependent_parent_fails_closed():
    result = evaluate_multimatrix_records(
        [
            _matrix_record(0.0, parent=-1),
            _matrix_record(1.0, parent=-1),
        ],
        base_matrix=_identity(),
        base_source_backed=True,
    )

    assert result["ready"] is False
    assert (
        "multimatrix:slot-1:parent-out-of-range:-1:count=2"
        in result["blocking_reasons"]
    )


def test_wrong_sgb_format_is_rejected():
    with pytest.raises(ValueError, match="SGBRuntime"):
        build_sgb_multimatrix_evaluation({"format": "wrong"})
