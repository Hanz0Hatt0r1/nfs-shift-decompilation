import pytest

from imb_static_scene_reference_candidate_join import (
    AMBIGUITY_FORMAT,
    FORMAT,
    _walk_object_references,
    build_static_scene_reference_candidate_join,
)


def _sha(char):
    return char * 64


def _object(path, *, matrix=-1):
    return {
        "decoded": True,
        "kind": {"text": "OBJECT"},
        "resource_filename": {"text": path},
        "matrix_number": matrix,
    }


def _lod(children, distances):
    return {
        "decoded": True,
        "kind": {"text": "LOD"},
        "hash_sha256": _sha("9"),
        "source_string": {"text": "tree_lod"},
        "subobjects": len(children),
        "lod_distances_serialized": distances,
        "lod_distance_runtime_rule": {
            "zero_value_fallback": "FUN_006993f0(name,index) or (1<<index)*100, then global scale"
        },
        "subobject_references": [
            {"index": index, "decoded": True, "report": child}
            for index, child in enumerate(children)
        ],
    }


def _ref(path, sha, *, lod_parent=None, child=0, distance=100.0):
    ancestry = []
    if lod_parent:
        ancestry = [{
            "lod_parent_identity_sha256": _sha(lod_parent),
            "lod_parent_object_path": [],
            "child_index": child,
            "serialized_distance": distance,
            "distance_status": "serialized-nonzero",
            "runtime_fallback_rule": "fallback",
        }]
    return {
        "reference_kind": "object-resource",
        "resource_path": path,
        "normalized_resource_path": path.lower(),
        "target_resource_sha256": _sha(sha),
        "target_identity_ready": True,
        "source_input": "Silverstone.zip",
        "archive": "Silverstone.bff",
        "sgb_path": "tracks/silverstone/scene.sgb",
        "chunk": "NODE",
        "source_record_index": 2,
        "object_path": [child],
        "lod_ancestry": ancestry,
    }


def _candidate(label, path):
    return {
        "content_group_sha256": _sha(label),
        "imb_sha256": _sha(label),
        "imb_paths": [path],
        "archives": ["Silverstone.bff"],
    }


def _ambiguity(candidates, *, cls="metadata-equivalent-geometry-alternatives"):
    return {
        "format": AMBIGUITY_FORMAT,
        "ambiguous_draws": [{
            "event_index": 123,
            "frame": 7,
            "draw_evidence_sha256": _sha("d"),
            "candidate_set_sha256": _sha("e"),
            "ambiguity_class": cls,
            "candidates": candidates,
        }],
    }


def _scene_index(refs):
    return {
        "wanted_path_count": 2,
        "decoded_sgb_count": 1,
        "ready_sgb_count": 1,
        "blocked_sgb_count": 0,
        "imb_path_identity_count": 2,
        "references": refs,
    }


def test_recursive_lod_walk_preserves_slot_and_distance_provenance():
    rows = _walk_object_references(_lod([
        _object("tracks/test/tree_loda.imb"),
        _object("tracks/test/tree_lodb.imb"),
    ], [80.0, 0.0]))

    assert [row["resource_path"] for row in rows] == [
        "tracks/test/tree_loda.imb",
        "tracks/test/tree_lodb.imb",
    ]
    first = rows[0]["lod_ancestry"][0]
    second = rows[1]["lod_ancestry"][0]
    assert first["child_index"] == 0
    assert first["serialized_distance"] == 80.0
    assert first["distance_status"] == "serialized-nonzero"
    assert second["child_index"] == 1
    assert second["serialized_distance"] == 0.0
    assert second["distance_status"] == "zero-uses-source-backed-runtime-fallback"
    assert first["lod_parent_identity_sha256"] == second["lod_parent_identity_sha256"]


def test_exact_lod_sibling_refs_form_source_backed_lod_family():
    candidates = [
        _candidate("a", "tracks/test/tree_loda.imb"),
        _candidate("b", "tracks/test/tree_lodb.imb"),
    ]
    refs = [
        _ref("tracks/test/tree_loda.imb", "a", lod_parent="1", child=0, distance=80.0),
        _ref("tracks/test/tree_lodb.imb", "b", lod_parent="1", child=1, distance=160.0),
    ]
    result = build_static_scene_reference_candidate_join(
        _ambiguity(candidates, cls="metadata-equivalent-lod-siblings"),
        _scene_index(refs),
    )
    assert result["format"] == FORMAT
    row = result["draws"][0]
    assert row["resolution_status"] == "source-backed-lod-family-needs-selection-witness"
    assert row["selected_content_group_sha256"] is None
    assert row["exact_scene_referenced_candidate_count"] == 2
    assert row["lod_groups"][0]["candidate_count"] == 2
    assert [slot["child_index"] for slot in row["lod_groups"][0]["slots"]] == [0, 1]
    assert result["summary"]["source_backed_lod_family_draw_count"] == 1
    assert result["summary"]["draw_attribution_resolved_count"] == 0


def test_single_exact_static_scene_reference_does_not_select_runtime_draw():
    candidates = [
        _candidate("a", "tracks/test/a.imb"),
        _candidate("b", "tracks/test/b.imb"),
    ]
    result = build_static_scene_reference_candidate_join(
        _ambiguity(candidates),
        _scene_index([_ref("tracks/test/a.imb", "a")]),
    )
    row = result["draws"][0]
    assert row["resolution_status"] == "single-static-scene-referenced-candidate-unproven-draw"
    assert row["selected_content_group_sha256"] is None
    assert result["boundary"]["single_static_scene_reference_is_draw_attribution"] is False
    assert result["summary"]["single_scene_referenced_candidate_draw_count"] == 1


def test_path_match_with_wrong_payload_sha_does_not_reference_candidate():
    candidate = _candidate("a", "tracks/test/a.imb")
    result = build_static_scene_reference_candidate_join(
        _ambiguity([candidate]),
        _scene_index([_ref("tracks/test/a.imb", "b")]),
    )
    row = result["draws"][0]
    assert row["resolution_status"] == "no-exact-static-scene-reference"
    assert row["candidate_results"][0]["exact_scene_reference_count"] == 0


def test_unresolved_duplicate_path_identity_is_not_positive_reference():
    candidate = _candidate("a", "tracks/test/a.imb")
    ref = _ref("tracks/test/a.imb", "a")
    ref["target_resource_sha256"] = None
    ref["target_identity_ready"] = False
    result = build_static_scene_reference_candidate_join(
        _ambiguity([candidate]),
        _scene_index([ref]),
    )
    candidate_result = result["draws"][0]["candidate_results"][0]
    assert candidate_result["exact_scene_referenced"] is False
    assert candidate_result["unresolved_reference_paths"] == ["tracks/test/a.imb"]


def test_unreferenced_candidate_is_not_treated_as_contradiction():
    candidates = [
        _candidate("a", "tracks/test/a.imb"),
        _candidate("b", "tracks/test/b.imb"),
    ]
    result = build_static_scene_reference_candidate_join(
        _ambiguity(candidates),
        _scene_index([_ref("tracks/test/a.imb", "a")]),
    )
    assert result["boundary"]["unreferenced_candidate_is_contradicted"] is False
    assert result["summary"]["remaining_geometry_ambiguous_draw_count"] == 1


def test_non_geometry_ambiguity_is_ignored():
    result = build_static_scene_reference_candidate_join(
        _ambiguity([_candidate("a", "tracks/test/a.imb")], cls="material-distinct-candidates"),
        _scene_index([]),
    )
    assert result["status"] == "no-geometry-ambiguity"
    assert result["draws"] == []


def test_format_fails_closed():
    with pytest.raises(ValueError, match="ambiguity report"):
        build_static_scene_reference_candidate_join(
            {"format": "wrong"},
            _scene_index([]),
        )
