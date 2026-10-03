from imb_draw_local_static_candidate_join import (
    FORMAT,
    _canonical_hash,
    _draw_resource_shape,
    build_draw_local_static_candidate_join,
)


def _sha(char):
    return char * 64


def _identity(*, primitive_count=12):
    return {
        "device_ptr": "0x1",
        "stream0_vertex_buffer_ptr": "0x40",
        "stream0_vertex_buffer_creation_event_index": 100,
        "index_buffer_ptr": "0x50",
        "index_buffer_creation_event_index": 101,
        "draw_range": {
            "primitive_type": 4,
            "base_vertex_index": 0,
            "start_index": 0,
            "primitive_count": primitive_count,
        },
        "creation_identity_complete": True,
    }


def _draw(*, vs="1", ps="2", event=200, primitive_count=12):
    identity = _identity(primitive_count=primitive_count)
    identity.pop("creation_identity_complete")
    return {
        "classification": "strong-capture-local",
        "event_index": event,
        "frame": 10,
        "draw_evidence_sha256": _sha("9"),
        "device_ptr": "0x1",
        "geometry_identity": identity,
        "shader_pair": {
            "vertex_shader_sha256": _sha(vs),
            "pixel_shader_sha256": _sha(ps),
        },
        "declaration": {
            "declaration_sha256": _sha("d"),
        },
        "streams": [
            {
                "stream": 0,
                "stride": 80,
                "descriptor": {
                    "length": 800,
                    "usage": 0,
                    "fvf": 0,
                    "pool": 1,
                },
            },
            {
                "stream": 1,
                "stride": 64,
                "descriptor": {
                    "length": 1024,
                    "usage": 520,
                    "fvf": 0,
                    "pool": 0,
                },
            },
        ],
        "index_binding": {
            "descriptor": {
                "length": 72,
                "usage": 0,
                "format": 101,
                "pool": 1,
            }
        },
        "sampler_bindings": [
            {
                "stage": 0,
                "descriptor": {
                    "resource_type_name": "texture2d",
                    "width": 512,
                    "height": 512,
                    "depth": None,
                    "edge_length": None,
                    "format": 827611204,
                    "pool": 1,
                    "level_count": 10,
                    "levels": 10,
                    "usage": 0,
                },
            }
        ],
    }


def _candidate(content, *, vs="1", ps="2", cross_vs=False):
    return {
        "content_group_sha256": _sha(content),
        "imb_sha256": _sha(content.upper()),
        "imb_paths": [f"tracks/{content}.imb"],
        "archives": ["Silverstone.bff"],
        "bmt_sha256": _sha("b"),
        "shader_family": "crowdgeninstanced",
        "primitive_index": 0,
        "draw_range": {
            "first_index": 0,
            "index_count": 36,
            "primitive_count": 12,
        },
        "static_vertex_stride": 80,
        "matched_vertex_shader_sha256": _sha(vs) if vs else None,
        "matched_pixel_shader_sha256": _sha(ps) if ps else None,
        "pipeline_recovery_evidence_kind": (
            "relaxed-cross-vs" if cross_vs else "exact-vs+ps"
        ),
        "pipeline_recovery_static_vertex_shader_mismatch": cross_vs,
    }


def _geometry_join(candidates, *, identity=None, resource_sha=None):
    identity = identity or _identity()
    return {
        "format": "SHIFT.IMBRuntimeGeometryPointerCandidateJoin/1",
        "resource_shapes": [
            {
                "resource_shape_sha256": resource_sha or _sha("7"),
                "geometry_pointer_identities": [
                    {
                        "geometry_pointer_identity_sha256": _canonical_hash(identity),
                        "geometry_candidate_gate_status": "no-seed",
                        "candidate_content_status": "ambiguous-content-candidates",
                        "candidate_content_groups": candidates,
                    }
                ],
            }
        ],
    }


def _draw_local(draws):
    return {
        "format": "SHIFT.D3D9TargetDrawLocalEvidence/1",
        "draws": draws,
    }


def test_exact_resource_and_shader_pair_reduce_to_single_candidate():
    draw = _draw()
    resource_sha = _canonical_hash(_draw_resource_shape(draw))
    report = build_draw_local_static_candidate_join(
        _draw_local([draw]),
        _geometry_join(
            [
                _candidate("a", vs="1", ps="2"),
                _candidate("c", vs="1", ps="3"),
            ],
            resource_sha=resource_sha,
        ),
    )

    assert report["format"] == FORMAT
    row = report["draws"][0]
    assert row["phase615_match_kind"] == "exact-resource+geometry"
    assert row["source_candidate_variant_count"] == 2
    assert row["surviving_content_group_count"] == 1
    assert row["candidate_resolution_status"] == "single-static-candidate"
    assert row["surviving_content_group_sha256s"] == [_sha("a")]
    assert row["surviving_candidate_variants"][0]["shader_gate_status"] == "exact-vs+ps-byte-match"
    assert row["rejected_candidate_variants"][0]["shader_gate_status"] == "rejected-pixel-shader-byte-mismatch"
    assert report["summary"]["single_static_candidate_draw_count"] == 1
    assert report["summary"]["exact_vs_ps_candidate_draw_count"] == 1
    assert report["summary"]["phase615_match_kind_counts"] == {
        "exact-resource+geometry": 1
    }


def test_cross_vs_donor_mismatch_is_not_used_as_rejection():
    report = build_draw_local_static_candidate_join(
        _draw_local([_draw(vs="1", ps="2")]),
        _geometry_join([
            _candidate("a", vs="4", ps="2", cross_vs=True),
        ]),
    )

    row = report["draws"][0]
    assert row["candidate_resolution_status"] == "single-static-candidate"
    assert row["surviving_candidate_variants"][0]["shader_gate_status"] == "exact-ps-byte-match-cross-vs-donor"
    assert row["rejected_candidate_variant_count"] == 0
    assert report["summary"]["exact_vs_ps_candidate_draw_count"] == 0


def test_equal_exact_shader_pairs_remain_ambiguous():
    report = build_draw_local_static_candidate_join(
        _draw_local([_draw()]),
        _geometry_join([
            _candidate("a"),
            _candidate("c"),
        ]),
    )

    row = report["draws"][0]
    assert row["candidate_resolution_status"] == "ambiguous-static-candidates"
    assert row["surviving_content_group_count"] == 2
    assert report["summary"]["ambiguous_static_candidate_draw_count"] == 1
    assert report["boundary"]["single_candidate_is_retail_identity"] is False


def test_missing_shader_hashes_fail_open():
    report = build_draw_local_static_candidate_join(
        _draw_local([_draw()]),
        _geometry_join([
            _candidate("a", vs="", ps=""),
            _candidate("c", vs="1", ps="3"),
        ]),
    )

    row = report["draws"][0]
    assert row["candidate_resolution_status"] == "single-static-candidate"
    assert row["surviving_candidate_variants"][0]["shader_gate_status"] == "shader-byte-gate-unavailable"
    assert row["rejected_candidate_variants"][0]["shader_gate_status"] == "rejected-pixel-shader-byte-mismatch"


def test_geometry_only_multi_resource_fallback_preserves_shader_variants():
    identity = _identity()
    identity_sha = _canonical_hash(identity)
    geometry = {
        "format": "SHIFT.IMBRuntimeGeometryPointerCandidateJoin/1",
        "resource_shapes": [
            {
                "resource_shape_sha256": _sha("7"),
                "geometry_pointer_identities": [
                    {
                        "geometry_pointer_identity_sha256": identity_sha,
                        "candidate_content_groups": [
                            _candidate("a", vs="1", ps="3")
                        ],
                    }
                ],
            },
            {
                "resource_shape_sha256": _sha("8"),
                "geometry_pointer_identities": [
                    {
                        "geometry_pointer_identity_sha256": identity_sha,
                        "candidate_content_groups": [
                            _candidate("a", vs="1", ps="2")
                        ],
                    }
                ],
            },
        ],
    }

    report = build_draw_local_static_candidate_join(
        _draw_local([_draw()]), geometry
    )
    row = report["draws"][0]

    assert row["phase615_match_kind"] == "geometry-only-multi-resource-fallback"
    assert row["source_candidate_variant_count"] == 2
    assert row["surviving_content_group_count"] == 1
    assert row["candidate_resolution_status"] == "single-static-candidate"
    assert len(row["surviving_candidate_variants"]) == 1
    assert len(row["rejected_candidate_variants"]) == 1


def test_unmatched_geometry_identity_stays_unresolved_and_is_deterministic():
    draws = _draw_local([_draw(primitive_count=13)])
    geometry = _geometry_join([_candidate("a")])

    first = build_draw_local_static_candidate_join(draws, geometry)
    second = build_draw_local_static_candidate_join(draws, geometry)

    assert first == second
    row = first["draws"][0]
    assert row["phase615_match_kind"] == "unmatched"
    assert row["candidate_resolution_status"] == "geometry-identity-not-in-phase615"
    assert row["surviving_content_group_count"] == 0


def test_wrong_input_contracts_fail_closed():
    good_draws = _draw_local([])
    good_geometry = _geometry_join([])

    for draws, geometry in [
        ({"format": "wrong"}, good_geometry),
        (good_draws, {"format": "wrong"}),
    ]:
        try:
            build_draw_local_static_candidate_join(draws, geometry)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid input contract must fail")
