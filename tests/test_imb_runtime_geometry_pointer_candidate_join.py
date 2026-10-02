from imb_runtime_geometry_pointer_candidate_join import (
    FORMAT,
    build_runtime_geometry_pointer_candidate_join,
)


def _sha(char):
    return char * 64


def _group(content, imb, *, primitive=0, triangles=12, stride=36, bmt="b"):
    return {
        "content_group_sha256": _sha(content),
        "imb_sha256": _sha(imb),
        "imb_paths": [f"tracks/{imb}.imb"],
        "archives": ["Silverstone.bff"],
        "bmt_sha256": _sha(bmt),
        "shader_family": "foliageinstanced",
        "primitive_index": primitive,
        "draw_range": {
            "first_index": 0,
            "index_count": triangles * 3,
            "primitive_count": triangles,
        },
        "static_vertex_stride": stride,
    }


def _material_row(resource, groups):
    return {
        "resource_shape_sha256": _sha(resource),
        "candidate_content_status": (
            "single-content-candidate" if len(groups) == 1
            else "ambiguous-content-candidates"
        ),
        "candidate_content_groups": groups,
        "draw_count": 10,
        "families": ["foliageinstanced"],
    }


def _geometry_observation(identity_sha, draws=10):
    return {
        "identity_sha256": _sha(identity_sha),
        "identity": {
            "device_ptr": "0x1",
            "stream0_vertex_buffer_ptr": "0x40",
            "stream0_vertex_buffer_creation_event_index": 100,
            "index_buffer_ptr": "0x50",
            "index_buffer_creation_event_index": 101,
            "draw_range": {
                "primitive_type": 4,
                "base_vertex_index": 0,
                "start_index": 0,
                "primitive_count": 12,
            },
            "creation_identity_complete": True,
        },
        "draw_count": draws,
        "draw_count_in_resource_shape": draws,
        "first_frame": 10,
        "last_frame": 20,
    }


def _pointer_row(resource, identity_sha, draws=10):
    return {
        "resource_shape_sha256": _sha(resource),
        "geometry_pointer_observations": [
            _geometry_observation(identity_sha, draws=draws)
        ],
    }


def _pointer_report(rows):
    return {
        "format": "SHIFT.D3D9TargetPointerObservations/1",
        "catalog_alignment": {"status": "exact"},
        "resource_shapes": rows,
    }


def _material_report(rows):
    return {
        "format": "SHIFT.IMBRuntimeMaterialDescriptorCandidateJoin/1",
        "resource_shapes": rows,
    }


def test_geometry_pointer_seed_resolves_when_textures_may_differ():
    group_a = _group("a", "1")
    group_b = _group("c", "2")
    material = _material_report([
        _material_row("3", [group_a]),
        _material_row("4", [group_a, group_b]),
    ])
    pointers = _pointer_report([
        _pointer_row("3", "5", draws=4),
        _pointer_row("4", "5", draws=6),
    ])

    report = build_runtime_geometry_pointer_candidate_join(pointers, material)

    assert report["format"] == FORMAT
    summary = report["summary"]
    assert summary["geometry_seed_identity_count"] == 1
    assert summary["newly_resolved_geometry_identity_count"] == 1
    assert summary["newly_resolved_geometry_identity_draw_count"] == 6
    assert summary["geometry_seed_conflict_identity_count"] == 0

    ambiguous = next(
        row for row in report["resource_shapes"]
        if row["resource_shape_sha256"] == _sha("4")
    )
    identity = ambiguous["geometry_pointer_identities"][0]
    assert identity["geometry_candidate_gate_status"] == "reduced-by-same-geometry-seed"
    assert identity["candidate_content_group_sha256s"] == [_sha("a")]


def test_conflicting_geometry_seeds_fail_open():
    group_a = _group("a", "1")
    group_b = _group("c", "2")
    material = _material_report([
        _material_row("3", [group_a]),
        _material_row("4", [group_b]),
        _material_row("5", [group_a, group_b]),
    ])
    pointers = _pointer_report([
        _pointer_row("3", "6", draws=2),
        _pointer_row("4", "6", draws=3),
        _pointer_row("5", "6", draws=5),
    ])

    report = build_runtime_geometry_pointer_candidate_join(pointers, material)
    ambiguous = next(
        row for row in report["resource_shapes"]
        if row["resource_shape_sha256"] == _sha("5")
    )
    identity = ambiguous["geometry_pointer_identities"][0]

    assert identity["geometry_seed_status"] == "conflicting-geometry-seeds"
    assert identity["geometry_candidate_gate_status"] == "conflicting-geometry-seeds"
    assert identity["candidate_content_group_count"] == 2
    assert report["summary"]["newly_resolved_geometry_identity_count"] == 0
    assert report["summary"]["geometry_seed_conflict_identity_count"] == 1


def test_geometry_seed_outside_static_candidates_fails_open():
    group_a = _group("a", "1")
    group_b = _group("c", "2")
    group_c = _group("d", "7")
    material = _material_report([
        _material_row("3", [group_a]),
        _material_row("4", [group_b, group_c]),
    ])
    pointers = _pointer_report([
        _pointer_row("3", "8", draws=4),
        _pointer_row("4", "8", draws=6),
    ])

    report = build_runtime_geometry_pointer_candidate_join(pointers, material)
    ambiguous = next(
        row for row in report["resource_shapes"]
        if row["resource_shape_sha256"] == _sha("4")
    )
    identity = ambiguous["geometry_pointer_identities"][0]

    assert identity["geometry_candidate_gate_status"] == "geometry-seed-outside-static-candidate-set"
    assert identity["candidate_content_group_count"] == 2
    assert report["summary"]["newly_resolved_geometry_identity_count"] == 0


def test_geometry_pointer_join_rejects_wrong_contracts():
    good_material = _material_report([])
    good_pointer = _pointer_report([])

    for pointer, material in [
        ({"format": "wrong"}, good_material),
        (good_pointer, {"format": "wrong"}),
        ({
            "format": "SHIFT.D3D9TargetPointerObservations/1",
            "catalog_alignment": {"status": "mismatch"},
            "resource_shapes": [],
        }, good_material),
    ]:
        try:
            build_runtime_geometry_pointer_candidate_join(pointer, material)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid input contract must fail")
