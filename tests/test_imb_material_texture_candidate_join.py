import struct

import pytest

import imb_material_texture_candidate_join as mod
from imb_material_texture_candidate_join import (
    CONSTANT_FORMAT,
    DRAW_FORMAT,
    FORMAT,
    _dds_descriptor,
    build_material_texture_candidate_join,
    compare_dds_to_runtime,
)


def _sha(char):
    return char * 64


def _dds(*, width=64, height=32, fourcc=b"DXT5", mipmaps=4, cube=False):
    data = bytearray(128)
    data[:4] = b"DDS "
    struct.pack_into("<I", data, 4, 124)
    struct.pack_into("<I", data, 12, height)
    struct.pack_into("<I", data, 16, width)
    struct.pack_into("<I", data, 28, mipmaps)
    struct.pack_into("<I", data, 76, 32)
    struct.pack_into("<I", data, 84, int.from_bytes(fourcc, "little"))
    struct.pack_into("<I", data, 112, 0x200 if cube else 0)
    return bytes(data)


def _static(path="tracks/a.dds", sha="a", *, width=64, height=32, fmt=None, levels=4):
    return {
        "resource_path": path,
        "resource_sha256": _sha(sha),
        "descriptor": {
            "resource_type_name": "texture2d",
            "width": width,
            "height": height,
            "format": int.from_bytes(b"DXT5", "little") if fmt is None else fmt,
            "level_count": levels,
        },
    }


def _runtime(*, path=None, sha=None, width=64, height=32, fmt=None, levels=4):
    return {
        "stage": 1,
        "sampler_name": "diffuseMap",
        "portable_resource_identity": {
            "resource_path": path,
            "resource_sha256": _sha(sha) if sha else None,
        },
        "descriptor": {
            "resource_type_name": "texture2d",
            "width": width,
            "height": height,
            "format": int.from_bytes(b"DXT5", "little") if fmt is None else fmt,
            "level_count": levels,
        },
    }


def _candidate(label, *, status="insufficient-material-constant-evidence"):
    return {
        "content_group_sha256": _sha(label),
        "bmt_sha256": _sha(label),
        "status": status,
        "shader_pair": {
            "vertex_shader_sha256": _sha("1"),
            "pixel_shader_sha256": _sha("2"),
        },
    }


def _constant_report(candidates, *, resolution="ambiguous-unexcluded-candidates"):
    return {
        "format": CONSTANT_FORMAT,
        "draws": [{
            "event_index": 100,
            "frame": 7,
            "input_candidate_count": len(candidates),
            "resolution_status": resolution,
            "candidate_results": candidates,
        }],
    }


def _draw_report():
    return {"format": DRAW_FORMAT, "draws": [{"event_index": 100, "frame": 7}]}


def _build(report):
    return build_material_texture_candidate_join(
        report,
        _draw_report(),
        materials_by_sha={},
        fx_sources_by_path={},
        dds_by_path={},
        fxo_pairs={},
    )


def test_dds_descriptor_preserves_d3d9_fourcc_and_shape():
    row = _dds_descriptor(_dds(width=128, height=64, fourcc=b"DXT3", mipmaps=6))
    assert row["resource_type_name"] == "texture2d"
    assert row["width"] == 128
    assert row["height"] == 64
    assert row["level_count"] == 6
    assert row["format"] == int.from_bytes(b"DXT3", "little")


def test_portable_path_and_sha_are_exact_positive_identity():
    result = compare_dds_to_runtime(
        _static(path="tracks/a.dds", sha="a"),
        _runtime(path="TRACKS\\A.DDS", sha="a"),
    )
    assert result["status"] == "exact-resource-identity-match"
    assert result["confidence"] == "exact-runtime-path-sha"


def test_portable_sha_mismatch_is_exact_contradiction():
    result = compare_dds_to_runtime(
        _static(path="tracks/a.dds", sha="a"),
        _runtime(path="tracks/a.dds", sha="b"),
    )
    assert result["status"] == "exact-resource-identity-contradiction"
    assert result["reason"] == "resource-sha256-mismatch"


def test_dds_header_descriptor_mismatch_is_exact_contradiction():
    result = compare_dds_to_runtime(
        _static(width=64),
        _runtime(width=128),
    )
    assert result["status"] == "exact-resource-descriptor-contradiction"
    assert result["mismatches"][0]["field"] == "width"


def test_descriptor_equality_is_not_positive_identity():
    result = compare_dds_to_runtime(_static(), _runtime())
    assert result["status"] == "descriptor-compatible-not-identity"
    assert result["confidence"] == "descriptor-only"


def test_unique_exact_texture_match_requires_all_other_candidates_contradicted(monkeypatch):
    first = _candidate("a")
    second = _candidate("b")

    def evaluate(candidate, draw, **kwargs):
        status = (
            "exact-material-texture-match"
            if candidate["content_group_sha256"] == first["content_group_sha256"]
            else "exact-material-texture-contradiction"
        )
        return {**candidate, "status": status}

    monkeypatch.setattr(mod, "evaluate_candidate", evaluate)
    result = _build(_constant_report([first, second]))
    row = result["draws"][0]
    assert result["format"] == FORMAT
    assert row["resolution_status"] == "single-candidate-by-exact-material-textures"
    assert row["selected_content_group_sha256"] == first["content_group_sha256"]
    assert result["summary"]["single_candidate_draw_count"] == 1


def test_exact_match_plus_insufficient_remains_ambiguous(monkeypatch):
    first = _candidate("a")
    second = _candidate("b")

    def evaluate(candidate, draw, **kwargs):
        status = (
            "exact-material-texture-match"
            if candidate["content_group_sha256"] == first["content_group_sha256"]
            else "insufficient-material-texture-evidence"
        )
        return {**candidate, "status": status}

    monkeypatch.setattr(mod, "evaluate_candidate", evaluate)
    row = _build(_constant_report([first, second]))["draws"][0]
    assert row["resolution_status"] == "ambiguous-unexcluded-texture-candidates"
    assert row["selected_content_group_sha256"] is None


def test_descriptor_contradictions_may_leave_single_unproven_survivor(monkeypatch):
    first = _candidate("a")
    second = _candidate("b")

    def evaluate(candidate, draw, **kwargs):
        status = (
            "insufficient-material-texture-evidence"
            if candidate["content_group_sha256"] == first["content_group_sha256"]
            else "exact-material-texture-contradiction"
        )
        return {**candidate, "status": status}

    monkeypatch.setattr(mod, "evaluate_candidate", evaluate)
    row = _build(_constant_report([first, second]))["draws"][0]
    assert row["resolution_status"] == "single-survivor-by-texture-contradiction-unproven"
    assert row["selected_content_group_sha256"] is None


def test_phase620_constant_contradictions_are_not_reintroduced(monkeypatch):
    eliminated = _candidate("a", status="exact-material-constant-contradiction")
    survivor = _candidate("b")
    seen = []

    def evaluate(candidate, draw, **kwargs):
        seen.append(candidate["content_group_sha256"])
        return {**candidate, "status": "insufficient-material-texture-evidence"}

    monkeypatch.setattr(mod, "evaluate_candidate", evaluate)
    result = _build(_constant_report([eliminated, survivor]))
    assert seen == [survivor["content_group_sha256"]]
    assert result["draws"][0]["constant_survivor_count"] == 1


def test_phase620_all_contradicted_conflict_retains_original_set(monkeypatch):
    candidates = [
        _candidate("a", status="exact-material-constant-contradiction"),
        _candidate("b", status="exact-material-constant-contradiction"),
    ]
    seen = []

    def evaluate(candidate, draw, **kwargs):
        seen.append(candidate["content_group_sha256"])
        return {**candidate, "status": "insufficient-material-texture-evidence"}

    monkeypatch.setattr(mod, "evaluate_candidate", evaluate)
    _build(_constant_report(candidates, resolution="material-constant-conflict-no-survivor"))
    assert sorted(seen) == sorted(row["content_group_sha256"] for row in candidates)


def test_already_resolved_constant_draw_is_skipped():
    report = _constant_report(
        [_candidate("a", status="exact-material-constant-match")],
        resolution="single-candidate-by-exact-material-constants",
    )
    result = _build(report)
    assert result["status"] == "no-unresolved-material-candidates"
    assert result["draws"] == []


def test_formats_fail_closed():
    with pytest.raises(ValueError, match="constant report"):
        build_material_texture_candidate_join(
            {"format": "wrong"},
            _draw_report(),
            materials_by_sha={},
            fx_sources_by_path={},
            dds_by_path={},
            fxo_pairs={},
        )
    with pytest.raises(ValueError, match="draw-local report"):
        build_material_texture_candidate_join(
            {"format": CONSTANT_FORMAT},
            {"format": "wrong"},
            materials_by_sha={},
            fx_sources_by_path={},
            dds_by_path={},
            fxo_pairs={},
        )
