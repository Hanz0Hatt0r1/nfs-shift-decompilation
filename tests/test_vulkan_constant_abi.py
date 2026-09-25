from shader_asm import ShaderProgram, to_glsl
from vulkan_constant_abi import build_vulkan_constant_layout


def _program(stage):
    return ShaderProgram(
        stage=stage,
        major=3,
        minor=0,
        offset=0,
        end=4,
        inputs=[],
        outputs=[],
        samplers=[],
        constants=[],
        temps=[],
        unsupported_opcodes=[],
        instructions=[],
        const_ints=[],
        const_bools=[],
        sampler_types={},
    )


def test_vulkan_vertex_and_pixel_use_distinct_constant_bindings():
    vertex = to_glsl(_program("vertex"), target="vulkan")
    pixel = to_glsl(_program("pixel"), target="vulkan")
    assert "binding = 14" in vertex
    assert "binding = 15" in pixel


def test_vulkan_constant_layout_maps_stage_registers():
    command = {
        "format": "SHIFT.RenderCommand/1",
        "submeshes": [{
            "constant_commands": [
                {"stage": "vertex", "register_index": 3, "register_count": 2},
                {"stage": "pixel", "register_index": 7, "register_count": 1},
            ]
        }],
    }
    result = build_vulkan_constant_layout(command)
    assert result["ready"] is True
    assert result["stages"]["vertex"]["descriptor_binding"] == 14
    assert result["stages"]["pixel"]["descriptor_binding"] == 15
    assert result["stages"]["vertex"]["registers"] == [3, 4]
    assert result["stages"]["pixel"]["registers"] == [7]
    assert result["stages"]["pixel"]["buffer_size"] == 4096


def test_vulkan_constant_layout_rejects_register_overflow():
    command = {
        "format": "SHIFT.RenderCommand/1",
        "submeshes": [{
            "constant_commands": [{
                "stage": "pixel",
                "register_index": 255,
                "register_count": 2,
            }]
        }],
    }
    result = build_vulkan_constant_layout(command)
    assert result["ready"] is False
    assert "vulkan-constants:register-range-invalid:pixel:255" in result["blocking_reasons"]
