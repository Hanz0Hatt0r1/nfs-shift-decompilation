from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from skinned_draw import build_skinned_draw_contract
from skinned_reference import skin_draw_directions, skin_draw_points, validate_bind_pose


def _draw():
    return {
        "shader_selection": {"status": "unique"},
        "bind_skeleton": {
            "format": "SHIFT.BindSkeleton/1",
            "coverage": 1.0,
            "bone_count": 2,
            "links": [
                {
                    "index": 0,
                    "name": "root",
                    "parent": None,
                    "local_matrix_3x4": [
                        1, 0, 0, 0,
                        0, 1, 0, 0,
                        0, 0, 1, 0,
                    ],
                },
                {
                    "index": 1,
                    "name": "wheel",
                    "parent": "root",
                    "local_matrix_3x4": [
                        1, 0, 0, 1,
                        0, 1, 0, 0,
                        0, 0, 1, 0,
                    ],
                },
            ],
            "animation_payload": {
                "decoded": False,
                "sha256": "opaque",
            },
        },
        "skin_pose": {
            "format": "SHIFT.SkinPose/1",
            "matrix_space": "skinning",
            "bone_count": 2,
            "matrices_3x4": [
                [
                    1, 0, 0, 2,
                    0, 1, 0, 0,
                    0, 0, 1, 0,
                ],
                [
                    1, 0, 0, 0,
                    0, 1, 0, 3,
                    0, 0, 1, 0,
                ],
            ],
            "source": "synthetic",
            "frame": 7,
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
        "submeshes": [
            {
                "material": {
                    "shader_selection": {
                        "status": "unique",
                        "shader_pair": {
                            "selection_status": "unique",
                            "interface": {"valid": True},
                            "vertex_format": {"valid": True},
                        },
                        "textures": [],
                        "linked_shader_pair": {
                            "format": "SHIFT.LinkedShaderPair/1",
                        },
                    }
                }
            }
        ],
    }


def _ready_draw():
    draw = build_skinned_draw_contract(_draw())
    assert draw["ready"] is True
    return draw


def test_skin_draw_points_uses_explicit_skin_pose():
    draw = _ready_draw()
    result = skin_draw_points(
        draw,
        [(1, 2, 3), (0, 1, 0)],
        [(0, 0, 0, 0), (0, 1, 0, 0)],
        [(1, 0, 0, 0), (0.5, 0.5, 0, 0)],
    )
    assert result["format"] == "SHIFT.SkinnedReference/1"
    assert result["frame"] == 7
    assert result["positions"][0] == [3.0, 2.0, 3.0]
    assert result["positions"][1] == [1.0, 2.5, 0.0]


def test_skin_draw_directions_uses_zero_translation():
    draw = _ready_draw()
    result = skin_draw_directions(
        draw,
        [(1, 0, 0)],
        [(1, 0, 0, 0)],
        [(1, 0, 0, 0)],
    )
    assert result["vectors"][0] == [1.0, 0.0, 0.0]


def test_skin_draw_reference_rejects_out_of_range_bone_index():
    draw = _ready_draw()
    with pytest.raises(ValueError, match="invalid skin influences"):
        skin_draw_points(
            draw,
            [(0, 0, 0)],
            [(2, 0, 0, 0)],
            [(1, 0, 0, 0)],
        )


def test_skin_draw_reference_rejects_incomplete_pose():
    draw = _draw()
    draw["skin_pose"]["matrices_3x4"] = draw["skin_pose"]["matrices_3x4"][:1]
    contract = build_skinned_draw_contract(draw)
    assert contract["ready"] is False
    assert "skin-pose:palette-incomplete" in contract["blocking_reasons"]


def test_skinned_draw_rejects_missing_linked_glsl_pair():
    draw = _draw()
    del draw["submeshes"][0]["material"]["shader_selection"]["linked_shader_pair"]
    contract = build_skinned_draw_contract(draw)
    assert contract["ready"] is False
    assert "material-shader-glsl:missing" in contract["blocking_reasons"]


def test_skinned_draw_rejects_linked_glsl_error():
    draw = _draw()
    draw["submeshes"][0]["material"]["shader_selection"]["linked_shader_error"] = "ValueError: translator"
    contract = build_skinned_draw_contract(draw)
    assert contract["ready"] is False
    assert "material-shader-glsl:error" in contract["blocking_reasons"]


def test_validate_bind_pose_accepts_identity_skin_pose():
    draw = _ready_draw()
    draw["skin_pose"]["matrices_3x4"] = [
        [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0],
        [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0],
    ]
    result = validate_bind_pose(
        draw,
        [(1, 2, 3), (-1, 0.5, 2)],
        [(0, 0, 0, 0), (1, 0, 0, 0)],
        [(1, 0, 0, 0), (1, 0, 0, 0)],
    )
    assert result["format"] == "SHIFT.SkinBindPoseCheck/1"
    assert result["valid"] is True
    assert result["max_error"] == 0.0
    assert result["mismatches"] == []


def test_validate_bind_pose_reports_position_error():
    draw = _ready_draw()
    result = validate_bind_pose(
        draw,
        [(0, 0, 0)],
        [(0, 0, 0, 0)],
        [(1, 0, 0, 0)],
        tolerance=0.1,
    )
    assert result["valid"] is False
    assert result["max_error"] == 2.0
    assert result["mismatches"][0]["vertex"] == 0


def test_skin_mesh_reference_transforms_geometry_and_direction_streams():
    from skinned_reference import skin_mesh_reference

    draw = _ready_draw()
    draw["skin_pose"]["matrices_3x4"] = [
        [1, 0, 0, 1, 0, 1, 0, 2, 0, 0, 1, 3],
        [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0],
    ]
    mesh = {
        "vertices": [(1, 0, 0), (0, 1, 0)],
        "normals": [(1, 0, 0), (0, 1, 0)],
        "tangents": [(0, 1, 0), (1, 0, 0)],
        "tangents2": [(0, 0, 1), (0, 0, 1)],
        "uv_layers": {"130": [(0.0, 0.0), (1.0, 1.0)]},
        "colors": [(10, 20, 30, 255), (40, 50, 60, 255)],
        "bone_weights": [(1, 0, 0, 0), (0.5, 0.5, 0, 0)],
        "bone_indices": [(0, 0, 0, 0), (0, 1, 0, 0)],
    }

    result = skin_mesh_reference(draw, mesh)
    assert result["format"] == "SHIFT.SkinnedMeshReference/1"
    assert result["frame"] == 7
    assert result["mesh"]["vertices"][0] == (2.0, 2.0, 3.0)
    assert result["mesh"]["vertices"][1] == (0.5, 1.5, 0.0)
    assert result["mesh"]["normals"][0] == (1.0, 0.0, 0.0)
    assert result["mesh"]["uv_layers"] == mesh["uv_layers"]
    assert result["mesh"]["colors"] == mesh["colors"]
    assert result["mesh"]["bone_indices"] == mesh["bone_indices"]
    assert result["mesh"]["bone_weights"] == mesh["bone_weights"]
    assert result["streams"]["directions"]["NORMAL"]["count"] == 2
    assert result["streams"]["directions"]["TANGENT"]["count"] == 2
    assert result["streams"]["directions"]["BINORMAL"]["count"] == 2


def test_skin_mesh_reference_requires_influence_streams():
    from skinned_reference import skin_mesh_reference

    mesh = {"vertices": [(0, 0, 0)]}
    with pytest.raises(ValueError, match="no bone influence streams"):
        skin_mesh_reference(_ready_draw(), mesh)


def test_skin_mesh_reference_propagates_out_of_range_influence_error():
    from skinned_reference import skin_mesh_reference

    mesh = {
        "vertices": [(0, 0, 0)],
        "bone_indices": [(2, 0, 0, 0)],
        "bone_weights": [(1, 0, 0, 0)],
    }
    with pytest.raises(ValueError, match="invalid skin influences"):
        skin_mesh_reference(_ready_draw(), mesh)
