import pytest

from sgb_multimatrix import matrix_from_record, matrix_multiply
from sgb_multimatrix_root_promotion import (
    build_root_promoted_object_handoffs,
)
from sgb_object_render_handoff import (
    build_sgb_object_render_handoff_set,
)
from sgb_render_binding_admission import (
    build_sgb_render_binding_admission,
)


def _record(index, *, parent, offset):
    return {
        "index": index,
        "offset_xyz": list(offset),
        "orientation_runtime_order": [1.0, 0.0, 0.0, 0.0],
        "scale": 1.0,
        "parent": parent,
    }


def _object(matrix_number=1):
    return {
        "format": "SHIFT.SGBObjectRuntime/1",
        "decoded": True,
        "kind": {"text": "OBJECT"},
        "matrix_number": matrix_number,
        "resource_filename": {"text": "tracks/test/runtime.imb"},
    }


def _fixture():
    records = [
        _record(0, parent=-1, offset=(0.0, 0.0, 0.0)),
        _record(1, parent=0, offset=(4.0, 0.0, 0.0)),
    ]
    owner = {
        "format": "SHIFT.SGBObjectRuntime/1",
        "decoded": True,
        "kind": {"text": "LOD"},
        "matrix_number": -1,
        "matrix_records": records,
        "subobject_references": [{
            "index": 0,
            "decoded": True,
            "report": _object(),
        }],
    }
    sgb = {
        "format": "SHIFT.SGBRuntime/1",
        "ready": True,
        "chunks": [{
            "tag": "SUMM",
            "records": [{
                "index": 7,
                "offset": 0x100,
                "name": {"text": "WRAPPER"},
                "resource": {"text": "tracks/test/wrapper.vhf"},
                "object_payload": {
                    "decoded": True,
                    "report": owner,
                },
            }],
        }],
    }
    root = [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        10.0, 20.0, 30.0, 1.0,
    ]
    expected_world = matrix_multiply(
        matrix_from_record(records[1]),
        root,
    )
    consensus = {
        "format": "SHIFT.SGBMultiMatrixRootConsensus/1",
        "version": 1,
        "status": "ready",
        "ready": True,
        "blocking_reasons": [],
        "consensus": [{
            "wrapper": {
                "chunk": "SUMM",
                "source_record_index": 7,
            },
            "status": "ready",
            "ready": True,
            "blocking_reasons": [],
            "authorizes_current_wrapper_root": True,
            "root_world_matrix": root,
            "root_float32_hex": "00" * 64,
            "support_resource_count": 2,
            "distinct_cumulative_local_count": 2,
            "witness_count": 2,
        }],
        "boundary": {
            "authorizes_current_wrapper_root_only": True,
            "scenegraph_update_history_recovered": False,
            "authorizes_render_admission": False,
        },
    }
    return sgb, consensus, root, expected_world


def _placement():
    return {
        "format": "SHIFT.SGBScenePlacement/1",
        "ready": True,
        "placements": [{
            "placement_index": 0,
            "mode": "flat-summ",
            "ready": True,
            "identity": {"runtime_index": 0},
            "object": {
                "source_record_index": 7,
                "name": "WRAPPER",
                "object_decoded": True,
            },
            "spatial": {"scope": "flat-leaf"},
            "render_binding_handoff": {
                "spatial_culling_ready": True,
                "draw_admission": False,
            },
        }],
    }


def test_ready_consensus_promotes_matrix_number_world():
    sgb, consensus, root, expected_world = _fixture()

    baseline = build_sgb_object_render_handoff_set(sgb)
    assert baseline["numeric_world_matrix_ready_count"] == 0
    assert baseline["objects"][0]["handoff"]["transform"][
        "world_matrix_ready"
    ] is False

    report = build_root_promoted_object_handoffs(
        sgb,
        consensus,
    )

    assert report["format"] == "SHIFT.SGBObjectRenderHandoffSet/1"
    assert report["numeric_world_matrix_ready_count"] == 1
    row = report["objects"][0]
    transform = row["handoff"]["transform"]
    assert transform["world_matrix_ready"] is True
    assert transform["world_matrix"] == pytest.approx(expected_world)
    assert row["runtime_wrapper_root"]["world_matrix"] == pytest.approx(root)

    promotion = report["runtime_root_promotion"]
    assert promotion["format"] == "SHIFT.SGBMultiMatrixRootPromotion/1"
    assert promotion["wrapper_root_count"] == 1
    assert promotion["promoted_matrix_object_count"] == 1
    assert promotion["remaining_unresolved_matrix_object_count"] == 0
    assert promotion["promoted_object_indices"] == [0]
    assert (
        promotion["boundary"]["scenegraph_update_history_recovered"]
        is False
    )
    assert (
        promotion["boundary"]["direct_render_admission_authorized"]
        is False
    )


def test_promoted_handoff_enters_existing_scene_admission():
    sgb, consensus, _, expected_world = _fixture()
    handoffs = build_root_promoted_object_handoffs(
        sgb,
        consensus,
    )

    admission = build_sgb_render_binding_admission(
        _placement(),
        handoffs,
    )

    assert admission["ready"] is True
    assert admission["admitted_binding_count"] == 1
    binding = admission["bindings"][0]
    assert binding["ready"] is True
    assert binding["object"]["transform_mode"] == (
        "parent-multimatrix-slot"
    )
    assert binding["object"]["world_matrix"] == pytest.approx(
        expected_world
    )
    assert (
        binding["scene_admission"][
            "admitted_to_generic_render_binding"
        ]
        is True
    )


def test_only_ready_authorized_consensus_rows_are_applied():
    sgb, consensus, _, _ = _fixture()
    consensus["consensus"][0]["ready"] = False
    consensus["consensus"][0]["authorizes_current_wrapper_root"] = False

    with pytest.raises(
        ValueError,
        match="contains no ready wrapper roots",
    ):
        build_root_promoted_object_handoffs(
            sgb,
            consensus,
        )


def test_stale_wrapper_consensus_is_rejected():
    sgb, consensus, _, _ = _fixture()
    consensus["consensus"][0]["wrapper"]["source_record_index"] = 99

    with pytest.raises(
        ValueError,
        match="absent from SGB runtime",
    ):
        build_root_promoted_object_handoffs(
            sgb,
            consensus,
        )


def test_consensus_cannot_claim_render_admission_or_history():
    sgb, consensus, _, _ = _fixture()
    consensus["boundary"]["authorizes_render_admission"] = True

    with pytest.raises(
        ValueError,
        match="must not directly authorize render admission",
    ):
        build_root_promoted_object_handoffs(
            sgb,
            consensus,
        )

    consensus["boundary"]["authorizes_render_admission"] = False
    consensus["boundary"]["scenegraph_update_history_recovered"] = True
    with pytest.raises(
        ValueError,
        match="must not claim SceneGraph update history",
    ):
        build_root_promoted_object_handoffs(
            sgb,
            consensus,
        )
