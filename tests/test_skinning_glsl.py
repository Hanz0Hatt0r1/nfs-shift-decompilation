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
    packet["bind_skeleton"]["palette"]["bone_count"] = 129
    packet["bind_skeleton"]["palette"]["matrices_3x4"] = (
        [[1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0]] * 129
    )
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
    assert contract["attributes"]["blendindices0"]["location"] == 2
