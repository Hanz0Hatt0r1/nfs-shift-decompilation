from skinned_draw import build_skinned_draw_contract


def _skeleton(coverage=1.0):
    return {
        "format": "SHIFT.BindSkeleton/1",
        "source": {"bab": "idle", "bas": "car"},
        "bone_count": 2,
        "coverage": coverage,
        "links": [
            {"index": 0, "name": "root", "parent": None, "local_matrix_3x4": [
                1.0, 0.0, 0.0, 0.0,
                0.0, 1.0, 0.0, 0.0,
                0.0, 0.0, 1.0, 0.0,
            ]},
            {"index": 1, "name": "wheel", "parent": "root", "local_matrix_3x4": [
                1.0, 0.0, 0.0, 1.0,
                0.0, 1.0, 0.0, 2.0,
                0.0, 0.0, 1.0, 3.0,
            ]},
        ],
        "animation_payload": {
            "offset": 512,
            "size": 32,
            "sha256": "deadbeef",
            "decoded": False,
        },
    }


def _packet():
    return {
        "shader_selection": {"status": "unique"},
        "bind_skeleton": _skeleton(),
        "mesh": {
            "ref": "cars/body.meb",
            "vertex_count": 4,
            "triangle_count": 2,
            "skinning": {
                "has_weights": True,
                "has_indices": True,
                "skinned": True,
                "valid": True,
            },
            "vertex_layout": {
                "format": "SHIFT.VertexLayout/1",
                "buffer_stride": 36,
                "attributes": [
                    {
                        "property_id": "200",
                        "location": 0,
                        "offset": 0,
                        "android": "FLOAT32x3",
                        "components": 3,
                        "normalized": False,
                    },
                    {
                        "property_id": "310",
                        "location": 1,
                        "offset": 12,
                        "android": "FLOAT32x4",
                        "components": 4,
                        "normalized": False,
                        "usage": "BLENDWEIGHT",
                        "usage_index": 0,
                    },
                    {
                        "property_id": "580",
                        "location": 2,
                        "offset": 28,
                        "android": "UINT8x4",
                        "components": 4,
                        "normalized": False,
                        "usage": "BLENDINDICES",
                        "usage_index": 0,
                    },
                ],
            },
        },
        "submeshes": [
            {
                "first_index": 0,
                "index_count": 6,
                "material": {
                    "shader_selection": {
                        "status": "unique",
                        "shader_pair": {
                            "selection_status": "unique",
                            "interface": {"valid": True},
                            "vertex_format": {"valid": True},
                        },
                        "external_samplers": [
                            {
                                "sampler": "environmentMap",
                                "d3d9_sampler_register": 3,
                                "binding": "external-or-specialised",
                            }
                        ],
                    },
                    "textures": [
                        {
                            "ref": "textures/body.dds",
                            "binding_source": "fxo-ctab",
                            "d3d9_sampler_register": 1,
                        }
                    ],
                },
            }
        ],
    }


def test_valid_skinned_draw_contains_four_weight_and_index_contract():
    result = build_skinned_draw_contract(_packet())
    assert result["ready"] is True
    assert result["blocking_reasons"] == []
    assert result["skinning"]["influences"] == 4
    assert result["skinning"]["weights"]["target_location"] == 1
    assert result["skinning"]["indices"]["target_location"] == 2


def test_skinned_draw_rejects_missing_blend_attributes():
    packet = _packet()
    packet["mesh"]["vertex_layout"]["attributes"] = [
        packet["mesh"]["vertex_layout"]["attributes"][0]
    ]
    result = build_skinned_draw_contract(packet)
    assert result["ready"] is False
    assert "skinning-attribute:BLENDWEIGHT-missing-or-ambiguous" in result["blocking_reasons"]
    assert "skinning-attribute:BLENDINDICES-missing-or-ambiguous" in result["blocking_reasons"]


def test_skinned_draw_rejects_incomplete_bind_skeleton():
    packet = _packet()
    packet["bind_skeleton"]["coverage"] = 0.5
    result = build_skinned_draw_contract(packet)
    assert result["ready"] is False
    assert "bind-skeleton:coverage-incomplete" in result["blocking_reasons"]


def test_skinned_draw_preserves_bind_matrices_and_opaque_animation_payload():
    result = build_skinned_draw_contract(_packet())
    palette = result["bind_skeleton"]["palette"]
    assert palette["matrices_3x4"][1] == [
        1.0, 0.0, 0.0, 1.0,
        0.0, 1.0, 0.0, 2.0,
        0.0, 0.0, 1.0, 3.0,
    ]
    assert palette["animation_payload"]["decoded"] is False
    assert palette["animation_payload"]["sha256"] == "deadbeef"
    assert palette["index_range"] == [0, 1]


def test_skinned_draw_preserves_external_samplers():
    result = build_skinned_draw_contract(_packet())
    assert result["external_samplers"][0]["sampler"] == "environmentMap"
    assert result["external_samplers"][0]["d3d9_sampler_register"] == 3


def test_skinned_draw_rejects_non_unique_shader_selection():
    packet = _packet()
    packet["shader_selection"]["status"] = "ambiguous"
    result = build_skinned_draw_contract(packet)
    assert result["ready"] is False
    assert "shader-selection:ambiguous" in result["blocking_reasons"]
