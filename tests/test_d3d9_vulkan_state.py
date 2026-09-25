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


def test_sampler_state_blocks_border_address_mode():
    result = translate_sampler_state(3, {1: 4})
    assert result["ready"] is False
