import pytest

from sgb_runtime_object_candidate_join import (
    FORMAT,
    build_runtime_object_candidate_join,
)


SHA_A = "a" * 64
SHA_B = "b" * 64


def _placement(*indices):
    return {
        "format": "SHIFT.SGBScenePlacement/1",
        "ready": True,
        "placements": [
            {
                "placement_index": ordinal,
                "mode": "flat-summ",
                "identity": {
                    "runtime_index": index,
                    "summ_source_order": index,
                },
                "object": {
                    "source_record_index": index,
                    "resource": "tracks/test/object.imb",
                },
                "spatial": {
                    "scope": "flat-leaf",
                    "spatial_bounds": {
                        "min_xyz": [0.0, 0.0, 0.0],
                        "max_xyz": [1.0, 1.0, 1.0],
                    },
                },
                "ready": True,
            }
            for ordinal, index in enumerate(indices)
        ],
    }


def _handoffs(*indices):
    return {
        "format": "SHIFT.SGBObjectRenderHandoffSet/1",
        "ready": True,
        "objects": [
            {
                "wrapper": {
                    "chunk": "SUMM",
                    "source_record_index": index,
                },
                "object_path": [index],
                "handoff": {
                    "ready": True,
                    "resource": {
                        "reference": "tracks/test/object.imb",
                    },
                    "transform": {
                        "mode": "parent-multimatrix-slot",
                        "matrix_number": 1,
                        "world_matrix_ready": False,
                        "world_matrix": None,
                    },
                },
            }
            for index in indices
        ],
    }


def _capture(*, sha=SHA_A, gate_ready=True):
    return {
        "format": "SHIFT.IMBRuntimeCapturePipeline/1",
        "pipeline_ready": True,
        "resource_results": [
            {
                "resource_index": 3,
                "archive": "TRACK.bff",
                "resource_path": "tracks/test/object.imb",
                "resource_sha256": sha,
                "candidate_binding_indices": [17, 18],
                "runtime_evidence": {
                    "same_instance_gate": {
                        "ready": gate_ready,
                    },
                },
            }
        ],
    }


def _manifest(*, sha=SHA_A):
    return [
        {
            "archive": "TRACK.bff",
            "path": "tracks/test/object.imb",
            "sha256": sha,
            "raw": "raw/object.imb",
        }
    ]


def test_unique_logical_scene_candidate_is_narrowing_not_admission():
    report = build_runtime_object_candidate_join(
        _placement(0),
        _handoffs(0),
        _capture(),
        _manifest(),
    )

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["status"] == "unique-candidates"
    assert report["identity_complete"] is True
    assert report["runtime_resource_count"] == 1
    assert report["matched_runtime_resource_count"] == 1
    assert report["unique_candidate_resource_count"] == 1

    row = report["resources"][0]
    assert row["exact_runtime_resource_ready"] is True
    assert row["ir_manifest_identity_ready"] is True
    assert row["scene_candidate_count"] == 1
    assert row["unique_logical_scene_candidate"] is True
    candidate = row["scene_candidates"][0]
    assert candidate["placement_index"] == 0
    assert candidate["wrapper"] == {
        "chunk": "SUMM",
        "source_record_index": 0,
    }
    assert candidate["object_path"] == [0]
    assert candidate["matrix_number"] == 1
    assert candidate["numeric_world_matrix_ready"] is False

    boundary = report["boundary"]
    assert boundary["uses_render_binding_admission_index"] is False
    assert boundary["unique_logical_candidate_is_render_admission"] is False
    assert boundary["authorizes_multimatrix_root_solve"] is False
    assert boundary["authorizes_world_matrix"] is False
    assert boundary["authorizes_render_admission"] is False


def test_repeated_scene_resource_remains_ambiguous():
    report = build_runtime_object_candidate_join(
        _placement(0, 1),
        _handoffs(0, 1),
        _capture(),
        _manifest(),
    )

    assert report["ready"] is True
    assert report["status"] == "ambiguous"
    assert report["identity_complete"] is False
    assert report["scene_candidate_count"] == 2
    assert report["unique_candidate_resource_count"] == 0
    row = report["resources"][0]
    assert row["scene_candidate_count"] == 2
    assert row["unique_logical_scene_candidate"] is False
    assert [c["object_path"] for c in row["scene_candidates"]] == [
        [0], [1],
    ]


def test_manifest_sha_mismatch_fails_closed():
    report = build_runtime_object_candidate_join(
        _placement(0),
        _handoffs(0),
        _capture(sha=SHA_A),
        _manifest(sha=SHA_B),
    )

    assert report["ready"] is False
    assert report["status"] == "not-found"
    row = report["resources"][0]
    assert row["ir_manifest_identity_ready"] is False
    assert row["exact_runtime_resource_ready"] is False
    assert any(
        "runtime-resource-ir-identity-not-found" in reason
        for reason in report["blocking_reasons"]
    )


def test_runtime_same_instance_gate_is_required():
    report = build_runtime_object_candidate_join(
        _placement(0),
        _handoffs(0),
        _capture(gate_ready=False),
        _manifest(),
    )

    assert report["ready"] is False
    assert report["resources"][0]["exact_runtime_resource_ready"] is False
    assert any(
        "runtime-same-instance-gate-not-ready" in reason
        for reason in report["blocking_reasons"]
    )


def test_wrong_input_formats_are_rejected():
    with pytest.raises(ValueError, match="SGBScenePlacement"):
        build_runtime_object_candidate_join(
            {"format": "wrong"},
            _handoffs(0),
            _capture(),
            _manifest(),
        )
