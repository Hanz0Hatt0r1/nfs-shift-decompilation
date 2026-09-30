from imb_runtime_shader_admission import (
    FORMAT,
    build_imb_runtime_shader_admission,
)


def _sha(char):
    return char * 64


def _variant(*, permutation="1", pair="2", vertex="3", pixel="4", file="a.fxo"):
    return {
        "permutation_identity_sha256": _sha(permutation),
        "pair_byte_sha256": _sha(pair),
        "vertex_byte_sha256": _sha(vertex),
        "pixel_byte_sha256": _sha(pixel),
        "candidate_file": file,
        "candidate_program_offset": 128,
        "exact": True,
    }


def _binding(index=0, *, variants=None):
    variants = variants or [_variant()]
    return {
        "binding_index": index,
        "archive": "Silverstone_Era3_GrandPrix.bff",
        "imb_path": "tracks/silverstone/object.imb",
        "imb_sha256": _sha("f"),
        "primitive_index": 0,
        "draw_range": {
            "first_index": 0,
            "index_count": 6,
            "primitive_count": 2,
        },
        "same_instance_match_ready": True,
        "material_reference": "materials/test.mtx",
        "bmt": "materials/test.bmt",
        "bmt_sha256": _sha("e"),
        "shader": "render/shaders/basic_instanced.fx",
        "shader_family": "basicinstanced",
        "targets": [{
            "identity_kind": "pixel",
            "identity_value": _sha("4"),
            "candidate_variants": variants,
        }],
    }


def _target_set(*bindings):
    return {
        "format": "SHIFT.IMBRuntimeShaderTargetSet/1",
        "binding_targets": list(bindings),
    }


def _selected(*, permutation="1", pair="2", vertex="3", pixel="4", score=100):
    return {
        "score": score,
        "evidence": ["permutation_identity_sha256"],
        "variant_key": ["permutation", _sha(permutation)],
        "permutation_identity_sha256": _sha(permutation),
        "pair_byte_sha256": _sha(pair),
        "vertex_byte_sha256": _sha(vertex),
        "pixel_byte_sha256": _sha(pixel),
        "candidate_file": "a.fxo",
        "candidate_program_offset": 128,
    }


def _result(index=0, *, attributed=True, selected=None):
    return {
        "binding_index": index,
        "primitive_index": 0,
        "imb_path": "tracks/silverstone/object.imb",
        "imb_sha256": _sha("f"),
        "draw_range": {
            "first_index": 0,
            "index_count": 6,
            "primitive_count": 2,
        },
        "attributed": attributed,
        "selected_variant": selected if selected is not None else _selected(),
    }


def _match(*results, resource_path="tracks/silverstone/object.imb", resource_sha=None):
    return {
        "format": "SHIFT.IMBRuntimeShaderVariantMatch/1",
        "target_resource": {
            "resource_path": resource_path,
            "resource_sha256": resource_sha or _sha("f"),
        },
        "binding_results": list(results),
    }


def test_admits_exact_phase572_variant_back_to_static_binding():
    report = build_imb_runtime_shader_admission(
        _target_set(_binding()),
        [_match(_result())],
    )

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["status"] == "ready"
    assert report["summary"]["admitted_binding_count"] == 1
    row = report["admitted_bindings"][0]
    assert row["binding_index"] == 0
    assert row["shader_selection_admitted"] is True
    assert row["render_admission"] is False
    assert row["selected_variant_key"] == ["permutation", _sha("1")]
    assert row["equivalent_static_locations"] == [
        {"file": "a.fxo", "program_offset": 128}
    ]


def test_preserves_content_equivalent_static_locations():
    first = _variant(file="a.fxo")
    second = _variant(file="copy.fxo")
    report = build_imb_runtime_shader_admission(
        _target_set(_binding(variants=[first, second])),
        [_match(_result())],
    )

    assert report["ready"] is True
    assert report["admitted_bindings"][0]["equivalent_static_locations"] == [
        {"file": "a.fxo", "program_offset": 128},
        {"file": "copy.fxo", "program_offset": 128},
    ]


def test_runtime_not_attributed_row_is_rejected_not_promoted():
    report = build_imb_runtime_shader_admission(
        _target_set(_binding()),
        [_match(_result(attributed=False))],
    )

    assert report["ready"] is False
    assert report["status"] == "not-admitted"
    assert report["summary"]["admitted_binding_count"] == 0
    assert "runtime-result-not-attributed" in (
        report["rejected_bindings"][0]["blocking_reasons"]
    )


def test_weak_pixel_only_selection_is_rejected():
    selected = _selected(score=40)
    report = build_imb_runtime_shader_admission(
        _target_set(_binding()),
        [_match(_result(selected=selected))],
    )

    assert report["ready"] is False
    assert "selected-variant-not-strong" in (
        report["rejected_bindings"][0]["blocking_reasons"]
    )


def test_runtime_resource_identity_must_match_target_binding():
    report = build_imb_runtime_shader_admission(
        _target_set(_binding()),
        [_match(_result(), resource_sha=_sha("0"))],
    )

    assert report["ready"] is False
    assert "runtime-resource-sha256-mismatch" in (
        report["rejected_bindings"][0]["blocking_reasons"]
    )


def test_selected_variant_must_exist_in_preserved_static_targets():
    selected = _selected(permutation="9", pair="8", vertex="7", pixel="6")
    report = build_imb_runtime_shader_admission(
        _target_set(_binding()),
        [_match(_result(selected=selected))],
    )

    assert report["ready"] is False
    assert "selected-variant-not-in-static-target-set" in (
        report["rejected_bindings"][0]["blocking_reasons"]
    )


def test_partial_match_report_admits_only_proven_rows():
    report = build_imb_runtime_shader_admission(
        _target_set(_binding(0), _binding(1)),
        [_match(_result(0), _result(1, attributed=False))],
    )

    assert report["status"] == "partial"
    assert report["ready"] is False
    assert report["summary"]["admitted_binding_count"] == 1
    assert report["summary"]["rejected_binding_count"] == 1


def test_wrong_match_format_blocks_report():
    report = build_imb_runtime_shader_admission(
        _target_set(_binding()),
        [{"format": "SHIFT.Other/1"}],
    )

    assert report["status"] == "blocked"
    assert report["ready"] is False
    assert "match-0:format-invalid" in report["blocking_reasons"]
