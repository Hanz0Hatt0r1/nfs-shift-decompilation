import hashlib

from imb_runtime_pipeline_candidate_join import (
    FORMAT,
    build_runtime_pipeline_candidate_join,
)


def _sha(label):
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


VS_A = _sha("vs-a")
VS_B = _sha("vs-b")
VS_C = _sha("vs-c")
PS_X = _sha("ps-x")
PS_Y = _sha("ps-y")


def _binding(index, family, vs, ps):
    return {
        "binding_index": index,
        "archive": "Silverstone_Era3_GrandPrix.bff",
        "imb_path": f"tracks/_data/instances/object_{index}.imb",
        "imb_sha256": _sha(f"imb-{index}"),
        "primitive_index": 0,
        "draw_range": {
            "first_index": 0,
            "index_count": 72,
            "primitive_count": 24,
        },
        "material_reference": f"MAT_{index}",
        "bmt": f"materials/mat_{index}.bmt",
        "bmt_sha256": _sha(f"bmt-{index}"),
        "shader": f"render/shaders/{family}.fx",
        "shader_family": family,
        "vertex_properties": ["200", "460"],
        "property_descriptors": [],
        "resource_identity_ready": True,
        "draw_range_ready": True,
        "same_instance_match_ready": True,
        "targets": [{
            "identity_kind": "pixel",
            "identity_value": ps,
            "strength": "prefilter-only",
            "candidate_variants": [{
                "vertex_byte_sha256": vs,
                "pixel_byte_sha256": ps,
                "pair_byte_sha256": _sha(f"pair-{index}"),
                "permutation_identity_sha256": _sha(
                    f"permutation-{index}"
                ),
                "candidate_file": f"{family}_{index}.fxo",
                "candidate_program_offset": 128 + index,
                "candidate_vertex_program_offset": 64 + index,
                "vertex_pair_selection_status": "unique",
                "exact": True,
            }],
        }],
    }


def _runtime_pipeline(signature, vs, ps, draws, family):
    return {
        "signature_sha256": _sha(signature),
        "draw_count": draws,
        "primitive_count_sum": draws * 24,
        "first_frame": 4287,
        "last_frame": 4308,
        "families": [family],
        "signature": {
            "vertex_shader_sha256": vs,
            "pixel_shader_sha256": ps,
            "declaration_sha256": _sha(f"decl-{family}"),
            "stream_layout": [
                {"stream": 0, "stride": 80},
                {"stream": 1, "stride": 64},
            ],
            "index_format": 101,
        },
    }


def test_pipeline_candidate_join_distinguishes_ambiguous_unique_and_pixel_only():
    target_set = {
        "format": "SHIFT.IMBRuntimeShaderTargetSet/1",
        "binding_targets": [
            _binding(0, "crowdgeninstanced", VS_A, PS_X),
            _binding(1, "crowdgeninstanced", VS_A, PS_X),
            _binding(2, "basicinstanced", VS_B, PS_Y),
        ],
    }
    runtime = {
        "format": "SHIFT.D3D9TargetDrawSignatureCatalog/1",
        "pipeline_signatures": [
            _runtime_pipeline(
                "ambiguous",
                VS_A,
                PS_X,
                5,
                "crowdgeninstanced",
            ),
            _runtime_pipeline(
                "unique",
                VS_B,
                PS_Y,
                3,
                "basicinstanced",
            ),
            _runtime_pipeline(
                "pixel-only",
                VS_C,
                PS_X,
                2,
                "crowdgeninstanced",
            ),
        ],
    }

    report = build_runtime_pipeline_candidate_join(runtime, target_set)

    assert report["format"] == FORMAT
    assert report["summary"]["runtime_pipeline_signature_count"] == 3
    assert report["summary"]["runtime_draw_count"] == 10
    assert report["summary"]["exact_vs_ps_candidate_pipeline_count"] == 2
    assert report["summary"]["exact_vs_ps_candidate_draw_count"] == 8
    assert (
        report["summary"][
            "single_static_binding_candidate_pipeline_count"
        ]
        == 1
    )
    assert (
        report["summary"][
            "single_static_binding_candidate_draw_count"
        ]
        == 3
    )
    assert report["summary"]["distinct_static_candidate_binding_count"] == 3
    assert report["summary"]["candidate_binding_count_distribution"] == {
        "1": 1,
        "2": 1,
    }
    assert report["summary"]["status_counts"] == {
        "ambiguous-static-binding-candidates": 1,
        "pixel-only-static-overlap": 1,
        "single-static-binding-candidate": 1,
    }

    by_draws = {
        row["draw_count"]: row
        for row in report["pipeline_candidates"]
    }
    ambiguous = by_draws[5]
    assert ambiguous["candidate_binding_indices"] == [0, 1]
    assert ambiguous["candidate_variant_count"] == 2
    assert ambiguous["family_consistent"] is True

    unique = by_draws[3]
    assert unique["status"] == "single-static-binding-candidate"
    assert unique["candidate_binding_indices"] == [2]
    assert unique["candidates"][0]["same_instance_match_ready"] is True

    pixel_only = by_draws[2]
    assert pixel_only["status"] == "pixel-only-static-overlap"
    assert pixel_only["candidate_binding_count"] == 0


def test_pipeline_candidate_join_deduplicates_repeated_static_variant():
    binding = _binding(0, "basicinstanced", VS_B, PS_Y)
    repeated = dict(binding["targets"][0])
    repeated["candidate_variants"] = [
        dict(binding["targets"][0]["candidate_variants"][0])
    ]
    binding["targets"].append(repeated)
    target_set = {
        "format": "SHIFT.IMBRuntimeShaderTargetSet/1",
        "binding_targets": [binding],
    }
    runtime = {
        "format": "SHIFT.D3D9TargetDrawSignatureCatalog/1",
        "pipeline_signatures": [
            _runtime_pipeline(
                "unique",
                VS_B,
                PS_Y,
                1,
                "basicinstanced",
            )
        ],
    }

    report = build_runtime_pipeline_candidate_join(runtime, target_set)

    row = report["pipeline_candidates"][0]
    assert row["candidate_binding_count"] == 1
    assert row["candidate_variant_count"] == 1


def test_pipeline_candidate_join_rejects_wrong_contracts():
    target_set = {
        "format": "SHIFT.IMBRuntimeShaderTargetSet/1",
        "binding_targets": [],
    }
    try:
        build_runtime_pipeline_candidate_join(
            {"format": "wrong"},
            target_set,
        )
    except ValueError as error:
        assert "runtime catalog" in str(error)
    else:
        raise AssertionError("wrong runtime contract must fail")

    try:
        build_runtime_pipeline_candidate_join(
            {
                "format": "SHIFT.D3D9TargetDrawSignatureCatalog/1",
                "pipeline_signatures": [],
            },
            {"format": "wrong"},
        )
    except ValueError as error:
        assert "target set" in str(error)
    else:
        raise AssertionError("wrong target contract must fail")

def _prefilter_binding(index, family, ps, properties):
    row = _binding(index, family, VS_A, ps)
    row["vertex_properties"] = list(properties)
    row["targets"] = [{
        "identity_kind": "pixel",
        "identity_value": ps,
        "strength": "prefilter-only",
        "candidate_variant_count": 2,
        "candidate_variants": [
            {
                "vertex_byte_sha256": None,
                "pixel_byte_sha256": ps,
                "pair_byte_sha256": None,
                "permutation_identity_sha256": None,
                "candidate_file": f"{family}_{index}.fxo",
                "candidate_program_offset": 100,
                "candidate_vertex_program_offset": None,
                "vertex_pair_selection_status": "none",
                "exact": False,
            },
            {
                "vertex_byte_sha256": None,
                "pixel_byte_sha256": ps,
                "pair_byte_sha256": None,
                "permutation_identity_sha256": None,
                "candidate_file": f"{family}_{index}.fxo",
                "candidate_program_offset": 200,
                "candidate_vertex_program_offset": None,
                "vertex_pair_selection_status": "none",
                "exact": False,
            },
        ],
    }]
    return row


def test_pipeline_candidate_join_uses_pixel_plus_source_stride_fallback():
    target_set = {
        "format": "SHIFT.IMBRuntimeShaderTargetSet/1",
        "binding_targets": [
            _prefilter_binding(
                10,
                "crowdgeninstanced",
                PS_X,
                ["200", "460", "220", "240", "250", "130", "580", "310"],
            ),
            _prefilter_binding(
                11,
                "basicinstanced",
                PS_X,
                ["200", "460", "220", "130"],
            ),
        ],
    }
    runtime = {
        "format": "SHIFT.D3D9TargetDrawSignatureCatalog/1",
        "pipeline_signatures": [
            _runtime_pipeline(
                "layout-fallback",
                VS_C,
                PS_X,
                7,
                "crowdgeninstanced",
            )
        ],
    }

    report = build_runtime_pipeline_candidate_join(runtime, target_set)

    row = report["pipeline_candidates"][0]
    assert row["status"] == "single-layout-pixel-static-binding-candidate"
    assert row["candidate_evidence_kind"] == "pixel+static-vertex-stride"
    assert row["runtime_vertex_stride"] == 80
    assert row["candidate_binding_indices"] == [10]
    assert row["candidate_binding_count"] == 1
    assert row["candidate_variant_count"] == 2
    assert row["candidates"][0]["static_vertex_stride"] == 80
    assert row["candidates"][0]["matched_variant_count"] == 2
    assert report["summary"]["layout_pixel_candidate_pipeline_count"] == 1
    assert report["summary"]["layout_pixel_candidate_draw_count"] == 7
    assert report["summary"]["candidate_draw_coverage"] == 1.0


def test_exact_pair_target_does_not_degrade_to_pixel_stride_fallback():
    binding = _binding(0, "crowdgeninstanced", VS_A, PS_X)
    binding["vertex_properties"] = [
        "200", "460", "220", "240", "250", "130", "580", "310"
    ]
    binding["targets"][0]["strength"] = "exact-pair"
    target_set = {
        "format": "SHIFT.IMBRuntimeShaderTargetSet/1",
        "binding_targets": [binding],
    }
    runtime = {
        "format": "SHIFT.D3D9TargetDrawSignatureCatalog/1",
        "pipeline_signatures": [
            _runtime_pipeline(
                "wrong-vs",
                VS_C,
                PS_X,
                2,
                "crowdgeninstanced",
            )
        ],
    }

    report = build_runtime_pipeline_candidate_join(runtime, target_set)

    row = report["pipeline_candidates"][0]
    assert row["status"] == "pixel-only-static-overlap"
    assert row["candidate_binding_count"] == 0
    assert report["summary"]["layout_pixel_candidate_pipeline_count"] == 0

