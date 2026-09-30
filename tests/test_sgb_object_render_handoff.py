import pytest

from sgb_object_render_handoff import (
    FORMAT,
    build_object_render_handoff,
    build_sgb_object_render_handoff_set,
)


def _object(*, matrix_number=-1, resource="tracks/test/object.meb"):
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
            "offset_xyz": [10.0, 20.0, 30.0],
            "scale": 2.0,
        }
    return report


def _parent(child, *, kind="LOD"):
    return {
        "format": "SHIFT.SGBObjectRuntime/1",
        "decoded": True,
        "kind": {"text": kind},
        "matrix_number": -1,
        "matrix_records": [{
            "index": 0,
            "offset_xyz": [1.0, 2.0, 3.0],
            "orientation_runtime_order": [1.0, 0.0, 0.0, 0.0],
            "scale": 1.0,
            "parent": -1,
        }],
        "subobject_references": [{
            "index": 0,
            "decoded": True,
            "report": child,
        }],
    }


def _wrapper(index, report, *, tag="SUMM"):
    return {
        "index": index,
        "offset": 0x100 + index * 0x40,
        "name": {"text": f"{tag}_{index}"},
        "resource": {"text": f"tracks/test/{tag.lower()}_{index}.vhf"},
        "object_payload": {
            "decoded": True,
            "report": report,
        },
    }


def test_explicit_object_transform_materializes_source_equivalent_matrix():
    handoff = build_object_render_handoff(_object())

    assert handoff["ready"] is True
    assert handoff["resource"]["reference"] == "tracks/test/object.meb"
    assert handoff["resource"]["runtime_descriptor_offset"] == 0x80

    transform = handoff["transform"]
    assert transform["mode"] == "explicit-object-transform"
    assert transform["world_matrix_ready"] is True
    assert transform["world_matrix"] == pytest.approx([
        2.0, 0.0, 0.0, 0.0,
        0.0, 2.0, 0.0, 0.0,
        0.0, 0.0, 2.0, 0.0,
        10.0, 20.0, 30.0, 1.0,
    ])
    assert handoff["render_binding_boundary"][
        "numeric_world_matrix_ready"
    ] is True
    assert handoff["render_binding_boundary"]["draw_admission"] is False


def test_parent_matrix_number_selects_multimatrix_slot_without_guessing_world_matrix():
    parent = _parent(_object(matrix_number=0))
    child = parent["subobject_references"][0]["report"]

    handoff = build_object_render_handoff(
        child,
        parent_object_report=parent,
    )

    assert handoff["ready"] is True
    transform = handoff["transform"]
    assert transform["mode"] == "parent-multimatrix-slot"
    assert transform["matrix_number"] == 0
    assert transform["runtime_slot_stride"] == 0x40
    assert transform["runtime_slot_offset"] == 0
    assert transform["selected_parent_matrix_record"]["parent"] == -1
    assert transform["world_matrix"] is None
    assert transform["world_matrix_ready"] is False
    assert transform["selector_ready"] is True


def test_parent_matrix_number_out_of_range_blocks():
    parent = _parent(_object(matrix_number=2))
    child = parent["subobject_references"][0]["report"]

    handoff = build_object_render_handoff(
        child,
        parent_object_report=parent,
    )

    assert handoff["ready"] is False
    assert (
        "object-render:matrix-number-out-of-range:2:count=1"
        in handoff["blocking_reasons"]
    )


def test_resource_reference_is_required():
    handoff = build_object_render_handoff(_object(resource=None))

    assert handoff["ready"] is False
    assert (
        "object-render:resource-reference-missing"
        in handoff["blocking_reasons"]
    )


def test_sgb_runtime_collection_walks_recursive_lod_objects_and_top_level_object():
    nested = _object(matrix_number=0, resource="tracks/test/nested.meb")
    report = {
        "format": "SHIFT.SGBRuntime/1",
        "ready": True,
        "chunks": [
            {
                "tag": "SUMM",
                "records": [
                    _wrapper(0, _parent(nested)),
                    _wrapper(
                        1,
                        _object(
                            matrix_number=-1,
                            resource="tracks/test/top.meb",
                        ),
                    ),
                ],
            }
        ],
    }

    handoffs = build_sgb_object_render_handoff_set(report)

    assert handoffs["format"] == FORMAT
    assert handoffs["ready"] is True
    assert handoffs["object_count"] == 2
    assert handoffs["explicit_transform_count"] == 1
    assert handoffs["parent_multimatrix_slot_count"] == 1
    assert handoffs["numeric_world_matrix_ready_count"] == 1
    assert handoffs["objects"][0]["object_path"] == [0]
    assert handoffs["objects"][0]["wrapper"]["chunk"] == "SUMM"
    assert handoffs["objects"][1]["object_path"] == []


def test_non_object_single_handoff_is_rejected():
    with pytest.raises(ValueError, match="OBJECT payloads only"):
        build_object_render_handoff({
            "format": "SHIFT.SGBObjectRuntime/1",
            "kind": {"text": "LOD"},
        })


def test_wrong_sgb_format_is_rejected():
    with pytest.raises(ValueError, match="SGBRuntime"):
        build_sgb_object_render_handoff_set({"format": "wrong"})



def test_nested_lod_object_selector_uses_inherited_root_multimatrix_table():
    child = _object(matrix_number=2, resource="tracks/test/deep.meb")
    nested_lod = {
        "format": "SHIFT.SGBObjectRuntime/1",
        "decoded": True,
        "kind": {"text": "LOD"},
        "matrix_number": 1,
        "matrix_records": [{
            "index": 0,
            "offset_xyz": [999.0, 0.0, 0.0],
            "orientation_runtime_order": [1.0, 0.0, 0.0, 0.0],
            "scale": 1.0,
            "parent": -1,
        }],
        "subobject_references": [{
            "index": 0,
            "decoded": True,
            "report": child,
        }],
    }
    root = {
        "format": "SHIFT.SGBObjectRuntime/1",
        "decoded": True,
        "kind": {"text": "HIERARCHY"},
        "matrix_number": 0,
        "matrix_records": [
            {
                "index": 0,
                "offset_xyz": [0.0, 0.0, 0.0],
                "orientation_runtime_order": [1.0, 0.0, 0.0, 0.0],
                "scale": 1.0,
                "parent": -1,
            },
            {
                "index": 1,
                "offset_xyz": [1.0, 0.0, 0.0],
                "orientation_runtime_order": [1.0, 0.0, 0.0, 0.0],
                "scale": 1.0,
                "parent": 0,
            },
            {
                "index": 2,
                "offset_xyz": [2.0, 0.0, 0.0],
                "orientation_runtime_order": [1.0, 0.0, 0.0, 0.0],
                "scale": 1.0,
                "parent": 0,
            },
        ],
        "subobject_references": [{
            "index": 0,
            "decoded": True,
            "report": nested_lod,
        }],
    }
    report = {
        "format": "SHIFT.SGBRuntime/1",
        "ready": True,
        "chunks": [{
            "tag": "SUMM",
            "records": [_wrapper(0, root)],
        }],
    }

    handoffs = build_sgb_object_render_handoff_set(report)

    assert handoffs["ready"] is True
    assert handoffs["object_count"] == 1
    row = handoffs["objects"][0]
    assert row["object_path"] == [0, 0]
    selected = row["handoff"]["transform"]["selected_parent_matrix_record"]
    assert selected["index"] == 2
    assert selected["offset_xyz"] == [2.0, 0.0, 0.0]
    assert selected["offset_xyz"] != [999.0, 0.0, 0.0]
