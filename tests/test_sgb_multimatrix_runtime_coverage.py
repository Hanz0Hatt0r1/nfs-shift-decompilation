import pytest

from sgb_multimatrix import matrix_from_record, matrix_multiply
from sgb_multimatrix_runtime_coverage import (
    FORMAT,
    build_multimatrix_runtime_coverage,
)


SHA_A = "a" * 64
SHA_B = "b" * 64


def _record(index, *, parent, offset):
    return {
        "index": index,
        "offset_xyz": list(offset),
        "orientation_runtime_order": [1.0, 0.0, 0.0, 0.0],
        "scale": 1.0,
        "parent": parent,
    }


def _object(matrix_number, resource):
    return {
        "format": "SHIFT.SGBObjectRuntime/1",
        "decoded": True,
        "kind": {"text": "OBJECT"},
        "matrix_number": matrix_number,
        "resource_filename": {"text": resource},
    }


def _fixture():
    records = [
        _record(0, parent=-1, offset=(0.0, 0.0, 0.0)),
        _record(1, parent=0, offset=(1.0, 0.0, 0.0)),
        _record(2, parent=0, offset=(0.0, 2.0, 0.0)),
    ]
    owner = {
        "format": "SHIFT.SGBObjectRuntime/1",
        "decoded": True,
        "kind": {"text": "LOD"},
        "matrix_number": -1,
        "matrix_records": records,
        "subobject_references": [
            {
                "index": 0,
                "decoded": True,
                "report": _object(
                    1,
                    "tracks/test/a.imb",
                ),
            },
            {
                "index": 1,
                "decoded": True,
                "report": _object(
                    2,
                    "tracks/test/b.imb",
                ),
            },
        ],
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

    placement = {
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

    root = [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        10.0, 20.0, 30.0, 1.0,
    ]
    world_a = matrix_multiply(
        matrix_from_record(records[1]),
        root,
    )
    world_b = matrix_multiply(
        matrix_from_record(records[2]),
        root,
    )

    def observation(binding, draw, start, matrix):
        return {
            "binding_index": binding,
            "frame": 1,
            "draw_index": draw,
            "status": "observed",
            "constant_state": {
                "vertex": {
                    str(start + row): list(
                        matrix[row * 4:(row + 1) * 4]
                    )
                    for row in range(4)
                },
                "pixel": {},
            },
        }

    capture = {
        "format": "SHIFT.IMBRuntimeCapturePipeline/1",
        "pipeline_ready": True,
        "resource_results": [
            {
                "resource_index": 0,
                "archive": "TRACK.bff",
                "resource_path": "tracks/test/a.imb",
                "resource_sha256": SHA_A,
                "candidate_binding_indices": [0],
                "runtime_evidence": {
                    "same_instance_gate": {
                        "ready": True,
                    },
                },
                "attributed_texture_observations": [
                    observation(0, 3, 20, world_a),
                ],
            },
            {
                "resource_index": 1,
                "archive": "TRACK.bff",
                "resource_path": "tracks/test/b.imb",
                "resource_sha256": SHA_B,
                "candidate_binding_indices": [1],
                "runtime_evidence": {
                    "same_instance_gate": {
                        "ready": True,
                    },
                },
                "attributed_texture_observations": [
                    observation(1, 4, 30, world_b),
                ],
            },
        ],
    }

    manifest = [
        {
            "archive": "TRACK.bff",
            "path": "tracks/test/a.imb",
            "sha256": SHA_A,
        },
        {
            "archive": "TRACK.bff",
            "path": "tracks/test/b.imb",
            "sha256": SHA_B,
        },
    ]
    return placement, sgb, capture, manifest, root


def test_runtime_coverage_measures_consensus_resolution_and_admission():
    placement, sgb, capture, manifest, root = _fixture()

    report = build_multimatrix_runtime_coverage(
        placement,
        sgb,
        capture,
        manifest,
    )

    assert report["format"] == FORMAT
    assert report["status"] == "measured"
    assert report["ready"] is True
    coverage = report["coverage"]
    assert coverage["runtime_resource_count"] == 2
    assert coverage["matched_runtime_resource_count"] == 2
    assert coverage["matrix_object_count"] == 2
    assert coverage["baseline_numeric_matrix_object_count"] == 0
    assert coverage["ready_consensus_owner_count"] == 1
    assert coverage["consensus_resolved_matrix_object_count"] == 2
    assert coverage["remaining_unresolved_matrix_object_count"] == 0
    assert coverage["promoted_numeric_matrix_object_count"] == 2
    assert coverage["baseline_admitted_binding_count"] == 0
    assert coverage["promoted_admitted_binding_count"] == 2
    assert coverage["newly_admitted_binding_count"] == 2

    assert len(report["resolved_matrix_objects"]) == 2
    assert {
        row["matrix_number"]
        for row in report["resolved_matrix_objects"]
    } == {1, 2}
    assert all(
        row["current_root_source"]
        == "phase596-runtime-root-consensus"
        for row in report["resolved_matrix_objects"]
    )
    assert all(
        row["runtime_root_consensus"] is not None
        for row in report["resolved_matrix_objects"]
    )
    consensus = report["stages"]["root_consensus"]
    assert consensus["ready"] is True
    assert consensus["ready_consensus_count"] == 1
    assert report["boundary"]["new_transform_inference"] is False
    assert (
        report["boundary"]["scenegraph_update_history_recovered"]
        is False
    )


def test_incomplete_capture_is_reported_blocked_without_guessing():
    placement, sgb, capture, manifest, _ = _fixture()
    capture["resource_results"][1]["runtime_evidence"][
        "same_instance_gate"
    ]["ready"] = False

    report = build_multimatrix_runtime_coverage(
        placement,
        sgb,
        capture,
        manifest,
    )

    assert report["ready"] is False
    assert report["status"] == "blocked"
    assert report["coverage"]["matched_runtime_resource_count"] == 1
    assert report["coverage"]["ready_consensus_owner_count"] == 0
    assert report["coverage"]["consensus_resolved_matrix_object_count"] == 0
    assert report["coverage"]["promoted_numeric_matrix_object_count"] == 0
    assert report["coverage"]["newly_admitted_binding_count"] == 0
    assert report["stages"]["root_consensus"]["ready"] is False
    assert report["stages"]["root_consensus"]["status"] == "blocked"
    assert report["coverage"]["consensus_hypothesis_count"] == 0
    assert report["coverage"]["consensus_eligible_root_count"] == 0
    assert any(
        "runtime-same-instance-gate-not-ready" in reason
        for reason in report["blocking_reasons"]
    )


def test_wrong_input_contracts_remain_rejected():
    placement, sgb, capture, manifest, _ = _fixture()

    with pytest.raises(ValueError, match="SGBScenePlacement"):
        build_multimatrix_runtime_coverage(
            {"format": "wrong"},
            sgb,
            capture,
            manifest,
        )

    with pytest.raises(ValueError, match="SGBRuntime"):
        build_multimatrix_runtime_coverage(
            placement,
            {"format": "wrong"},
            capture,
            manifest,
        )
