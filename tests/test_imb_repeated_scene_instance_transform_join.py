import pytest

from imb_repeated_scene_instance_transform_join import (
    FORMAT,
    OBJECT_JOIN_FORMAT,
    PIPELINE_FORMAT,
    RESOURCE_DRAW_FORMAT,
    build_repeated_scene_instance_transform_join,
)


def _sha(char):
    return char * 64


def _matrix(base):
    return [float(base + index) for index in range(16)]


def _transpose(values):
    return [
        values[row + column * 4]
        for row in range(4)
        for column in range(4)
    ]


def _constant_state(matrix, *, start=20):
    return {
        "vertex": {
            str(start + row): matrix[row * 4:(row + 1) * 4]
            for row in range(4)
        },
        "pixel": {},
    }


def _scene_candidate(index, matrix, *, ready=True):
    return {
        "scene_candidate_index": index,
        "placement_index": index,
        "placement_mode": "part-node",
        "placement_identity": {"partition": 4, "object": index},
        "placement_spatial": {"kind": "partition"},
        "wrapper": {"chunk": "NODE", "source_record_index": index},
        "object_path": [index],
        "wrapper_object_ordinal": 0,
        "resource_reference": "tracks/silverstone/tree.imb",
        "normalized_resource_reference": "tracks/silverstone/tree.imb",
        "handoff_ready": True,
        "transform_mode": "explicit-object-transform",
        "matrix_number": -1,
        "numeric_world_matrix_ready": ready,
        "world_matrix": matrix if ready else None,
    }


def _object_join(*candidates, ready=True, path="tracks/silverstone/tree.imb", sha=None):
    sha = sha or _sha("a")
    return {
        "format": OBJECT_JOIN_FORMAT,
        "ready": ready,
        "resources": [
            {
                "resource_path": path,
                "normalized_resource_path": path,
                "resource_sha256": sha,
                "exact_runtime_resource_ready": True,
                "scene_candidate_count": len(candidates),
                "scene_candidates": list(candidates),
            }
        ],
    }


def _resource_draw(*, status="exact-resource-draw-repeated-scene-instance", witnesses=None):
    if witnesses is None:
        witnesses = [
            {
                "resource_path": "tracks/silverstone/tree.imb",
                "resource_sha256": _sha("a"),
                "binding_index": 7,
                "frame": 4,
                "draw_index": 3,
                "event_index": 100,
            }
        ]
    row = {
        "event_index": 100,
        "frame": 4,
        "draw_evidence_sha256": _sha("d"),
        "candidate_set_sha256": _sha("c"),
        "status": status,
        "selected_candidate": {
            "content_group_sha256": _sha("1"),
            "imb_sha256": _sha("a"),
            "imb_paths": ["tracks/silverstone/tree.imb"],
            "exact_scene_reference_count": 2,
        },
        "runtime_witnesses": witnesses,
    }
    return {
        "format": RESOURCE_DRAW_FORMAT,
        "draws": [row],
        "summary": {
            "input_geometry_draw_count": 1,
            "exact_resource_draw_count": 1,
            "exact_scene_resource_draw_count": 0,
            "repeated_scene_instance_draw_count": 1,
            "remaining_scene_draw_ambiguity_count": 1,
        },
    }


def _pipeline(matrix, *, frame=4, draw_index=3, binding=7, path="tracks/silverstone/tree.imb", sha=None):
    sha = sha or _sha("a")
    return {
        "format": PIPELINE_FORMAT,
        "pipeline_ready": True,
        "resource_results": [
            {
                "resource_path": path,
                "resource_sha256": sha,
                "attributed_texture_observations": [
                    {
                        "binding_index": binding,
                        "frame": frame,
                        "draw_index": draw_index,
                        "status": "observed",
                        "constant_state": _constant_state(matrix),
                    }
                ],
            }
        ],
    }


def test_exact_float32_world_matrix_resolves_repeated_instance():
    first = _matrix(1)
    second = _matrix(101)
    report = build_repeated_scene_instance_transform_join(
        _resource_draw(),
        _object_join(
            _scene_candidate(0, first),
            _scene_candidate(1, second),
        ),
        _pipeline(second),
    )

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["status"] == "ready"
    assert report["summary"]["resolved_repeated_instance_draw_count"] == 1
    assert report["summary"]["remaining_scene_draw_ambiguity_count"] == 0
    row = report["draws"][0]
    assert row["status"] == "exact-repeated-scene-instance"
    assert row["selected_scene_candidate"]["placement_index"] == 1
    match = row["observation_results"][0]["matches"][0]
    assert match["status"] == "exact-single-scene-world-matrix"
    assert match["witnesses"][0]["start_register"] == 20
    assert "row-major" in match["witnesses"][0]["layouts"]


def test_transpose_layout_is_exact_observational_witness():
    first = _matrix(1)
    second = _matrix(201)
    report = build_repeated_scene_instance_transform_join(
        _resource_draw(),
        _object_join(
            _scene_candidate(0, first),
            _scene_candidate(1, second),
        ),
        _pipeline(_transpose(first)),
    )
    row = report["draws"][0]
    assert row["ready"] is True
    assert row["selected_scene_candidate"]["placement_index"] == 0
    witnesses = row["observation_results"][0]["matches"][0]["witnesses"]
    assert any("transpose" in witness["layouts"] for witness in witnesses)
    assert report["boundary"]["register_semantics_assigned"] is False


def test_equal_world_matrices_remain_ambiguous():
    shared = _matrix(1)
    report = build_repeated_scene_instance_transform_join(
        _resource_draw(),
        _object_join(
            _scene_candidate(0, shared),
            _scene_candidate(1, shared),
        ),
        _pipeline(shared),
    )
    row = report["draws"][0]
    assert row["ready"] is False
    assert row["status"] == "ambiguous-equal-or-multiple-world-matrix-matches"
    match = row["observation_results"][0]["matches"][0]
    assert len(match["matching_scene_candidate_identity_sha256s"]) == 2
    assert report["boundary"]["equal_world_matrices_select_instance"] is False


def test_incomplete_candidate_matrix_prevents_excluding_that_candidate():
    first = _matrix(1)
    report = build_repeated_scene_instance_transform_join(
        _resource_draw(),
        _object_join(
            _scene_candidate(0, first),
            _scene_candidate(1, None, ready=False),
        ),
        _pipeline(first),
    )
    row = report["draws"][0]
    assert row["ready"] is False
    assert row["status"] == "blocked-incomplete-scene-world-matrices"
    match = row["observation_results"][0]["matches"][0]
    assert match["status"] == "blocked-incomplete-scene-world-matrices"


def test_different_draw_index_constant_observation_does_not_authenticate_instance():
    first = _matrix(1)
    second = _matrix(101)
    report = build_repeated_scene_instance_transform_join(
        _resource_draw(),
        _object_join(
            _scene_candidate(0, first),
            _scene_candidate(1, second),
        ),
        _pipeline(first, draw_index=4),
    )
    row = report["draws"][0]
    assert row["ready"] is False
    assert row["status"] == "draw-local-transform-observation-missing"
    assert row["observation_results"][0]["capture_observation_count"] == 0


def test_all_same_draw_observations_must_agree_on_one_scene_candidate():
    first = _matrix(1)
    second = _matrix(101)
    witnesses = [
        {
            "resource_path": "tracks/silverstone/tree.imb",
            "resource_sha256": _sha("a"),
            "binding_index": 7,
            "frame": 4,
            "draw_index": 3,
            "event_index": 100,
        },
        {
            "resource_path": "tracks/silverstone/tree.imb",
            "resource_sha256": _sha("a"),
            "binding_index": 8,
            "frame": 4,
            "draw_index": 3,
            "event_index": 100,
        },
    ]
    pipeline = _pipeline(first, binding=7)
    pipeline["resource_results"][0]["attributed_texture_observations"].append({
        "binding_index": 8,
        "frame": 4,
        "draw_index": 3,
        "status": "observed",
        "constant_state": _constant_state(second),
    })
    report = build_repeated_scene_instance_transform_join(
        _resource_draw(witnesses=witnesses),
        _object_join(
            _scene_candidate(0, first),
            _scene_candidate(1, second),
        ),
        pipeline,
    )
    row = report["draws"][0]
    assert row["ready"] is False
    assert "same-draw-transform-observations-disagree:2" in row["blocking_reasons"]


def test_object_candidate_join_must_be_ready_for_complete_candidate_set():
    first = _matrix(1)
    second = _matrix(101)
    report = build_repeated_scene_instance_transform_join(
        _resource_draw(),
        _object_join(
            _scene_candidate(0, first),
            _scene_candidate(1, second),
            ready=False,
        ),
        _pipeline(first),
    )
    row = report["draws"][0]
    assert row["ready"] is False
    assert "runtime-object-candidate-join-not-ready" in row["blocking_reasons"]


def test_exact_resource_identity_is_required_for_scene_candidate_lookup():
    first = _matrix(1)
    second = _matrix(101)
    report = build_repeated_scene_instance_transform_join(
        _resource_draw(),
        _object_join(
            _scene_candidate(0, first),
            _scene_candidate(1, second),
            sha=_sha("b"),
        ),
        _pipeline(first),
    )
    row = report["draws"][0]
    assert row["ready"] is False
    assert "exact-runtime-resource-not-found-in-object-candidate-join" in row["blocking_reasons"]


def test_non_instance_upstream_ambiguity_is_preserved():
    resource_draw = _resource_draw(status="no-exact-runtime-resource-draw-witness")
    report = build_repeated_scene_instance_transform_join(
        resource_draw,
        _object_join(),
        _pipeline(_matrix(1)),
    )
    assert report["status"] == "upstream-non-instance-ambiguity"
    assert report["ready"] is False
    assert report["summary"]["repeated_instance_input_draw_count"] == 0
    assert report["summary"]["upstream_non_instance_ambiguity_count"] == 1
    assert report["summary"]["remaining_scene_draw_ambiguity_count"] == 1


def test_already_exact_unique_scene_resource_needs_no_instance_stage():
    resource_draw = _resource_draw(status="exact-scene-resource-draw")
    report = build_repeated_scene_instance_transform_join(
        resource_draw,
        _object_join(),
        _pipeline(_matrix(1)),
    )
    assert report["status"] == "not-needed"
    assert report["ready"] is True
    assert report["summary"]["already_exact_scene_resource_draw_count"] == 1
    assert report["summary"]["remaining_scene_draw_ambiguity_count"] == 0


def test_formats_fail_closed():
    good_resource = _resource_draw()
    good_object = _object_join(
        _scene_candidate(0, _matrix(1)),
        _scene_candidate(1, _matrix(101)),
    )
    good_pipeline = _pipeline(_matrix(1))
    with pytest.raises(ValueError, match="resource draw"):
        build_repeated_scene_instance_transform_join(
            {"format": "wrong"}, good_object, good_pipeline
        )
    with pytest.raises(ValueError, match="object candidate join"):
        build_repeated_scene_instance_transform_join(
            good_resource, {"format": "wrong"}, good_pipeline
        )
    with pytest.raises(ValueError, match="capture pipeline"):
        build_repeated_scene_instance_transform_join(
            good_resource, good_object, {"format": "wrong"}
        )
