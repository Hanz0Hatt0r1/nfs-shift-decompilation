from sgb_multimatrix import matrix_from_record, matrix_multiply
from sgb_runtime_transform_recovery import (
    FORMAT,
    build_sgb_runtime_transform_recovery_pipeline,
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
                "report": _object(1, "tracks/test/a.imb"),
            },
            {
                "index": 1,
                "decoded": True,
                "report": _object(2, "tracks/test/b.imb"),
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
                "offset": 100,
                "name": {"text": "wrapper"},
                "resource": {"text": ""},
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
            "identity": {
                "runtime_index": 0,
                "summ_source_order": 7,
            },
            "object": {
                "source_record_index": 7,
                "resource": "tracks/test/a.imb",
            },
            "spatial": {
                "scope": "flat-leaf",
                "spatial_bounds": {
                    "min_xyz": [-10.0, -10.0, -10.0],
                    "max_xyz": [10.0, 10.0, 10.0],
                },
            },
            "render_binding_handoff": {
                "spatial_culling_ready": True,
            },
            "ready": True,
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
    return sgb, placement, root, world_a, world_b


def _constant_state(start, matrix):
    return {
        "vertex": {
            str(start + row): list(
                matrix[row * 4:(row + 1) * 4]
            )
            for row in range(4)
        },
        "pixel": {},
    }


def _resource(index, path, sha, start, world):
    return {
        "resource_index": index,
        "archive": "TRACK.bff",
        "resource_path": path,
        "resource_sha256": sha,
        "candidate_binding_indices": [index],
        "runtime_evidence": {
            "same_instance_gate": {
                "ready": True,
                "status": "ready",
                "blocking_reasons": [],
            },
        },
        "attributed_texture_observations": [{
            "binding_index": index,
            "frame": 2,
            "draw_index": index + 3,
            "status": "observed",
            "constant_state": _constant_state(start, world),
            "active_texture_bindings": [],
        }],
    }


def _capture(world_a, world_b, *, include_b=True):
    resources = [
        _resource(
            0,
            "tracks/test/a.imb",
            SHA_A,
            20,
            world_a,
        ),
    ]
    if include_b:
        resources.append(
            _resource(
                1,
                "tracks/test/b.imb",
                SHA_B,
                30,
                world_b,
            )
        )
    return {
        "format": "SHIFT.IMBRuntimeCapturePipeline/1",
        "pipeline_ready": True,
        "status": "ready",
        "blocking_reasons": [],
        "resource_results": resources,
    }


def _manifest(*, bad_b_sha=False):
    return [
        {
            "archive": "TRACK.bff",
            "path": "tracks/test/a.imb",
            "sha256": SHA_A,
            "raw": "raw/a.imb",
        },
        {
            "archive": "TRACK.bff",
            "path": "tracks/test/b.imb",
            "sha256": ("c" * 64 if bad_b_sha else SHA_B),
            "raw": "raw/b.imb",
        },
    ]


def test_pipeline_recovers_matrixnumber_rows_and_scene_admission():
    sgb, placement, root, world_a, world_b = _fixture()
    report = build_sgb_runtime_transform_recovery_pipeline(
        sgb,
        placement,
        _capture(world_a, world_b),
        _manifest(),
    )

    assert report["format"] == FORMAT
    assert report["pipeline_ready"] is True
    assert report["status"] == "recovered"
    assert report["consensus_applied"] is True
    assert report["transform_recovery_complete"] is True
    assert report["scene_admission_ready"] is True

    summary = report["summary"]
    assert summary["parent_multimatrix_slot_count"] == 2
    assert summary["parent_multimatrix_numeric_ready_before"] == 0
    assert summary["parent_multimatrix_numeric_ready_after"] == 2
    assert summary["recovered_matrixnumber_object_count"] == 2
    assert summary["remaining_blocked_matrixnumber_object_count"] == 0
    assert summary["root_consensus_ready_count"] == 1
    assert summary["admitted_binding_count_before"] == 0
    assert summary["admitted_binding_count_after"] == 2
    assert summary["admitted_binding_delta"] == 2

    consensus = report["root_consensus"]["consensus"][0]
    assert consensus["owner_path"] == []
    assert consensus["root_world_matrix"] == root

    recovered = report["comparison"]["recovered_objects"]
    assert len(recovered) == 2
    assert all(
        row["runtime_root_consensus"]["owner_path"] == []
        for row in recovered
    )
    assert report["boundary"]["new_transform_math"] is False
    assert report["boundary"]["register_semantics_assigned"] is False
    assert (
        report["boundary"]["scenegraph_update_history_recovered"]
        is False
    )


def test_pipeline_reports_no_consensus_without_two_resources():
    sgb, placement, _, world_a, world_b = _fixture()
    report = build_sgb_runtime_transform_recovery_pipeline(
        sgb,
        placement,
        _capture(world_a, world_b, include_b=False),
        _manifest(),
    )

    assert report["pipeline_ready"] is True
    assert report["status"] == "no-consensus"
    assert report["consensus_applied"] is False
    assert report["scene_admission_ready"] is False
    summary = report["summary"]
    assert summary["recovered_matrixnumber_object_count"] == 0
    assert summary["parent_multimatrix_numeric_ready_before"] == 0
    assert summary["parent_multimatrix_numeric_ready_after"] == 0
    assert summary["admitted_binding_delta"] == 0


def test_pipeline_fails_closed_when_exact_ir_identity_is_missing():
    sgb, placement, _, world_a, world_b = _fixture()
    report = build_sgb_runtime_transform_recovery_pipeline(
        sgb,
        placement,
        _capture(world_a, world_b),
        _manifest(bad_b_sha=True),
    )

    assert report["pipeline_ready"] is False
    assert report["status"] == "blocked"
    assert report["consensus_applied"] is False
    assert any(
        "runtime-resource-ir-identity-not-found" in reason
        for reason in report["blocking_reasons"]
    )
    assert report["summary"]["admitted_binding_delta"] == 0


def test_pipeline_rejects_wrong_sgb_format():
    _, placement, _, world_a, world_b = _fixture()
    try:
        build_sgb_runtime_transform_recovery_pipeline(
            {"format": "wrong"},
            placement,
            _capture(world_a, world_b),
            _manifest(),
        )
    except ValueError as error:
        assert "SGBRuntime/1" in str(error)
    else:
        raise AssertionError("wrong SGB format was accepted")
