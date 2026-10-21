from d3d9_vulkan_state import translate_render_states, translate_sampler_state


def test_render_state_translation_covers_depth_blend_and_color_mask():
    result = translate_render_states({
        7: 1,
        14: 1,
        23: 4,
        27: 1,
        19: 5,
        20: 6,
        168: 0xD,
    })
    assert result["ready"] is True
    assert result["depth"]["test_enable"] is True
    assert result["depth"]["write_enable"] is True
    assert result["depth"]["compare_op"] == "VK_COMPARE_OP_LESS_OR_EQUAL"
    assert result["blend"]["src_factor"] == "VK_BLEND_FACTOR_SRC_ALPHA"
    assert result["blend"]["dst_factor"] == "VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA"
    assert result["color_write_mask"] == {"r": True, "g": False, "b": True, "a": True}


def test_render_state_translation_blocks_unknown_modes():
    result = translate_render_states({23: 999, 22: 999, 19: 999})
    assert result["ready"] is False
    assert "d3d9-vulkan-state:unsupported-zfunc:999" in result["blocking_reasons"]
    assert "d3d9-vulkan-state:unsupported-cullmode:999" in result["blocking_reasons"]


def test_d3d_cull_values_map_to_opposite_vulkan_face_flags():
    assert translate_render_states({22: 1})["raster"]["cull_mode"] == "NONE"
    assert translate_render_states({22: 2})["raster"]["cull_mode"] == "BACK"
    assert translate_render_states({22: 3})["raster"]["cull_mode"] == "FRONT"


def test_sampler_state_translation_is_explicit():
    result = translate_sampler_state(1, {
        1: 1,
        2: 3,
        3: 3,
        5: 2,
        6: 2,
    })
    assert result["ready"] is True
    assert result["address_mode"]["u"] == "VK_SAMPLER_ADDRESS_MODE_REPEAT"
    assert result["address_mode"]["v"] == "VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE"
    assert result["filter"]["min"] == "VK_FILTER_LINEAR"
    assert result["filter"]["mag"] == "VK_FILTER_LINEAR"


def test_sampler_state_accepts_captured_transparent_border_and_srgb():
    result = translate_sampler_state(3, {1: 4, 2: 4, 3: 3, 4: 0, 11: 1})
    assert result["ready"] is True
    assert result["address_mode"]["u"] == "VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_BORDER"
    assert result["border_color"] == "VK_BORDER_COLOR_FLOAT_TRANSPARENT_BLACK"
    assert result["srgb_texture"] is True


def test_sampler_state_blocks_unproven_or_unsupported_border_modes():
    missing_color = translate_sampler_state(3, {1: 4})
    assert missing_color["ready"] is False
    assert "d3d9-vulkan-state:border-address-requires-proven-color:s3" in missing_color["blocking_reasons"]

    custom_color = translate_sampler_state(3, {1: 4, 4: 0xFF000000})
    assert custom_color["ready"] is False
    assert "d3d9-vulkan-state:unsupported-border-color:s3:4278190080" in custom_color["blocking_reasons"]
