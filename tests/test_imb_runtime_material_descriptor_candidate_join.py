import os
from pathlib import Path
import subprocess
import sys

import pytest

from imb_runtime_material_descriptor_candidate_join import (
    FORMAT,
    GEOMETRY_FORMAT,
    RUNTIME_FORMAT,
    build_runtime_material_descriptor_candidate_join,
)


PS = "1" * 64
RESOURCE = "2" * 64
GEOMETRY = "3" * 64
GROUP_A = "4" * 64
GROUP_B = "5" * 64
BMT_A = "6" * 64
BMT_B = "7" * 64
DXT1 = 827611204
DXT5 = 894720068


def _runtime(*, width=256, height=128, fmt=DXT5):
    return {
        "format": RUNTIME_FORMAT,
        "resource_shape_signatures": [{
            "signature_sha256": RESOURCE,
            "signature": {
                "pixel_shader_sha256": PS,
                "texture_stages": [
                    {
                        "stage": 0,
                        "resource_type_name": "texture2d",
                        "width": 2048,
                        "height": 8192,
                        "format": 80,
                        "level_count": 1,
                        "pool": 0,
                        "usage": 2,
                    },
                    {
                        "stage": 1,
                        "resource_type_name": "texture2d",
                        "width": width,
                        "height": height,
                        "format": fmt,
                        "level_count": 9,
                        "pool": 1,
                        "usage": 0,
                    },
                ],
            },
            "draw_count": 11,
            "first_frame": 4287,
            "last_frame": 4308,
            "families": ["crowdgeninstancedbillboard"],
        }],
    }


def _group(group_sha, bmt_sha, path):
    return {
        "content_group_sha256": group_sha,
        "bmt_sha256": bmt_sha,
        "imb_sha256": "8" * 64,
        "matched_pixel_shader_sha256": PS,
        "archives": ["A.bff"],
        "imb_paths": [path],
        "binding_indices": [1],
        "draw_range": {
            "first_index": 0,
            "index_count": 6,
            "primitive_count": 2,
        },
    }


def _geometry(groups):
    return {
        "format": GEOMETRY_FORMAT,
        "geometry_shapes": [{
            "geometry_shape_sha256": GEOMETRY,
            "pipeline_signature_sha256": "9" * 64,
            "resource_shape_sha256s": [RESOURCE],
            "candidate_content_groups": groups,
        }],
    }


def _occurrence(
    bmt_sha,
    *,
    texture,
    width,
    height,
    fmt=DXT5,
):
    return {
        "archive": "A.bff",
        "bmt_path": f"materials/{bmt_sha[:4]}.bmt",
        "bmt_sha256": bmt_sha,
        "material_name": "test",
        "shader": "render/shaders/test.fx",
        "params": {
            "diffuseTexture": {
                "name": "diffuseTexture",
                "value": texture,
            }
        },
        "fx_samplers": {
            "diffuseMap": {
                "sampler": "diffuseMap",
                "texture_parameter": "diffuseTexture",
            }
        },
        "texture_descriptors": {
            texture.lower(): {
                "resource_type_name": "texture2d",
                "width": width,
                "height": height,
                "format": fmt,
                "level_count": 9,
            }
        },
    }


def _reflection():
    return {
        PS: {
            "status": "consistent",
            "variant_count": 1,
            "samplers": [
                {
                    "name": "shadowMap",
                    "register": 0,
                    "count": 1,
                },
                {
                    "name": "diffuseMap",
                    "register": 1,
                    "count": 1,
                },
            ],
        }
    }


def test_material_descriptor_gate_reduces_two_content_groups_to_one():
    group_a = _group(GROUP_A, BMT_A, "characters/a.imb")
    group_b = _group(GROUP_B, BMT_B, "characters/b.imb")
    occurrences = {
        BMT_A: [
            _occurrence(
                BMT_A,
                texture="textures/a.dds",
                width=256,
                height=128,
            )
        ],
        BMT_B: [
            _occurrence(
                BMT_B,
                texture="textures/b.dds",
                width=256,
                height=256,
            )
        ],
    }

    report = build_runtime_material_descriptor_candidate_join(
        _runtime(),
        _geometry([group_a, group_b]),
        material_occurrences=occurrences,
        pixel_reflections=_reflection(),
    )

    row = report["resource_shapes"][0]
    assert report["format"] == FORMAT
    assert row["base_geometry_content_group_count"] == 2
    assert row["material_descriptor_gate_status"] == "reduced"
    assert row["candidate_content_status"] == "single-content-candidate"
    assert row["candidate_content_group_sha256s"] == [GROUP_A]
    assert (
        row["candidate_content_groups"][0][
            "material_descriptor_match"
        ]
        is True
    )
    assert report["summary"][
        "material_descriptor_gate_applied_resource_shape_count"
    ] == 1
    assert report["summary"][
        "material_descriptor_gate_reduced_resource_shape_count"
    ] == 1
    assert report["summary"][
        "single_content_candidate_draw_count"
    ] == 11


def test_external_reflected_sampler_is_not_required_material_evidence():
    group = _group(GROUP_A, BMT_A, "characters/a.imb")
    occurrence = _occurrence(
        BMT_A,
        texture="textures/a.dds",
        width=256,
        height=128,
    )

    report = build_runtime_material_descriptor_candidate_join(
        _runtime(),
        _geometry([group]),
        material_occurrences={BMT_A: [occurrence]},
        pixel_reflections=_reflection(),
    )

    row = report["resource_shapes"][0]
    assert row["material_descriptor_gate_status"] == "matched-all"
    evidence = row["candidate_content_groups"][0][
        "material_occurrences"
    ][0]
    assert evidence["runtime_descriptor_match"] is True
    assert [
        binding["register"]
        for binding in evidence["material_sampler_bindings"]
    ] == [1]
    assert [
        binding["sampler"]
        for binding in evidence["material_sampler_bindings"]
    ] == ["diffuseMap"]


def test_zero_material_descriptor_matches_falls_back_without_rejection():
    group_a = _group(GROUP_A, BMT_A, "characters/a.imb")
    group_b = _group(GROUP_B, BMT_B, "characters/b.imb")
    occurrences = {
        BMT_A: [
            _occurrence(
                BMT_A,
                texture="textures/a.dds",
                width=256,
                height=256,
            )
        ],
        BMT_B: [
            _occurrence(
                BMT_B,
                texture="textures/b.dds",
                width=512,
                height=512,
            )
        ],
    }

    report = build_runtime_material_descriptor_candidate_join(
        _runtime(width=128, height=128),
        _geometry([group_a, group_b]),
        material_occurrences=occurrences,
        pixel_reflections=_reflection(),
    )

    row = report["resource_shapes"][0]
    assert (
        row["material_descriptor_gate_status"]
        == "no-exact-match-fallback"
    )
    assert row["candidate_content_status"] == "ambiguous-content-candidates"
    assert row["candidate_content_group_sha256s"] == [
        GROUP_A,
        GROUP_B,
    ]
    assert report["summary"][
        "material_descriptor_gate_fallback_resource_shape_count"
    ] == 1


def test_same_bmt_lod_pair_remains_ambiguous_when_material_matches():
    group_a = _group(GROUP_A, BMT_A, "characters/man_loda.imb")
    group_b = _group(GROUP_B, BMT_A, "characters/man_lodb.imb")
    occurrence = _occurrence(
        BMT_A,
        texture="textures/man.dds",
        width=256,
        height=128,
    )

    report = build_runtime_material_descriptor_candidate_join(
        _runtime(),
        _geometry([group_a, group_b]),
        material_occurrences={BMT_A: [occurrence]},
        pixel_reflections=_reflection(),
    )

    row = report["resource_shapes"][0]
    assert row["material_descriptor_gate_status"] == "matched-all"
    assert row["candidate_content_status"] == "ambiguous-content-candidates"
    assert row["candidate_content_group_sha256s"] == [
        GROUP_A,
        GROUP_B,
    ]


def test_material_descriptor_join_rejects_wrong_contracts():
    with pytest.raises(ValueError, match="runtime catalog"):
        build_runtime_material_descriptor_candidate_join(
            {"format": "wrong"},
            {"format": GEOMETRY_FORMAT},
            material_occurrences={},
            pixel_reflections={},
        )

    with pytest.raises(ValueError, match="geometry join"):
        build_runtime_material_descriptor_candidate_join(
            {"format": RUNTIME_FORMAT},
            {"format": "wrong"},
            material_occurrences={},
            pixel_reflections={},
        )


def test_material_descriptor_join_cli_imports_without_pythonpath():
    repo_root = Path(__file__).resolve().parents[1]
    script = (
        repo_root
        / "src"
        / "scene"
        / "imb_runtime_material_descriptor_candidate_join.py"
    )
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)

    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "runtime_catalog" in result.stdout
    assert "geometry_join" in result.stdout
    assert "source_archive" in result.stdout
    assert "render_archive" in result.stdout
