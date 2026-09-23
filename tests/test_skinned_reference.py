from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from skinned_draw import build_skinned_draw_contract
from skinned_reference import skin_draw_directions, skin_draw_points


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
