import pytest

from sgb_render_binding_admission import (
    FORMAT,
    build_sgb_render_binding_admission,
)


def _placement(
    *,
    mode="flat-summ",
    source_record_index=0,
    ready=True,
    spatial_ready=True,
):
    return {
        "placement_index": 0,
        "mode": mode,
        "ready": ready,
        "identity": {"runtime_index": 0},
        "object": {
            "source_record_index": source_record_index,
            "name": "WRAPPER",
            "object_decoded": True,
        },
        "spatial": {
            "scope": "flat-leaf" if mode == "flat-summ" else "partition"
        },
        "render_binding_handoff": {
            "spatial_culling_ready": spatial_ready,
            "draw_admission": False,
        },
    }


def _scene(*placements):
    return {
        "format": "SHIFT.SGBScenePlacement/1",
        "ready": True,
        "placements": list(placements or [_placement()]),
    }


def _object_row(
    *,
    chunk="SUMM",
    source_record_index=0,
    path=(0,),
    world_ready=True,
    resource="tracks/test/object.meb",
):
    matrix = [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        10.0, 20.0, 30.0, 1.0,
    ]
    return {
        "wrapper": {
            "chunk": chunk,
            "source_record_index": source_record_index,
            "source_record_offset": 0x100,
        },
        "object_path": list(path),
        "handoff": {
            "format": "SHIFT.SGBObjectRenderHandoff/1",
            "ready": True,
            "resource": {
                "reference": resource,
                "factory_classification": {
                    "format": "SHIFT.SGBObjectResourceFactory/1",
                    "factory_type": (
                        7
                        if str(resource or "").lower().endswith(
                            (".imb", ".imx")
                        )
                        else 0
                    ),
                    "factory_name": (
                        "MeshInst"
                        if str(resource or "").lower().endswith(
                            (".imb", ".imx")
                        )
                        else "MeshType"
                    ),
                },
            },
            "transform": {
                "mode": "explicit-object-transform",
                "world_matrix": matrix if world_ready else None,
                "world_matrix_ready": world_ready,
            },
        },
    }


def _handoffs(*rows):
    return {
        "format": "SHIFT.SGBObjectRenderHandoffSet/1",
        "ready": True,
        "objects": list(rows or [_object_row()]),
    }


def test_flat_summ_wrapper_joins_to_ready_object_binding():
    report = build_sgb_render_binding_admission(
        _scene(),
        _handoffs(),
    )
    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["binding_count"] == 1
    assert report["admitted_binding_count"] == 1

    row = report["bindings"][0]
    assert row["placement"]["wrapper_chunk"] == "SUMM"
    assert row["object"]["object_path"] == [0]
    assert row["object"]["resource_reference"] == "tracks/test/object.meb"
    assert row["object"]["resource_factory"]["factory_type"] == 0
    assert row["object"]["resource_factory"]["factory_name"] == "MeshType"
    assert row["object"]["world_matrix"][12:15] == pytest.approx(
        [10.0, 20.0, 30.0]
    )
    assert row["scene_admission"]["admitted_to_generic_render_binding"] is True
    assert row["scene_admission"]["draw_admission"] is False


def test_part_node_uses_node_wrapper_identity():
    report = build_sgb_render_binding_admission(
        _scene(_placement(mode="part-node", source_record_index=2)),
        _handoffs(_object_row(chunk="NODE", source_record_index=2)),
    )
    assert report["ready"] is True
    assert report["bindings"][0]["placement"]["wrapper_chunk"] == "NODE"


def test_one_wrapper_can_expand_to_multiple_object_children():
    report = build_sgb_render_binding_admission(
        _scene(),
        _handoffs(
            _object_row(path=(0,)),
            _object_row(path=(1,)),
        ),
    )
    assert report["ready"] is True
    assert report["binding_count"] == 2
    assert [row["object"]["object_path"] for row in report["bindings"]] == [
        [0],
        [1],
    ]


def test_missing_numeric_matrix_blocks_only_that_binding():
    report = build_sgb_render_binding_admission(
        _scene(),
        _handoffs(
            _object_row(path=(0,), world_ready=True),
            _object_row(path=(1,), world_ready=False),
        ),
    )
    assert report["ready"] is False
    assert report["binding_count"] == 2
    assert report["admitted_binding_count"] == 1
    assert report["blocked_binding_count"] == 1
    assert report["bindings"][0]["ready"] is True
    assert report["bindings"][1]["ready"] is False
    assert (
        "numeric-world-matrix-not-ready"
        in report["bindings"][1]["blocking_reasons"]
    )


def test_placement_without_matching_wrapper_blocks_join():
    report = build_sgb_render_binding_admission(
        _scene(_placement(source_record_index=7)),
        _handoffs(_object_row(source_record_index=0)),
    )
    assert report["ready"] is False
    assert report["binding_count"] == 0
    assert report["unmatched_placement_indices"] == [0]
    assert (
        "sgb-render-binding:placements-without-object-handoff:0"
        in report["blocking_reasons"]
    )


def test_orphan_handoff_is_reported_without_blocking_ready_placement():
    report = build_sgb_render_binding_admission(
        _scene(),
        _handoffs(
            _object_row(source_record_index=0),
            _object_row(source_record_index=99),
        ),
    )
    assert report["ready"] is True
    assert report["binding_count"] == 1
    assert report["orphan_object_handoffs"] == [{
        "handoff_index": 1,
        "wrapper_chunk": "SUMM",
        "source_record_index": 99,
        "object_path": [0],
    }]


def test_missing_resource_or_spatial_geometry_blocks_admission():
    report = build_sgb_render_binding_admission(
        _scene(_placement(spatial_ready=False)),
        _handoffs(_object_row(resource=None)),
    )
    row = report["bindings"][0]
    assert report["ready"] is False
    assert "resource-reference-missing" in row["blocking_reasons"]
    assert "spatial-culling-not-ready" in row["blocking_reasons"]


def test_wrong_contract_formats_are_rejected():
    with pytest.raises(ValueError, match="SGBScenePlacement"):
        build_sgb_render_binding_admission(
            {"format": "wrong"},
            _handoffs(),
        )
    with pytest.raises(ValueError, match="SGBObjectRenderHandoffSet"):
        build_sgb_render_binding_admission(
            _scene(),
            {"format": "wrong"},
        )
