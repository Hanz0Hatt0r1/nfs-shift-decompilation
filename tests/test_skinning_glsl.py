import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from skinned_draw import build_skinned_draw_contract
from skinning_glsl import (
    build_gles31_skinning_contract,
    build_gles31_skinning_test_shader,
    gles31_skinning_functions,
    palette_uniform_bytes,
)


def _packet():
    return {
        "format": "SHIFT.SkinnedDraw/1",
        "ready": True,
        "blocking_reasons": [],
        "skinning": {
            "influences": 4,
            "weights": {
                "format": "FLOAT32x4",
                "target_location": 1,
            },
            "indices": {
                "format": "UINT8x4",
                "target_location": 2,
            },
        },
        "bind_skeleton": {
            "format": "SHIFT.BindSkeleton/1",
            "bone_count": 2,
            "coverage": 1.0,
            "palette": {
                "format": "SHIFT.BonePalette/1",
                "bone_count": 2,
                "matrices_3x4": [
                    [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0],
                    [1, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0],
                ],
            },
        },
        "skin_pose": {
            "format": "SHIFT.SkinPose/1",
            "matrix_space": "skinning",
            "bone_count": 2,
            "matrices_3x4": [
                [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0],
                [1, 0, 0, 1, 0, 1, 0, 2, 0, 0, 1, 3],
            ],
            "source": "synthetic",
            "frame": 0,
        },
        "mesh": {
            "vertex_layout": {
                "format": "SHIFT.VertexLayout/1",
                "buffer_stride": 32,
                "attributes": [
                    {
                        "property_id": "200",
                        "location": 0,
                        "android": "FLOAT32x3",
                        "components": 3,
                        "normalized": False,
                    },
                    {
                        "property_id": "310",
                        "location": 1,
                        "android": "FLOAT32x4",
                        "components": 4,
                        "normalized": False,
                    },
                    {
                        "property_id": "580",
                        "location": 2,
                        "android": "UINT8x4",
                        "components": 4,
                        "normalized": False,
                    },
                ],
            },
        },
    }


def test_gles31_contract_preserves_integer_blend_indices():
    result = build_gles31_skinning_contract(_packet())
    assert result["api"] == "OpenGL ES 3.1"
    assert result["attributes"]["blendweight0"]["glsl_type"] == "vec4"
    assert result["attributes"]["blendindices0"]["glsl_type"] == "uvec4"
    assert result["attributes"]["blendindices0"]["integer_attribute"] is True
    assert result["bone_binding"] == 15


def test_skinning_glsl_uses_four_weight_matrix_blends():
    source = gles31_skinning_functions()
    assert source.count("u_bones[indices.") == 8
    assert "weights.x" in source
    assert "weights.y" in source
    assert "weights.z" in source
    assert "weights.w" in source


def test_palette_std140_size_is_four_mat4_slots():
    assert palette_uniform_bytes(0) == 0
    assert palette_uniform_bytes(2) == 128
    assert palette_uniform_bytes(128) == 8192


@pytest.mark.parametrize("binding,max_bones", [(15, 128), (3, 64)])
def test_minimal_gles31_skinning_shader_compiles(binding, max_bones, tmp_path):
    validator = shutil.which("glslangValidator")
    if validator is None:
        pytest.skip("glslangValidator is not installed")

    path = tmp_path / "skinning.vert"
    path.write_text(
        build_gles31_skinning_test_shader(
            bone_binding=binding,
            max_bones=max_bones,
        ),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [validator, "-S", "vert", str(path)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_gles31_contract_rejects_oversized_palette():
    packet = _packet()
    packet["skin_pose"]["bone_count"] = 129
    packet["skin_pose"]["matrices_3x4"] = (
        [[1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0]] * 129
    )
    packet["bind_skeleton"]["bone_count"] = 129
    packet["bind_skeleton"]["palette"]["bone_count"] = 129
    with pytest.raises(ValueError, match="exceeds GLES shader limit"):
        build_gles31_skinning_contract(packet, max_bones=128)


def test_real_skinned_draw_contract_can_feed_gles31_contract():
    packet = {
        "shader_selection": {"status": "unique"},
        "bind_skeleton": {
            "format": "SHIFT.BindSkeleton/1",
            "coverage": 1.0,
            "bone_count": 1,
            "links": [{
                "index": 0,
                "name": "root",
                "local_matrix_3x4": [
                    1, 0, 0, 0,
                    0, 1, 0, 0,
                    0, 0, 1, 0,
                ],
            }],
            "animation_payload": {"decoded": False, "sha256": "opaque"},
        },
        "skin_pose": {
            "format": "SHIFT.SkinPose/1",
            "matrix_space": "skinning",
            "bone_count": 1,
            "matrices_3x4": [
                [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0],
            ],
            "source": "synthetic",
            "frame": 0,
        },
        "mesh": {
            "vertex_layout": {
                "format": "SHIFT.VertexLayout/1",
                "buffer_stride": 32,
                "attributes": [
                    {
                        "property_id": "200",
                        "location": 0,
                        "android": "FLOAT32x3",
                        "components": 3,
                        "normalized": False,
                    },
                    {
                        "property_id": "310",
                        "location": 1,
                        "android": "FLOAT32x4",
                        "components": 4,
                        "normalized": False,
                    },
                    {
                        "property_id": "580",
                        "location": 2,
                        "android": "UINT8x4",
                        "components": 4,
                        "normalized": False,
                    },
                ],
            },
            "skinning": {
                "has_weights": True,
                "has_indices": True,
                "skinned": True,
                "valid": True,
            },
        },
        "submeshes": [{
            "material": {
                "shader_selection": {
                    "status": "unique",
                    "shader_pair": {
                        "selection_status": "unique",
                        "interface": {"valid": True},
                        "vertex_format": {"valid": True},
                    },
                    "linked_shader_pair": {
                        "format": "SHIFT.LinkedShaderPair/1",
                    },
                },
                "textures": [],
            }
        }],
    }
    draw = build_skinned_draw_contract(packet)
    assert draw["ready"] is True
    draw["bind_skeleton"]["palette"]["matrix_layout"] = "3x4-row-major"
    contract = build_gles31_skinning_contract(draw)
    assert contract["bone_count"] == 1
    assert contract["attributes"]["position"]["location"] == 0
    assert contract["attributes"]["blendindices0"]["location"] == 2


def test_gles31_contract_uses_vertex_layout_position_location():
    packet = _packet()
    attrs = packet["mesh"]["vertex_layout"]["attributes"]
    attrs[0]["location"] = 7
    contract = build_gles31_skinning_contract(packet)
    assert contract["attributes"]["position"]["location"] == 7
    assert contract["attributes"]["blendweight0"]["location"] == 1
    assert contract["attributes"]["blendindices0"]["location"] == 2


def test_gles31_contract_rejects_stale_skin_summary_location():
    packet = _packet()
    packet["mesh"]["vertex_layout"]["attributes"][1]["location"] = 4
    with pytest.raises(ValueError, match="conflicts with SHIFT.VertexLayout"):
        build_gles31_skinning_contract(packet)


def _skinned_render_command():
    return {
        "format": "SHIFT.RenderCommand/1",
        "ready": True,
        "draw_kind": "skinned",
        "blocking_reasons": [],
        "mesh": {
            "attributes": [
                {"property_id": "200", "location": 4},
                {"property_id": "310", "location": 5},
                {"property_id": "580", "location": 6},
            ],
        },
        "skinning": {
            "format": "SHIFT.Skinning/1",
            "influences": 4,
            "weights": {
                "property_id": "310",
                "format": "FLOAT32x4",
                "target_location": 5,
            },
            "indices": {
                "property_id": "580",
                "format": "UINT8x4",
                "target_location": 6,
            },
            "bind_skeleton": {
                "format": "SHIFT.BonePalette/1",
                "bone_count": 2,
                "matrix_layout": "3x4-row-major",
                "matrix_space": "local-bind",
                "local_matrices_3x4": [
                    [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0],
                    [1, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0],
                ],
            },
            "skin_pose": {
                "format": "SHIFT.SkinPose/1",
                "matrix_space": "skinning",
                "matrix_layout": "3x4-row-major",
                "bone_count": 2,
                "matrices_3x4": [
                    [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0],
                    [1, 0, 0, 2, 0, 1, 0, 3, 0, 0, 1, 4],
                ],
                "source": "synthetic",
                "frame": 12,
            },
        },
    }


def test_gles31_contract_can_be_built_directly_from_render_command():
    from skinning_glsl import build_gles31_skinning_contract_from_render_command

    result = build_gles31_skinning_contract_from_render_command(
        _skinned_render_command(),
        bone_binding=7,
        max_bones=64,
    )
    assert result["format"] == "SHIFT.GLES31Skinning/1"
    assert result["bone_binding"] == 7
    assert result["bone_count"] == 2
    assert result["attributes"]["position"]["location"] == 4
    assert result["attributes"]["blendweight0"]["location"] == 5
    assert result["attributes"]["blendindices0"]["location"] == 6
    assert result["skin_pose"]["frame"] == 12


def test_gles31_contract_from_render_command_rejects_static_command():
    from skinning_glsl import build_gles31_skinning_contract_from_render_command

    command = _skinned_render_command()
    command["draw_kind"] = "static"
    with pytest.raises(ValueError, match="not a skinned draw"):
        build_gles31_skinning_contract_from_render_command(command)


def test_gles31_contract_from_render_command_rejects_not_ready_command():
    from skinning_glsl import build_gles31_skinning_contract_from_render_command

    command = _skinned_render_command()
    command["ready"] = False
    command["blocking_reasons"] = ["skinning:skin-pose-palette-incomplete"]
    with pytest.raises(ValueError, match="skin-pose-palette-incomplete"):
        build_gles31_skinning_contract_from_render_command(command)


def test_render_command_gles31_skinning_parity_accepts_matching_contract():
    from skinning_glsl import (
        build_gles31_skinning_contract_from_render_command,
        validate_gles31_skinning_contract_parity,
    )

    command = _skinned_render_command()
    contract = build_gles31_skinning_contract_from_render_command(command)
    parity = validate_gles31_skinning_contract_parity(command, contract)
    assert parity["format"] == "SHIFT.GLES31SkinningParity/1"
    assert parity["valid"] is True, parity["blocking_reasons"]
    assert parity["blocking_reasons"] == []
    assert all(row["status"] == "match" for row in parity["checks"])


def test_render_command_gles31_skinning_parity_detects_attribute_location_mismatch():
    from skinning_glsl import (
        build_gles31_skinning_contract_from_render_command,
        validate_gles31_skinning_contract_parity,
    )

    command = _skinned_render_command()
    contract = build_gles31_skinning_contract_from_render_command(command)
    contract["attributes"]["blendindices0"]["location"] = 99
    parity = validate_gles31_skinning_contract_parity(command, contract)
    assert parity["valid"] is False
    assert "parity:blendindices0-location-mismatch" in parity["blocking_reasons"]


def test_render_command_gles31_skinning_parity_detects_skin_pose_matrix_mismatch():
    from skinning_glsl import (
        build_gles31_skinning_contract_from_render_command,
        validate_gles31_skinning_contract_parity,
    )

    command = _skinned_render_command()
    contract = build_gles31_skinning_contract_from_render_command(command)
    contract["skin_pose"]["matrices_sha256"] = "deadbeef"
    parity = validate_gles31_skinning_contract_parity(command, contract)
    assert parity["valid"] is False
    assert "parity:skin-pose-matrices-mismatch" in parity["blocking_reasons"]


def test_render_command_gles31_skinning_parity_propagates_source_blocker():
    from skinning_glsl import (
        build_gles31_skinning_contract_from_render_command,
        validate_gles31_skinning_contract_parity,
    )

    command = _skinned_render_command()
    contract = build_gles31_skinning_contract_from_render_command(command)
    command["ready"] = False
    command["blocking_reasons"] = ["skinning:external-pose-blocked"]
    parity = validate_gles31_skinning_contract_parity(command, contract)
    assert parity["valid"] is False
    assert "parity:render-command-not-ready" in parity["blocking_reasons"]
    assert "parity:source-blocker:skinning:external-pose-blocked" in parity["blocking_reasons"]

def test_gles31_skinning_submission_gate_returns_contract_and_parity():
    from skinning_glsl import build_gles31_skinning_submission_gate

    command = _skinned_render_command()
    gate = build_gles31_skinning_submission_gate(command, bone_binding=9, max_bones=64)
    assert gate["format"] == "SHIFT.GLES31SkinningSubmissionGate/1"
    assert gate["ready"] is True, gate["blocking_reasons"]
    assert gate["blocking_reasons"] == []
    assert gate["contract"]["bone_binding"] == 9
    assert gate["parity"]["valid"] is True
