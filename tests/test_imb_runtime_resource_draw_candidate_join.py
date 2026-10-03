import pytest

from imb_runtime_resource_draw_candidate_join import (
    FORMAT,
    PIPELINE_FORMAT,
    SCENE_FORMAT,
    build_runtime_resource_draw_candidate_join,
)


def _sha(char):
    return char * 64


def _candidate(char, path, *, refs=1):
    return {
        "content_group_sha256": _sha(char),
        "imb_sha256": _sha(char.upper()),
        "imb_paths": [path],
        "exact_scene_referenced": refs > 0,
        "exact_scene_reference_count": refs,
        "lod_parent_identity_sha256s": [_sha("e")] if refs else [],
        "scene_references": [
            {
                "sgb_path": "tracks/silverstone/scene.sgb",
                "chunk": "NODE",
                "source_record_index": index,
                "object_path": [index],
                "resource_path": path,
                "target_resource_sha256": _sha(char.upper()),
            }
            for index in range(refs)
        ],
    }


def _scene(*candidates, event=100):
    return {
        "format": SCENE_FORMAT,
        "draws": [
            {
                "event_index": event,
                "frame": 4,
                "draw_evidence_sha256": _sha("d"),
                "candidate_set_sha256": _sha("c"),
                "ambiguity_class": "metadata-equivalent-lod-siblings",
                "candidate_results": list(candidates),
            }
        ],
    }


def _resource(
    char,
    path,
    *,
    event=100,
    binding=7,
    attributed=True,
    score=100,
    selected_key=None,
):
    key = selected_key or ["permutation", _sha("f")]
    selected = {
        "score": score,
        "variant_key": key,
        "permutation_identity_sha256": _sha("f"),
    }
    return {
        "resource_index": binding,
        "archive": "Silverstone.bff",
        "resource_path": path,
        "resource_sha256": _sha(char.upper()),
        "runtime_evidence": {
            "same_instance_gate": {
                "status": "ready",
                "ready": True,
            }
        },
        "variant_match": {
            "candidate_binding_results": [
                {
                    "binding_index": binding,
                    "primitive_index": 2,
                    "imb_path": path,
                    "imb_sha256": _sha(char.upper()),
                    "draw_range": {
                        "first_index": 12,
                        "index_count": 6,
                        "primitive_count": 2,
                    },
                    "material_reference": "road.bmt",
                    "shader_family": "road",
                    "attributed": attributed,
                    "selected_variant": selected if attributed else None,
                    "matches": [
                        {
                            "frame": 4,
                            "draw_index": 3,
                            "draw": {
                                "event_index": event,
                                "start_index": 12,
                                "primitive_count": 2,
                                "base_vertex_index": 0,
                            },
                            "resource_identity_status": "exact",
                            "gate_descriptor_match_count": 3,
                            "runtime_hashes": {
                                "permutation": _sha("f")
                            },
                            "variant_matches": [
                                {
                                    "score": score,
                                    "variant_key": key,
                                    "evidence": ["permutation_identity_sha256"],
                                }
                            ],
                        }
                    ],
                }
            ]
        },
    }


def _pipeline(*resources):
    return {
        "format": PIPELINE_FORMAT,
        "pipeline_ready": True,
        "attribution_complete": True,
        "resource_results": list(resources),
    }


def test_exact_same_event_path_sha_and_unique_scene_reference_closes_draw():
    first = _candidate("a", "tracks/silverstone/a_loda.imb", refs=1)
    second = _candidate("b", "tracks/silverstone/a_lodb.imb", refs=1)
    report = build_runtime_resource_draw_candidate_join(
        _scene(first, second),
        _pipeline(_resource("a", "TRACKS\\SILVERSTONE\\A_LODA.IMB")),
    )

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["summary"]["exact_resource_draw_count"] == 1
    assert report["summary"]["exact_scene_resource_draw_count"] == 1
    row = report["draws"][0]
    assert row["status"] == "exact-scene-resource-draw"
    assert row["selected_content_group_sha256"] == _sha("a")
    assert row["runtime_witnesses"][0]["event_index"] == 100
    assert row["runtime_witnesses"][0]["same_instance_gate_ready"] is True


def test_exact_resource_draw_keeps_repeated_scene_instance_open():
    candidate = _candidate("a", "tracks/silverstone/tree.imb", refs=2)
    report = build_runtime_resource_draw_candidate_join(
        _scene(candidate),
        _pipeline(_resource("a", "tracks/silverstone/tree.imb")),
    )

    assert report["ready"] is False
    assert report["status"] == "partial"
    assert report["summary"]["exact_resource_draw_count"] == 1
    assert report["summary"]["exact_scene_resource_draw_count"] == 0
    assert report["summary"]["repeated_scene_instance_draw_count"] == 1
    row = report["draws"][0]
    assert row["status"] == "exact-resource-draw-repeated-scene-instance"
    assert row["selected_content_group_sha256"] == _sha("a")
    assert "transform-or-spatial" in row["blocking_reasons"][0]


def test_different_event_does_not_authenticate_phase623_draw():
    candidate = _candidate("a", "tracks/silverstone/a.imb", refs=1)
    report = build_runtime_resource_draw_candidate_join(
        _scene(candidate, event=100),
        _pipeline(_resource("a", "tracks/silverstone/a.imb", event=101)),
    )
    row = report["draws"][0]
    assert row["status"] == "no-exact-runtime-resource-draw-witness"
    assert row["selected_content_group_sha256"] is None
    assert report["summary"]["exact_resource_draw_count"] == 0


def test_weak_or_unattributed_variant_is_not_a_runtime_witness():
    candidate = _candidate("a", "tracks/silverstone/a.imb", refs=1)
    weak = _resource("a", "tracks/silverstone/a.imb", score=40)
    report = build_runtime_resource_draw_candidate_join(
        _scene(candidate),
        _pipeline(weak),
    )
    assert report["draws"][0]["status"] == "no-exact-runtime-resource-draw-witness"

    not_attributed = _resource(
        "a", "tracks/silverstone/a.imb", attributed=False
    )
    report = build_runtime_resource_draw_candidate_join(
        _scene(candidate),
        _pipeline(not_attributed),
    )
    assert report["draws"][0]["status"] == "no-exact-runtime-resource-draw-witness"


def test_same_event_runtime_resource_outside_candidate_set_fails_closed():
    candidate = _candidate("a", "tracks/silverstone/a.imb", refs=1)
    report = build_runtime_resource_draw_candidate_join(
        _scene(candidate),
        _pipeline(_resource("b", "tracks/silverstone/b.imb")),
    )
    row = report["draws"][0]
    assert row["status"] == "runtime-resource-not-in-phase623-candidate-set"
    assert row["selected_content_group_sha256"] is None
    assert report["summary"]["conflict_draw_count"] == 1


def test_two_exact_resources_on_same_event_do_not_choose_by_order():
    first = _candidate("a", "tracks/silverstone/a.imb", refs=1)
    second = _candidate("b", "tracks/silverstone/b.imb", refs=1)
    report = build_runtime_resource_draw_candidate_join(
        _scene(first, second),
        _pipeline(
            _resource("a", "tracks/silverstone/a.imb", binding=1),
            _resource("b", "tracks/silverstone/b.imb", binding=2),
        ),
    )
    row = report["draws"][0]
    assert row["status"] == "multiple-exact-runtime-resource-candidates"
    assert row["selected_content_group_sha256"] is None
    assert sorted(row["runtime_candidate_content_group_sha256s"]) == [
        _sha("a"),
        _sha("b"),
    ]


def test_runtime_identity_requires_path_and_sha_match_inside_binding_result():
    candidate = _candidate("a", "tracks/silverstone/a.imb", refs=1)
    resource = _resource("a", "tracks/silverstone/a.imb")
    resource["variant_match"]["candidate_binding_results"][0]["imb_sha256"] = _sha("b")
    report = build_runtime_resource_draw_candidate_join(
        _scene(candidate),
        _pipeline(resource),
    )
    assert report["draws"][0]["status"] == "no-exact-runtime-resource-draw-witness"


def test_exact_runtime_resource_without_phase623_scene_reference_stays_open():
    candidate = _candidate("a", "tracks/silverstone/a.imb", refs=0)
    report = build_runtime_resource_draw_candidate_join(
        _scene(candidate),
        _pipeline(_resource("a", "tracks/silverstone/a.imb")),
    )
    row = report["draws"][0]
    assert row["status"] == "exact-runtime-resource-not-exact-scene-referenced"
    assert report["summary"]["exact_resource_draw_count"] == 1
    assert report["summary"]["exact_scene_resource_draw_count"] == 0


def test_empty_geometry_set_is_not_needed():
    report = build_runtime_resource_draw_candidate_join(
        {"format": SCENE_FORMAT, "draws": []},
        _pipeline(),
    )
    assert report["status"] == "not-needed"
    assert report["ready"] is False
    assert report["summary"]["input_geometry_draw_count"] == 0


def test_formats_fail_closed():
    with pytest.raises(ValueError, match="scene geometry"):
        build_runtime_resource_draw_candidate_join(
            {"format": "wrong"},
            _pipeline(),
        )
    with pytest.raises(ValueError, match="capture pipeline"):
        build_runtime_resource_draw_candidate_join(
            {"format": SCENE_FORMAT, "draws": []},
            {"format": "wrong"},
        )
