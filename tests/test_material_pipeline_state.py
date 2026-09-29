from material_pipeline_state import (
    FORMAT,
    translate_bmt_pipeline_state,
)


def _enum(raw, index):
    return {
        "raw": raw,
        "engine_enum_index": index,
        "status": "known",
    }


def test_phase532_retail_defaults_match_constructor():
    state = translate_bmt_pipeline_state({})

    assert state["format"] == FORMAT
    assert state["ready"] is True
    assert state["depth"]["enabled"] is True
    assert state["depth"]["write_enabled"] is True
    assert (
        state["depth"]["compare"]["engine_name"]
        == "ETF_LESS_THAN_OR_EQUAL"
    )
    assert state["alpha_test"]["enabled"] is False
    assert state["alpha_blend"]["enabled"] is False
    assert state["alpha_blend"]["source_blend"]["engine_name"] == "EBF_ONE"
    assert state["alpha_blend"]["dest_blend"]["engine_name"] == "EBF_ZERO"
    assert state["alpha_blend"]["blend_op"]["engine_name"] == "EBO_ADD"
    assert state["vulkan"]["depth_test_enable"] is True
    assert state["vulkan"]["depth_write_enable"] is True
    assert state["vulkan"]["depth_compare_op"] == "VK_COMPARE_OP_LESS_OR_EQUAL"
    assert state["vulkan"]["blend_enable"] is False


def test_phase532_maps_all_compare_functions_to_d3d9_and_vulkan():
    expected = [
        ("ETF_FAIL", 1, "VK_COMPARE_OP_NEVER"),
        ("ETF_LESS_THAN", 2, "VK_COMPARE_OP_LESS"),
        ("ETF_EQUAL", 3, "VK_COMPARE_OP_EQUAL"),
        ("ETF_LESS_THAN_OR_EQUAL", 4, "VK_COMPARE_OP_LESS_OR_EQUAL"),
        ("ETF_GREATER_THAN", 5, "VK_COMPARE_OP_GREATER"),
        ("ETF_NOT_EQUAL", 6, "VK_COMPARE_OP_NOT_EQUAL"),
        ("ETF_GREATER_THAN_OR_EQUAL", 7, "VK_COMPARE_OP_GREATER_OR_EQUAL"),
        ("ETF_PASS", 8, "VK_COMPARE_OP_ALWAYS"),
    ]
    for index, (name, d3d9, vulkan) in enumerate(expected):
        result = translate_bmt_pipeline_state({
            "depth": {
                "format": "SHIFT.BMTDepthState/1",
                "enabled": True,
                "write_enabled": True,
                "function": _enum(name, index),
            }
        })
        assert result["ready"] is True
        assert result["depth"]["compare"]["d3d9_value"] == d3d9
        assert result["vulkan"]["depth_compare_op"] == vulkan


def test_phase532_maps_blend_factors_and_ops():
    result = translate_bmt_pipeline_state({
        "alpha_blend": {
            "format": "SHIFT.BMTAlphaBlendState/1",
            "enabled": True,
            "source_blend": _enum("EBF_SOURCE_ALPHA", 4),
            "dest_blend": _enum("EBF_INV_SOURCE_ALPHA", 5),
            "blend_op": _enum("EBO_DEST_MINUS_SOURCE", 1),
        }
    })

    assert result["ready"] is True, result["blocking_reasons"]
    blend = result["alpha_blend"]
    assert blend["source_blend"]["d3d9_value"] == 5
    assert blend["dest_blend"]["d3d9_value"] == 6
    assert blend["blend_op"]["d3d9_value"] == 3
    assert result["vulkan"]["blend_enable"] is True
    assert result["vulkan"]["src_color_blend_factor"] == "VK_BLEND_FACTOR_SRC_ALPHA"
    assert (
        result["vulkan"]["dst_color_blend_factor"]
        == "VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA"
    )
    assert result["vulkan"]["color_blend_op"] == "VK_BLEND_OP_REVERSE_SUBTRACT"
    # Retail separate-alpha default is false.
    assert (
        result["vulkan"]["src_alpha_blend_factor"]
        == "VK_BLEND_FACTOR_SRC_ALPHA"
    )
    assert (
        result["vulkan"]["dst_alpha_blend_factor"]
        == "VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA"
    )
    assert (
        result["vulkan"]["alpha_blend_op"]
        == "VK_BLEND_OP_REVERSE_SUBTRACT"
    )


def test_phase532_maps_source_minus_dest_to_subtract():
    result = translate_bmt_pipeline_state({
        "alpha_blend": {
            "enabled": True,
            "source_blend": _enum("EBF_ONE", 1),
            "dest_blend": _enum("EBF_ZERO", 0),
            "blend_op": _enum("EBO_SOURCE_MINUS_DEST", 4),
        }
    })
    assert result["ready"] is True
    assert result["alpha_blend"]["blend_op"]["d3d9_value"] == 2
    assert result["vulkan"]["color_blend_op"] == "VK_BLEND_OP_SUBTRACT"


def test_phase532_blocks_enabled_alpha_test_until_shader_discard_is_proven():
    result = translate_bmt_pipeline_state({
        "alpha_test": {
            "format": "SHIFT.BMTAlphaTestState/1",
            "enabled": True,
            "function": _enum("ETF_GREATER_THAN_OR_EQUAL", 6),
            "value_normalized": 0.5,
        }
    })
    assert result["ready"] is False
    assert (
        "material-pipeline:alpha-test-enabled-unsupported"
        in result["blocking_reasons"]
    )


def test_phase532_blocks_unmapped_depth_or_blend_fields():
    depth = translate_bmt_pipeline_state({
        "depth": {
            "enabled": True,
            "unmapped_fields": [{"element_id": 0x12345678, "value": 0.125}],
        }
    })
    assert depth["ready"] is False
    assert (
        "material-pipeline:depth-unmapped-fields"
        in depth["blocking_reasons"]
    )

    blend = translate_bmt_pipeline_state({
        "alpha_blend": {
            "enabled": False,
            "unmapped_fields": [{"element_id": 0x87654321, "value": True}],
        }
    })
    assert blend["ready"] is False
    assert (
        "material-pipeline:alpha-blend-unmapped-fields"
        in blend["blocking_reasons"]
    )


def test_phase532_blocks_unknown_enum_without_guessing():
    result = translate_bmt_pipeline_state({
        "depth": {
            "enabled": True,
            "function": {
                "raw": "ETF_MAGIC",
                "engine_enum_index": None,
                "status": "unknown",
            },
        }
    })
    assert result["ready"] is False
    assert "material-pipeline:depth-function-unknown:ETF_MAGIC" in (
        result["blocking_reasons"]
    )


def test_phase532_preserves_phase530_cull_mapping():
    result = translate_bmt_pipeline_state({
        "cull": "EBFCT_CLOCKWISE",
    })
    assert result["ready"] is True
    assert result["cull"]["d3d9_name"] == "D3DCULL_CW"
    assert result["vulkan"]["cull_mode"] == "VK_CULL_MODE_BACK_BIT"
