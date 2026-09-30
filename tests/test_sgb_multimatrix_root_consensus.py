import pytest

from sgb_multimatrix import matrix_from_record, matrix_multiply
from sgb_multimatrix_root_consensus import (
    FORMAT,
    build_multimatrix_root_consensus,
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
    first = _object(1, "tracks/test/a.imb")
    second = _object(2, "tracks/test/b.imb")
    owner = {
        "format": "SHIFT.SGBObjectRuntime/1",
        "decoded": True,
        "kind": {"text": "LOD"},
        "matrix_number": -1,
        "matrix_records": records,
        "subobject_references": [
            {"index": 0, "decoded": True, "report": first},
            {"index": 1, "decoded": True, "report": second},
        ],
    }
    sgb = {
        "format": "SHIFT.SGBRuntime/1",
        "ready": True,
        "chunks": [{
            "tag": "SUMM",
            "records": [{
                "index": 7,
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
    world_a = matrix_multiply(
        matrix_from_record(records[1]),
        root,
    )
    world_b = matrix_multiply(
        matrix_from_record(records[2]),
        root,
    )
    return sgb, root, world_a, world_b


def _candidate(
    index,
    *,
    resource_path,
    sha,
    object_path,
    matrix_number,
):
    return {
        "scene_candidate_index": index,
        "placement_index": index,
        "wrapper": {
            "chunk": "SUMM",
            "source_record_index": 7,
        },
        "object_path": object_path,
        "resource_reference": resource_path,
        "normalized_resource_reference": resource_path,
        "transform_mode": "parent-multimatrix-slot",
        "matrix_number": matrix_number,
        "numeric_world_matrix_ready": False,
        "world_matrix": None,
    }


def _candidate_join(*, same_slot=False, include_b=True):
    rows = [{
        "runtime_resource_index": 0,
        "archive": "TRACK.bff",
        "resource_path": "tracks/test/a.imb",
        "resource_sha256": SHA_A,
        "exact_runtime_resource_ready": True,
        "scene_candidates": [
            _candidate(
                0,
                resource_path="tracks/test/a.imb",
                sha=SHA_A,
                object_path=[0],
                matrix_number=1,
            )
        ],
    }]
    if include_b:
        rows.append({
            "runtime_resource_index": 1,
            "archive": "TRACK.bff",
            "resource_path": "tracks/test/b.imb",
            "resource_sha256": SHA_B,
            "exact_runtime_resource_ready": True,
            "scene_candidates": [
                _candidate(
                    1,
                    resource_path="tracks/test/b.imb",
                    sha=SHA_B,
                    object_path=[1],
                    matrix_number=1 if same_slot else 2,
                )
            ],
        })
    return {
        "format": "SHIFT.SGBRuntimeObjectCandidateJoin/1",
        "ready": True,
        "resources": rows,
    }


def _constant_state(start, matrix, *, extra=None):
    vertex = {
        str(start + row): list(matrix[row * 4:(row + 1) * 4])
        for row in range(4)
    }
    if extra:
        for extra_start, extra_matrix in extra:
            for row in range(4):
                vertex[str(extra_start + row)] = list(
                    extra_matrix[row * 4:(row + 1) * 4]
                )
    return {"vertex": vertex, "pixel": {}}


def _capture(world_a, world_b, *, include_b=True, extras=None):
    resources = [{
        "resource_index": 0,
        "archive": "TRACK.bff",
        "resource_path": "tracks/test/a.imb",
        "resource_sha256": SHA_A,
        "attributed_texture_observations": [{
            "binding_index": 10,
            "frame": 1,
            "draw_index": 3,
            "status": "observed",
            "constant_state": _constant_state(
                20,
                world_a,
                extra=(extras or {}).get("a"),
            ),
        }],
    }]
    if include_b:
        resources.append({
            "resource_index": 1,
            "archive": "TRACK.bff",
            "resource_path": "tracks/test/b.imb",
            "resource_sha256": SHA_B,
            "attributed_texture_observations": [{
                "binding_index": 11,
                "frame": 1,
                "draw_index": 4,
                "status": "observed",
                "constant_state": _constant_state(
                    30,
                    world_b,
                    extra=(extras or {}).get("b"),
                ),
            }],
        })
    return {
        "format": "SHIFT.IMBRuntimeCapturePipeline/1",
        "pipeline_ready": True,
        "resource_results": resources,
    }


def test_two_independent_resources_recover_one_wrapper_root():
    sgb, root, world_a, world_b = _fixture()
    report = build_multimatrix_root_consensus(
        sgb,
        _candidate_join(),
        _capture(world_a, world_b),
    )

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["status"] == "ready"
    assert report["ready_consensus_count"] == 1
    consensus = report["consensus"][0]
    assert consensus["ready"] is True
    assert consensus["authorizes_current_wrapper_root"] is True
    assert consensus["wrapper"] == {
        "chunk": "SUMM",
        "source_record_index": 7,
    }
    assert consensus["owner_path"] == []
    assert (
        consensus["authorizes_current_multimatrix_owner_root"]
        is True
    )
    assert consensus["authorizes_current_wrapper_root"] is True
    assert consensus["root_world_matrix"] == pytest.approx(root)
    assert consensus["support_resource_count"] == 2
    assert consensus["distinct_cumulative_local_count"] == 2
    assert {
        row["matrix_number"]
        for row in consensus["witnesses"]
    } == {1, 2}
    assert report["boundary"]["register_semantics_assigned"] is False
    assert (
        report["boundary"]["scenegraph_update_history_recovered"]
        is False
    )
    assert report["boundary"]["authorizes_render_admission"] is False


def test_one_resource_cannot_authorize_wrapper_root():
    sgb, _, world_a, world_b = _fixture()
    report = build_multimatrix_root_consensus(
        sgb,
        _candidate_join(include_b=False),
        _capture(world_a, world_b, include_b=False),
    )

    assert report["ready"] is False
    assert report["status"] == "not-found"
    assert report["eligible_root_count"] == 0
    assert report["ready_consensus_count"] == 0


def test_same_local_chain_does_not_count_as_independent_shape():
    sgb, _, world_a, _ = _fixture()
    world_same_slot = world_a
    report = build_multimatrix_root_consensus(
        sgb,
        _candidate_join(same_slot=True),
        _capture(world_a, world_same_slot),
    )

    assert report["ready"] is False
    assert report["eligible_root_count"] == 0


def test_two_supported_root_values_keep_wrapper_ambiguous():
    sgb, root, world_a, world_b = _fixture()
    other_root = list(root)
    other_root[12] = 100.0
    records = (
        sgb["chunks"][0]["records"][0]["object_payload"]["report"][
            "matrix_records"
        ]
    )
    other_a = matrix_multiply(
        matrix_from_record(records[1]),
        other_root,
    )
    other_b = matrix_multiply(
        matrix_from_record(records[2]),
        other_root,
    )
    capture = _capture(
        world_a,
        world_b,
        extras={
            "a": [(40, other_a)],
            "b": [(50, other_b)],
        },
    )

    report = build_multimatrix_root_consensus(
        sgb,
        _candidate_join(),
        capture,
    )

    assert report["ready"] is False
    assert report["status"] == "ambiguous"
    assert report["eligible_root_count"] == 2
    assert report["ambiguous_consensus_count"] == 1
    row = report["consensus"][0]
    assert row["ready"] is False
    assert row["authorizes_current_wrapper_root"] is False
    assert len(row["candidate_roots"]) == 2


def test_wrong_formats_are_rejected():
    sgb, _, world_a, world_b = _fixture()
    with pytest.raises(ValueError, match="SGBRuntime"):
        build_multimatrix_root_consensus(
            {"format": "wrong"},
            _candidate_join(),
            _capture(world_a, world_b),
        )


def test_nested_multimatrix_owners_in_one_wrapper_do_not_cross_support():
    root = [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        10.0, 20.0, 30.0, 1.0,
    ]
    records_a = [
        _record(0, parent=-1, offset=(0.0, 0.0, 0.0)),
        _record(1, parent=0, offset=(1.0, 0.0, 0.0)),
    ]
    records_b = [
        _record(0, parent=-1, offset=(0.0, 0.0, 0.0)),
        _record(1, parent=0, offset=(0.0, 2.0, 0.0)),
    ]
    owner_a = {
        "format": "SHIFT.SGBObjectRuntime/1",
        "decoded": True,
        "kind": {"text": "LOD"},
        "matrix_number": -1,
        "matrix_records": records_a,
        "subobject_references": [{
            "index": 0,
            "decoded": True,
            "report": _object(1, "tracks/test/a.imb"),
        }],
    }
    owner_b = {
        "format": "SHIFT.SGBObjectRuntime/1",
        "decoded": True,
        "kind": {"text": "HIERARCHY"},
        "matrix_number": -1,
        "matrix_records": records_b,
        "subobject_references": [{
            "index": 0,
            "decoded": True,
            "report": _object(1, "tracks/test/b.imb"),
        }],
    }
    wrapper_root = {
        "format": "SHIFT.SGBObjectRuntime/1",
        "decoded": True,
        "kind": {"text": "HIERARCHY"},
        "matrix_number": -1,
        "matrix_records": [_record(
            0, parent=-1, offset=(0.0, 0.0, 0.0)
        )],
        "subobject_references": [
            {"index": 0, "decoded": True, "report": owner_a},
            {"index": 1, "decoded": True, "report": owner_b},
        ],
    }
    sgb = {
        "format": "SHIFT.SGBRuntime/1",
        "ready": True,
        "chunks": [{
            "tag": "SUMM",
            "records": [{
                "index": 7,
                "object_payload": {
                    "decoded": True,
                    "report": wrapper_root,
                },
            }],
        }],
    }
    candidate_join = {
        "format": "SHIFT.SGBRuntimeObjectCandidateJoin/1",
        "ready": True,
        "resources": [
            {
                "archive": "TRACK.bff",
                "resource_path": "tracks/test/a.imb",
                "resource_sha256": SHA_A,
                "scene_candidates": [{
                    **_candidate(
                        0,
                        resource_path="tracks/test/a.imb",
                        sha=SHA_A,
                        object_path=[0, 0],
                        matrix_number=1,
                    ),
                }],
            },
            {
                "archive": "TRACK.bff",
                "resource_path": "tracks/test/b.imb",
                "resource_sha256": SHA_B,
                "scene_candidates": [{
                    **_candidate(
                        1,
                        resource_path="tracks/test/b.imb",
                        sha=SHA_B,
                        object_path=[1, 0],
                        matrix_number=1,
                    ),
                }],
            },
        ],
    }
    world_a = matrix_multiply(
        matrix_from_record(records_a[1]),
        root,
    )
    world_b = matrix_multiply(
        matrix_from_record(records_b[1]),
        root,
    )
    capture = _capture(world_a, world_b)

    report = build_multimatrix_root_consensus(
        sgb,
        candidate_join,
        capture,
    )

    # The two resources support different MultiMatrix owners. They may not
    # combine merely because the wrapper and solved root are identical.
    assert report["ready"] is False
    assert report["eligible_root_count"] == 0
    assert report["ready_consensus_count"] == 0
