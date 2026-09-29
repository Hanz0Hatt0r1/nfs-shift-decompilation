from material_pipeline_state import (
    BLEND_OP_TO_D3D9,
    BLEND_TO_D3D9,
    DEFAULTS,
    TEST_TO_D3D9,
    build_material_pipeline_state,
)


def _enum(index, raw):
    return {
        "raw": raw,
        "engine_enum_index": index,
        "status": "known",
    }


def test_material_pipeline_defaults_match_retail_constructor():
    result = build_material_pipeline_state({})

    assert result["ready"] is True, result["blocking_reasons"]
    assert result["depth"] == {
        "enabled": True,
        "write_enabled": True,
        "engine_compare_index": 3,
        "d3d9_compare_value": 4,
        "vulkan_compare_op": "VK_COMPARE_OP_LESS_OR_EQUAL",
    }
    assert result["alpha_test"]["enabled"] is False
    assert result["alpha_test"]["engine_compare_index"] == 7
    assert result["alpha_test"]["d3d9_compare_value"] == 8
    assert result["alpha_test"]["reference"] == 0.0
    assert result["blend"]["enabled"] is False
    assert result["blend"]["source_d3d9_value"] == 2
    assert result["blend"]["dest_d3d9_value"] == 1
    assert result["blend"]["op_d3d9_value"] == 1
    assert result["vulkan_src_color_blend_factor"] == "VK_BLEND_FACTOR_ONE"
    assert result["vulkan_dst_color_blend_factor"] == "VK_BLEND_FACTOR_ZERO"
    assert result["vulkan_color_blend_op"] == "VK_BLEND_OP_ADD"


def test_material_pipeline_translates_depth_and_alpha_blend_exactly():
    result = build_material_pipeline_state({
        "cull": "EBFCT_ANTICLOCKWISE",
        "depth": {
            "enabled": True,
            "write_enabled": False,
            "function": _enum(3, "ETF_LESS_THAN_OR_EQUAL"),
        },
        "alpha_test": {
            "enabled": False,
            "function": _enum(7, "ETF_PASS"),
            "value_normalized": 0.0,
        },
        "alpha_blend": {
            "enabled": True,
            "source_blend": _enum(4, "EBF_SOURCE_ALPHA"),
            "dest_blend": _enum(5, "EBF_INV_SOURCE_ALPHA"),
            "blend_op": _enum(0, "EBO_ADD"),
        },
    })

    assert result["ready"] is True, result["blocking_reasons"]
    assert result["vulkan_cull_mode"] == "VK_CULL_MODE_FRONT_BIT"
    assert result["vulkan_depth_test_enable"] is True
    assert result["vulkan_depth_write_enable"] is False
    assert result["vulkan_depth_compare_op"] == "VK_COMPARE_OP_LESS_OR_EQUAL"
    assert result["vulkan_blend_enable"] is True
    assert result["vulkan_src_color_blend_factor"] == "VK_BLEND_FACTOR_SRC_ALPHA"
    assert result["vulkan_dst_color_blend_factor"] == "VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA"
    assert result["vulkan_color_blend_op"] == "VK_BLEND_OP_ADD"


def test_material_pipeline_blend_subtract_direction_matches_retail_lookup():
    result = build_material_pipeline_state({
        "alpha_blend": {
            "enabled": True,
            "source_blend": _enum(1, "EBF_ONE"),
            "dest_blend": _enum(0, "EBF_ZERO"),
            "blend_op": _enum(1, "EBO_DEST_MINUS_SOURCE"),
        },
    })

    assert result["ready"] is True, result["blocking_reasons"]
    assert result["blend"]["op_d3d9_value"] == 3
    assert result["vulkan_color_blend_op"] == "VK_BLEND_OP_REVERSE_SUBTRACT"


def test_enabled_alpha_test_fails_closed_until_shader_discard_exists():
    result = build_material_pipeline_state({
        "alpha_test": {
            "enabled": True,
            "function": _enum(6, "ETF_GREATER_THAN_OR_EQUAL"),
            "value_normalized": 64.0 / 255.0,
        },
    })

    assert result["ready"] is False
    assert (
        "material-pipeline:alpha-test-enabled-requires-shader-discard"
        in result["blocking_reasons"]
    )


def test_unmapped_bmt_state_fails_closed():
    result = build_material_pipeline_state({
        "depth": {
            "unmapped_fields": [{"element_id": 123}],
        },
        "unmapped_groups": [{"element_id": 456}],
    })

    assert result["ready"] is False
    assert "material-pipeline:depth-fields-unmapped" in result["blocking_reasons"]
    assert "material-pipeline:unmapped-bmt-state-group" in result["blocking_reasons"]


def test_unknown_enum_fails_closed():
    result = build_material_pipeline_state({
        "depth": {
            "function": {
                "raw": "ETF_MAGIC",
                "engine_enum_index": None,
                "status": "unknown",
            },
        },
    })

    assert result["ready"] is False
    assert "material-pipeline:depth-function-enum-unresolved" in result["blocking_reasons"]


def test_retail_lookup_tables_are_exact():
    assert TEST_TO_D3D9 == tuple(range(1, 9))
    assert BLEND_TO_D3D9 == tuple(range(1, 12))
    assert BLEND_OP_TO_D3D9 == (1, 3, 4, 5, 2)
    assert DEFAULTS["depth_function"] == 3
    assert DEFAULTS["source_blend"] == 1
    assert DEFAULTS["dest_blend"] == 0
