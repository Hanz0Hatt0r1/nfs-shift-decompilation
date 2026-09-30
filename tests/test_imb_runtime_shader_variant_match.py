from imb_runtime_shader_variant_match import (
    FORMAT,
    match_imb_runtime_shader_variants,
)


def _sha(char):
    return char * 64


def _variant(
    *,
    permutation="1",
    pair="2",
    vertex="3",
    pixel="4",
):
    return {
        "permutation_identity_sha256": _sha(permutation),
        "pair_byte_sha256": _sha(pair),
        "vertex_byte_sha256": _sha(vertex),
        "pixel_byte_sha256": _sha(pixel),
        "candidate_file": "render/cache/example.fxo",
        "candidate_program_offset": 128,
        "candidate_vertex_program_offset": 64,
        "vertex_pair_selection_status": "ambiguous",
        "exact": True,
    }


def _binding(index, variants, *, first_index=0, index_count=6):
    return {
        "binding_index": index,
        "archive": "Silverstone_Era3_GrandPrix.bff",
        "imb_path": "tracks/silverstone/object.imb",
        "imb_entry_index": 100,
        "imb_sha256": _sha("f"),
        "primitive_index": index,
        "draw_range": {
            "first_index": first_index,
            "index_count": index_count,
            "primitive_count": index_count // 3,
        },
        "resource_identity_ready": True,
        "draw_range_ready": True,
        "same_instance_match_ready": True,
        "material_reference": "materials/test.mtx",
        "shader_family": "basicinstanced",
        "targets": [
            {
                "identity_kind": "pixel",
                "identity_value": _sha("4"),
                "strength": "prefilter-only",
                "candidate_variant_count": len(variants),
                "candidate_variants": variants,
            }
        ],
    }


def _target_set(*bindings):
    return {
        "format": "SHIFT.IMBRuntimeShaderTargetSet/1",
        "capture_ready": True,
        "same_instance_match_ready": True,
        "binding_targets": list(bindings),
    }


def _identity(
    *,
    permutation="1",
    pair="2",
    vertex="3",
    pixel="4",
):
    return {
        "format": "SHIFT.ShaderPermutationIdentity/1",
        "identity_sha256": _sha(permutation),
        "pair_byte_sha256": _sha(pair),
        "vertex_byte_sha256": _sha(vertex),
        "pixel_byte_sha256": _sha(pixel),
        "payload": {
            "vertex": {"byte_sha256": _sha(vertex)},
            "pixel": {"byte_sha256": _sha(pixel)},
        },
    }


def _snapshot(
    *,
    draw_index=0,
    first_index=0,
    index_count=6,
    identity=None,
):
    return {
        "format": "SHIFT.D3D9DrawStateSnapshot/1",
        "frame": 1,
        "draw_index": draw_index,
        "draw": {
            "start_index": first_index,
            "primitive_count": index_count // 3,
        },
        "vertex_declaration": {
            "resource_path": "tracks/silverstone/object.imb",
            "resource_sha256": _sha("f"),
        },
        "shader_permutation_identity": identity or _identity(),
    }


def _runtime(*snapshots, gate_ready=True, descriptor_proof=True):
    candidate_frames = []
    for snapshot in snapshots:
        candidate_frames.append({
            "frame": 1,
            "draw_index": snapshot["draw_index"],
            "same_meb_resource": True,
            "bound_declaration_valid": True,
            "snapshot_schema_status": "valid",
            "descriptor_matches": (
                [{"property_id": "200"}] if descriptor_proof else []
            ),
        })
    return {
        "format": "SHIFT.D3D9RuntimeBindingEvidence/1",
        "frames": [{
            "frame": 1,
            "draw_snapshots": list(snapshots),
        }],
        "meb_correlation": {
            "resource_identity": {
                "resource_path": "tracks/silverstone/object.imb",
                "resource_sha256": _sha("f"),
            }
        },
        "same_instance_gate": {
            "ready": gate_ready,
            "candidate_frames": candidate_frames,
        },
    }


def test_matcher_attributes_unique_exact_runtime_variant():
    report = match_imb_runtime_shader_variants(
        _target_set(_binding(0, [_variant()])),
        _runtime(_snapshot()),
    )

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["summary"]["resource_binding_count"] == 1
    assert report["summary"]["attributed_binding_count"] == 1
    row = report["binding_results"][0]
    assert row["attributed"] is True
    assert row["best_score"] == 100
    assert row["selected_variant"]["permutation_identity_sha256"] == _sha("1")
    assert row["selected_variant"]["candidate_vertex_program_offset"] == 64


def test_matcher_uses_draw_range_for_multi_primitive_imb():
    first = _binding(0, [_variant()], first_index=0, index_count=6)
    second = _binding(
        1,
        [_variant(permutation="5", pair="6", vertex="7", pixel="8")],
        first_index=6,
        index_count=3,
    )
    report = match_imb_runtime_shader_variants(
        _target_set(first, second),
        _runtime(
            _snapshot(draw_index=0, first_index=0, index_count=6),
            _snapshot(
                draw_index=1,
                first_index=6,
                index_count=3,
                identity=_identity(
                    permutation="5",
                    pair="6",
                    vertex="7",
                    pixel="8",
                ),
            ),
        ),
    )

    assert report["ready"] is True
    assert report["summary"]["attributed_binding_count"] == 2
    assert [row["primitive_index"] for row in report["binding_results"]] == [
        0, 1,
    ]


def test_pixel_only_runtime_hit_is_not_attribution():
    variant = _variant(permutation="1", pair="2", vertex="3", pixel="4")
    report = match_imb_runtime_shader_variants(
        _target_set(_binding(0, [variant])),
        _runtime(
            _snapshot(
                identity=_identity(
                    permutation="9",
                    pair="8",
                    vertex="7",
                    pixel="4",
                )
            )
        ),
    )

    assert report["ready"] is False
    row = report["binding_results"][0]
    assert row["observed"] is True
    assert row["attributed"] is False
    assert row["best_score"] is None
    assert "only-prefilter-hash-matched" in row["blocking_reasons"]


def test_multiple_strong_variants_fail_closed():
    first = _variant(
        permutation="1",
        pair="2",
        vertex="3",
        pixel="4",
    )
    second = _variant(
        permutation="5",
        pair="2",
        vertex="3",
        pixel="4",
    )
    # Runtime pair bytes identify both variants equally; permutation identity
    # does not match either one.
    report = match_imb_runtime_shader_variants(
        _target_set(_binding(0, [first, second])),
        _runtime(
            _snapshot(
                identity=_identity(
                    permutation="9",
                    pair="2",
                    vertex="3",
                    pixel="4",
                )
            )
        ),
    )

    assert report["ready"] is False
    row = report["binding_results"][0]
    assert row["best_score"] == 90
    assert row["attributed"] is False
    assert "multiple-strong-variants" in row["blocking_reasons"]


def test_declaration_proof_is_required_even_when_gate_flag_is_ready():
    report = match_imb_runtime_shader_variants(
        _target_set(_binding(0, [_variant()])),
        _runtime(_snapshot(), descriptor_proof=False),
    )

    assert report["ready"] is False
    assert (
        "same-instance-gate-has-no-declaration-proven-draws"
        in report["blocking_reasons"]
    )


def test_wrong_runtime_resource_does_not_match_bindings():
    runtime = _runtime(_snapshot())
    runtime["meb_correlation"]["resource_identity"]["resource_sha256"] = _sha("0")
    report = match_imb_runtime_shader_variants(
        _target_set(_binding(0, [_variant()])),
        runtime,
    )

    assert report["ready"] is False
    assert "target-resource-not-found" in report["blocking_reasons"]
    assert report["summary"]["resource_binding_count"] == 0


def test_wrong_formats_are_rejected():
    try:
        match_imb_runtime_shader_variants(
            {"format": "wrong"},
            {"format": "SHIFT.D3D9RuntimeBindingEvidence/1"},
        )
    except ValueError as error:
        assert "IMBRuntimeShaderTargetSet" in str(error)
    else:
        raise AssertionError("wrong target format must be rejected")
