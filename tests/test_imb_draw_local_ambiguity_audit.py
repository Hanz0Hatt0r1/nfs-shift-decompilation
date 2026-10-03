from imb_draw_local_ambiguity_audit import (
    FORMAT,
    build_draw_local_ambiguity_audit,
)


def _sha(char):
    return char * 64


def _candidate(
    content,
    imb,
    path,
    *,
    bmt="b",
    vs="1",
    ps="2",
    cross_vs=False,
):
    return {
        "content_group_sha256": _sha(content),
        "imb_sha256": _sha(imb),
        "imb_paths": [path],
        "archives": ["Silverstone_Era3_GrandPrix.bff"],
        "bmt_sha256": _sha(bmt),
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
            "sibling-runtime-pipeline-same-ps-layout" if cross_vs else None
        ),
        "pipeline_recovery_static_vertex_shader_mismatch": cross_vs,
        "shader_gate_status": (
            "exact-ps-byte-match-cross-vs-donor"
            if cross_vs
            else "exact-ps-byte-match"
        ),
    }


def _ambiguous(candidates, *, event=100, geometry="3", resource="4"):
    return {
        "candidate_resolution_status": "ambiguous-static-candidates",
        "event_index": event,
        "frame": 7,
        "draw_evidence_sha256": _sha("5"),
        "resource_shape_sha256": _sha(resource),
        "geometry_pointer_identity_sha256": _sha(geometry),
        "shader_pair": {
            "vertex_shader_sha256": _sha("1"),
            "pixel_shader_sha256": _sha("2"),
        },
        "surviving_candidate_variants": candidates,
    }


def _single(candidate):
    return {
        "candidate_resolution_status": "single-static-candidate",
        "event_index": 99,
        "surviving_candidate_variants": [candidate],
    }


def _report(draws):
    return {
        "format": "SHIFT.IMBDrawLocalStaticCandidateJoin/1",
        "draws": draws,
    }


def test_metadata_equivalent_lod_siblings_are_not_ranked():
    draws = _report([
        _ambiguous([
            _candidate(
                "a", "c", "characters/crowds/crowd_man_01_loda.imb"
            ),
            _candidate(
                "d", "e", "characters/crowds/crowd_man_01_lodb.imb"
            ),
        ])
    ])

    result = build_draw_local_ambiguity_audit(draws)
    assert result["format"] == FORMAT
    row = result["ambiguous_draws"][0]
    assert row["ambiguity_class"] == "metadata-equivalent-lod-siblings"
    assert row["metadata_equivalent_except_imb_identity"] is True
    assert row["lod_path_diagnostic"]["status"] == "path-name-lod-siblings"
    assert row["next_gate"] == "static-scene-reference-or-portable-geometry-identity"
    assert result["boundary"]["candidate_ranking"] is False
    assert result["boundary"]["lod_path_is_identity_proof"] is False


def test_distinct_bmt_candidates_route_to_offline_material_evidence():
    result = build_draw_local_ambiguity_audit(_report([
        _ambiguous([
            _candidate("a", "c", "tracks/a.imb", bmt="b"),
            _candidate("d", "e", "tracks/b.imb", bmt="f"),
        ])
    ]))

    row = result["ambiguous_draws"][0]
    assert row["ambiguity_class"] == "material-distinct-candidates"
    assert row["distinct_bmt_sha256_count"] == 2
    assert row["next_gate"] == "offline-exact-material-content-correlation"
    assert row["minimal_evidence"]["offline_first"]


def test_shader_provenance_difference_is_preserved_without_selection():
    result = build_draw_local_ambiguity_audit(_report([
        _ambiguous([
            _candidate("a", "c", "tracks/a.imb", vs="1"),
            _candidate("d", "e", "tracks/b.imb", vs="6"),
        ])
    ]))

    row = result["ambiguous_draws"][0]
    assert row["ambiguity_class"] == "shader-provenance-distinct-candidates"
    assert row["distinct_static_shader_pair_count"] == 2
    assert row["next_gate"] == "offline-exact-fxo-pair-provenance"
    assert row["surviving_content_group_count"] == 2


def test_cross_vs_donor_flag_is_diagnostic_only():
    result = build_draw_local_ambiguity_audit(_report([
        _ambiguous([
            _candidate("a", "c", "tracks/a.imb", vs="6", cross_vs=True),
            _candidate("d", "e", "tracks/b.imb", vs="6", cross_vs=True),
        ])
    ]))

    row = result["ambiguous_draws"][0]
    assert row["all_cross_vs_donor_evidence"] is True
    assert result["summary"]["all_cross_vs_donor_ambiguous_draw_count"] == 1


def test_summary_groups_repeated_candidate_sets_and_counts_singles():
    a = _candidate("a", "c", "tracks/a.imb")
    b = _candidate("d", "e", "tracks/b.imb")
    result = build_draw_local_ambiguity_audit(_report([
        _single(a),
        _ambiguous([a, b], event=101),
        _ambiguous([a, b], event=102),
    ]))

    summary = result["summary"]
    assert summary["source_draw_count"] == 3
    assert summary["single_static_candidate_draw_count"] == 1
    assert summary["ambiguous_static_candidate_draw_count"] == 2
    assert summary["unique_ambiguous_candidate_set_count"] == 1
    assert result["candidate_sets"][0]["draw_count"] == 2
    assert summary["surviving_content_group_count_distribution"] == {"2": 2}


def test_output_is_deterministic_and_wrong_contract_fails_closed():
    report = _report([
        _ambiguous([
            _candidate("a", "c", "tracks/a.imb"),
            _candidate("d", "e", "tracks/b.imb"),
        ])
    ])
    first = build_draw_local_ambiguity_audit(report)
    second = build_draw_local_ambiguity_audit(report)
    assert first == second

    try:
        build_draw_local_ambiguity_audit({"format": "wrong", "draws": []})
    except ValueError:
        pass
    else:
        raise AssertionError("wrong input contract must fail")
