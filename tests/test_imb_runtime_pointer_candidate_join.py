import hashlib

from imb_runtime_pointer_candidate_join import (
    FORMAT,
    MATERIAL_FORMAT,
    POINTER_FORMAT,
    build_runtime_pointer_candidate_join,
)


def _sha(label):
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


CONTENT_A = _sha("content-a")
CONTENT_B = _sha("content-b")
POINTER_SHARED = _sha("pointer-shared")
POINTER_UNSEEDED = _sha("pointer-unseeded")


def _group(content_sha, label):
    return {
        "content_group_sha256": content_sha,
        "imb_sha256": _sha(f"imb-{label}"),
        "imb_paths": [f"tracks/{label}.imb"],
        "archives": ["Silverstone_Era3_Drift.bff"],
        "bmt_sha256": _sha(f"bmt-{label}"),
        "shader_family": "foliageinstanced",
        "primitive_index": 0,
        "draw_range": {
            "first_index": 0,
            "index_count": 36,
            "primitive_count": 12,
        },
        "static_vertex_stride": 36,
        "matched_pixel_shader_sha256": _sha("ps"),
    }


def _material_row(resource_sha, groups, *, draws):
    hashes = [row["content_group_sha256"] for row in groups]
    return {
        "resource_shape_sha256": resource_sha,
        "geometry_shape_sha256": _sha(f"geometry-{resource_sha}"),
        "pipeline_signature_sha256": _sha(f"pipeline-{resource_sha}"),
        "families": ["foliageinstanced"],
        "draw_count": draws,
        "candidate_content_status": (
            "single-content-candidate"
            if len(hashes) == 1
            else "ambiguous-content-candidates"
        ),
        "candidate_content_group_count": len(hashes),
        "candidate_content_group_sha256s": hashes,
        "candidate_content_groups": groups,
        "material_descriptor_gate_status": "matched-all",
    }


def _pointer_observation(identity_sha, draws):
    return {
        "identity_sha256": identity_sha,
        "identity": {
            "geometry": {
                "device_ptr": "0x1",
                "stream0_vertex_buffer_ptr": "0x40",
                "stream0_vertex_buffer_creation_event_index": 4,
                "index_buffer_ptr": "0x50",
                "index_buffer_creation_event_index": 6,
                "draw_range": {
                    "primitive_type": 4,
                    "base_vertex_index": 0,
                    "start_index": 0,
                    "primitive_count": 12,
                },
            },
            "material": {
                "device_ptr": "0x1",
                "texture_stages": [],
            },
        },
        "draw_count": draws,
        "draw_count_in_resource_shape": draws,
        "first_frame": 4287,
        "last_frame": 4308,
    }


def _pointer_row(resource_sha, observations):
    return {
        "resource_shape_sha256": resource_sha,
        "draw_count": sum(
            row["draw_count_in_resource_shape"] for row in observations
        ),
        "combined_pointer_identity_count": len(observations),
        "combined_pointer_observations": observations,
    }


def _reports(material_rows, pointer_rows):
    material = {
        "format": MATERIAL_FORMAT,
        "resource_shapes": material_rows,
    }
    pointer = {
        "format": POINTER_FORMAT,
        "catalog_alignment": {"status": "exact"},
        "resource_shapes": pointer_rows,
    }
    return pointer, material


def test_pointer_join_narrows_per_object_without_collapsing_whole_shape():
    resource_seed = _sha("resource-seed")
    resource_mixed = _sha("resource-mixed")
    resource_all = _sha("resource-all")
    group_a = _group(CONTENT_A, "tree-a")
    group_b = _group(CONTENT_B, "tree-b")

    material_rows = [
        _material_row(resource_seed, [group_a], draws=5),
        _material_row(resource_mixed, [group_a, group_b], draws=10),
        _material_row(resource_all, [group_a, group_b], draws=4),
    ]
    pointer_rows = [
        _pointer_row(
            resource_seed,
            [_pointer_observation(POINTER_SHARED, 5)],
        ),
        _pointer_row(
            resource_mixed,
            [
                _pointer_observation(POINTER_SHARED, 7),
                _pointer_observation(POINTER_UNSEEDED, 3),
            ],
        ),
        _pointer_row(
            resource_all,
            [_pointer_observation(POINTER_SHARED, 4)],
        ),
    ]
    pointer, material = _reports(material_rows, pointer_rows)

    report = build_runtime_pointer_candidate_join(pointer, material)

    assert report["format"] == FORMAT
    summary = report["summary"]
    assert summary["runtime_resource_shape_count"] == 3
    assert summary["runtime_resource_shape_draw_count"] == 19
    assert summary["combined_pointer_identity_observation_count"] == 4
    assert summary["combined_pointer_identity_draw_count"] == 19
    assert summary["pointer_seed_identity_count"] == 1
    assert summary["pointer_seed_status_counts"] == {
        "unique-content-seed": 1
    }
    assert summary["newly_resolved_pointer_identity_count"] == 2
    assert summary["newly_resolved_pointer_identity_draw_count"] == 11
    assert summary["pointer_seed_conflict_identity_count"] == 0

    by_resource = {
        row["resource_shape_sha256"]: row
        for row in report["resource_shapes"]
    }
    mixed = by_resource[resource_mixed]
    assert mixed["pointer_resource_status"] == (
        "pointer-identities-still-ambiguous"
    )
    by_identity = {
        row["combined_pointer_identity_sha256"]: row
        for row in mixed["pointer_identities"]
    }
    shared = by_identity[POINTER_SHARED]
    assert shared["pointer_candidate_gate_status"] == (
        "reduced-by-same-object-seed"
    )
    assert shared["candidate_content_group_sha256s"] == [CONTENT_A]
    assert shared["candidate_content_status"] == "single-content-candidate"

    unseeded = by_identity[POINTER_UNSEEDED]
    assert unseeded["pointer_candidate_gate_status"] == "no-seed"
    assert unseeded["candidate_content_status"] == (
        "ambiguous-content-candidates"
    )
    assert set(unseeded["candidate_content_group_sha256s"]) == {
        CONTENT_A,
        CONTENT_B,
    }

    all_seeded = by_resource[resource_all]
    assert all_seeded["pointer_resource_status"] == (
        "single-content-across-pointer-identities"
    )
    assert all_seeded["resolved_content_group_sha256s"] == [CONTENT_A]


def test_pointer_join_conflicting_single_seeds_fail_closed():
    seed_a = _sha("seed-a")
    seed_b = _sha("seed-b")
    target = _sha("target")
    group_a = _group(CONTENT_A, "tree-a")
    group_b = _group(CONTENT_B, "tree-b")

    material_rows = [
        _material_row(seed_a, [group_a], draws=2),
        _material_row(seed_b, [group_b], draws=3),
        _material_row(target, [group_a, group_b], draws=5),
    ]
    pointer_rows = [
        _pointer_row(seed_a, [_pointer_observation(POINTER_SHARED, 2)]),
        _pointer_row(seed_b, [_pointer_observation(POINTER_SHARED, 3)]),
        _pointer_row(target, [_pointer_observation(POINTER_SHARED, 5)]),
    ]
    pointer, material = _reports(material_rows, pointer_rows)

    report = build_runtime_pointer_candidate_join(pointer, material)

    assert report["summary"]["pointer_seed_status_counts"] == {
        "conflicting-content-seeds": 1
    }
    assert report["summary"]["newly_resolved_pointer_identity_count"] == 0
    assert report["summary"]["pointer_seed_conflict_identity_count"] == 1
    assert report["summary"]["pointer_seed_conflict_draw_count"] == 5

    target_row = next(
        row
        for row in report["resource_shapes"]
        if row["resource_shape_sha256"] == target
    )
    identity = target_row["pointer_identities"][0]
    assert identity["pointer_candidate_gate_status"] == (
        "conflicting-pointer-seeds"
    )
    assert identity["candidate_content_status"] == (
        "ambiguous-content-candidates"
    )
    assert set(identity["candidate_content_group_sha256s"]) == {
        CONTENT_A,
        CONTENT_B,
    }


def test_pointer_join_requires_exact_catalog_alignment_and_shape_sets():
    resource = _sha("resource")
    group = _group(CONTENT_A, "tree-a")
    material_row = _material_row(resource, [group], draws=1)
    pointer_row = _pointer_row(
        resource,
        [_pointer_observation(POINTER_SHARED, 1)],
    )
    pointer, material = _reports([material_row], [pointer_row])

    wrong_alignment = dict(pointer)
    wrong_alignment["catalog_alignment"] = {"status": "mismatch"}
    try:
        build_runtime_pointer_candidate_join(wrong_alignment, material)
    except ValueError as error:
        assert "exact Phase 605 catalog alignment" in str(error)
    else:
        raise AssertionError("mismatched catalog alignment must fail")

    wrong_set = dict(pointer)
    wrong_set["resource_shapes"] = []
    try:
        build_runtime_pointer_candidate_join(wrong_set, material)
    except ValueError as error:
        assert "resource-shape set mismatch" in str(error)
    else:
        raise AssertionError("resource-shape mismatch must fail")

    for bad_pointer, bad_material, expected in [
        ({"format": "wrong"}, material, "pointer report"),
        (pointer, {"format": "wrong"}, "material join"),
    ]:
        try:
            build_runtime_pointer_candidate_join(
                bad_pointer,
                bad_material,
            )
        except ValueError as error:
            assert expected in str(error)
        else:
            raise AssertionError("wrong contract must fail")
