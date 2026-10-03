import struct

import pytest

import imb_material_constant_candidate_join as mod
from imb_material_constant_candidate_join import (
    AMBIGUITY_FORMAT,
    DRAW_FORMAT,
    FXO_FORMAT,
    FORMAT,
    build_material_constant_candidate_join,
    evaluate_material_constant_contract,
)


def _sha(char):
    return char * 64


def _runtime_variable(name, register, values, *, stage="pixel", complete=True):
    return stage, {
        "name": name,
        "register_index": register,
        "register_count": 1,
        "complete": complete,
        "registers": [
            {
                "register": register,
                "values": list(values) if values is not None else None,
                "last_write_event_index": 90,
                "last_write_frame": 7,
            }
        ],
    }


def _draw(event_index, variables):
    banks = {"vertex": [], "pixel": []}
    for stage, variable in variables:
        banks[stage].append(variable)
    return {
        "event_index": event_index,
        "frame": 7,
        "vertex_constants": {"variables": banks["vertex"]},
        "pixel_constants": {"variables": banks["pixel"]},
    }


def _candidate(label, *, bmt, vs="1", ps="2"):
    return {
        "content_group_sha256": _sha(label),
        "imb_sha256": _sha("a"),
        "imb_paths": [f"tracks/{label}.imb"],
        "archives": ["Silverstone.bff"],
        "bmt_sha256": _sha(bmt),
        "matched_vertex_shader_sha256": _sha(vs),
        "matched_pixel_shader_sha256": _sha(ps),
    }


def _ambiguity(candidates, *, event_index=100):
    return {
        "format": AMBIGUITY_FORMAT,
        "ambiguous_draws": [
            {
                "event_index": event_index,
                "frame": 7,
                "draw_evidence_sha256": _sha("d"),
                "candidate_set_sha256": _sha("e"),
                "ambiguity_class": "material-distinct-candidates",
                "candidates": candidates,
            }
        ],
    }


def _draw_report(draw):
    return {"format": DRAW_FORMAT, "draws": [draw]}


def _material(value):
    return {
        "shaderparams": [
            {
                "name": "dirtBasis",
                "type": "EPT_VEC4",
                "value": list(value),
            }
        ]
    }


def _materials(*rows):
    return {
        _sha(label): {
            "bmt_sha256": _sha(label),
            "parse_status": "parsed",
            "material": _material(value),
            "occurrences": [
                {
                    "archive": "Silverstone.bff",
                    "entry_path": f"materials/{label}.bmt",
                    "entry_index": 3,
                }
            ],
        }
        for label, value in rows
    }


def _fxo_pair():
    return {
        (_sha("1"), _sha("2")): [
            {
                "payload": b"verified-fxo",
                "payload_sha256": _sha("f"),
                "archive": "RENDER.bff",
                "entry_path": "render/shaders/test.fxo",
                "entry_index": 8,
                "vertex_program_offset": 0,
                "pixel_program_offset": 64,
                "variant_provenance_sha256": _sha("9"),
            }
        ]
    }


def _mock_uniform_linker(material, data, offsets):
    param = material["shaderparams"][0]
    return {
        "format": "SHIFT.MaterialUniformBinding/1",
        "bindings": [
            {
                "name": param["name"],
                "type": param["type"],
                "value": param["value"],
                "program_offset": offsets[-1],
                "stage": "pixel",
                "register_set": 2,
                "register_index": 5,
                "register_count": 1,
                "component_count": 4,
                "binding": "material-constant",
            }
        ],
        "optimized_out_or_unreflected": [],
        "unresolved": [],
    }


def test_f32_exact_witness_matches_json_float_spelling(monkeypatch):
    monkeypatch.setattr(mod, "link_material_uniforms", _mock_uniform_linker)
    expected = [0.1, 0.2, 0.3, 1.0]
    observed = [
        struct.unpack("<f", struct.pack("<f", value))[0]
        for value in expected
    ]
    report = evaluate_material_constant_contract(
        _material(expected),
        b"fxo",
        vertex_offset=0,
        pixel_offset=64,
        draw=_draw(100, [_runtime_variable("dirtBasis", 5, observed)]),
    )
    assert report["status"] == "exact-material-constant-match"
    assert report["matched_witness_count"] == 1
    assert report["witnesses"][0]["status"] == "exact-f32-match"
    assert report["witnesses"][0]["expected_f32_bits"] == report["witnesses"][0]["observed_f32_bits"]


def test_complete_mismatch_is_exact_contradiction(monkeypatch):
    monkeypatch.setattr(mod, "link_material_uniforms", _mock_uniform_linker)
    report = evaluate_material_constant_contract(
        _material([1.0, 2.0, 3.0, 4.0]),
        b"fxo",
        vertex_offset=0,
        pixel_offset=64,
        draw=_draw(100, [_runtime_variable("dirtBasis", 5, [1.0, 2.0, 99.0, 4.0])]),
    )
    assert report["status"] == "exact-material-constant-contradiction"
    assert report["contradicted_witness_count"] == 1


def test_incomplete_runtime_register_never_eliminates_candidate(monkeypatch):
    monkeypatch.setattr(mod, "link_material_uniforms", _mock_uniform_linker)
    stage, variable = _runtime_variable("dirtBasis", 5, None, complete=False)
    report = evaluate_material_constant_contract(
        _material([1.0, 2.0, 3.0, 4.0]),
        b"fxo",
        vertex_offset=0,
        pixel_offset=64,
        draw=_draw(100, [(stage, variable)]),
    )
    assert report["status"] == "insufficient-material-constant-evidence"
    assert report["insufficient_witness_count"] == 1


def test_unique_match_requires_every_other_candidate_to_be_contradicted(monkeypatch):
    monkeypatch.setattr(mod, "link_material_uniforms", _mock_uniform_linker)
    first = _candidate("b", bmt="b")
    second = _candidate("c", bmt="c")
    draw = _draw(100, [_runtime_variable("dirtBasis", 5, [1.0, 2.0, 3.0, 4.0])])
    report = build_material_constant_candidate_join(
        _ambiguity([first, second]),
        _draw_report(draw),
        materials_by_sha=_materials(
            ("b", [1.0, 2.0, 3.0, 4.0]),
            ("c", [9.0, 9.0, 9.0, 9.0]),
        ),
        fxo_pairs=_fxo_pair(),
    )
    row = report["draws"][0]
    assert report["format"] == FORMAT
    assert row["resolution_status"] == "single-candidate-by-exact-material-constants"
    assert row["selected_content_group_sha256"] == first["content_group_sha256"]
    assert report["summary"]["single_candidate_draw_count"] == 1


def test_one_match_plus_one_insufficient_remains_ambiguous(monkeypatch):
    monkeypatch.setattr(mod, "link_material_uniforms", _mock_uniform_linker)
    first = _candidate("b", bmt="b")
    second = _candidate("c", bmt="c")
    draw = _draw(100, [_runtime_variable("dirtBasis", 5, [1.0, 2.0, 3.0, 4.0])])
    report = build_material_constant_candidate_join(
        _ambiguity([first, second]),
        _draw_report(draw),
        materials_by_sha=_materials(("b", [1.0, 2.0, 3.0, 4.0])),
        fxo_pairs=_fxo_pair(),
    )
    row = report["draws"][0]
    assert row["resolution_status"] == "ambiguous-unexcluded-candidates"
    assert row["selected_content_group_sha256"] is None


def test_two_exact_matches_remain_ambiguous(monkeypatch):
    monkeypatch.setattr(mod, "link_material_uniforms", _mock_uniform_linker)
    candidates = [_candidate("b", bmt="b"), _candidate("c", bmt="c")]
    draw = _draw(100, [_runtime_variable("dirtBasis", 5, [1.0, 2.0, 3.0, 4.0])])
    report = build_material_constant_candidate_join(
        _ambiguity(candidates),
        _draw_report(draw),
        materials_by_sha=_materials(
            ("b", [1.0, 2.0, 3.0, 4.0]),
            ("c", [1.0, 2.0, 3.0, 4.0]),
        ),
        fxo_pairs=_fxo_pair(),
    )
    assert report["draws"][0]["resolution_status"] == "ambiguous-multiple-exact-material-constant-matches"


def test_all_candidates_contradicted_retains_original_set(monkeypatch):
    monkeypatch.setattr(mod, "link_material_uniforms", _mock_uniform_linker)
    candidates = [_candidate("b", bmt="b"), _candidate("c", bmt="c")]
    draw = _draw(100, [_runtime_variable("dirtBasis", 5, [1.0, 2.0, 3.0, 4.0])])
    report = build_material_constant_candidate_join(
        _ambiguity(candidates),
        _draw_report(draw),
        materials_by_sha=_materials(
            ("b", [7.0, 7.0, 7.0, 7.0]),
            ("c", [8.0, 8.0, 8.0, 8.0]),
        ),
        fxo_pairs=_fxo_pair(),
    )
    row = report["draws"][0]
    assert row["resolution_status"] == "material-constant-conflict-no-survivor"
    assert row["selected_content_group_sha256"] is None
    assert "all-candidates-contradicted-retain-original-set" in row["blocking_reasons"]


def test_missing_draw_local_event_is_not_capture_reinterpretation(monkeypatch):
    monkeypatch.setattr(mod, "link_material_uniforms", _mock_uniform_linker)
    report = build_material_constant_candidate_join(
        _ambiguity([_candidate("b", bmt="b")], event_index=100),
        {"format": DRAW_FORMAT, "draws": []},
        materials_by_sha=_materials(("b", [1.0, 2.0, 3.0, 4.0])),
        fxo_pairs=_fxo_pair(),
    )
    row = report["draws"][0]
    assert row["resolution_status"] == "draw-local-evidence-missing"
    assert report["boundary"]["capture_requirement"].startswith("none")


def test_formats_fail_closed():
    with pytest.raises(ValueError, match="ambiguity report"):
        build_material_constant_candidate_join(
            {"format": "wrong"},
            {"format": DRAW_FORMAT},
            materials_by_sha={},
            fxo_pairs={},
        )
    with pytest.raises(ValueError, match="draw-local report"):
        build_material_constant_candidate_join(
            {"format": AMBIGUITY_FORMAT},
            {"format": "wrong"},
            materials_by_sha={},
            fxo_pairs={},
        )


def test_fxo_provenance_format_is_explicit_constant():
    assert FXO_FORMAT == "SHIFT.IMBFXOPairProvenance/1"
