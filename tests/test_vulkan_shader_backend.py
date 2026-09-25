from shader_asm import ShaderProgram
from shader_backend import validate_vulkan_glsl_pair, validate_linked_shader_pair_vulkan


def test_shader_asm_vulkan_target_uses_core_profile():
    program = ShaderProgram(
        stage="vertex",
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
    from shader_asm import to_glsl

    glsl = to_glsl(program, target="vulkan")
    assert glsl.startswith("#version 450\n")
    assert "precision highp" not in glsl
    assert "binding = 14" in glsl


def test_vulkan_shader_validation_reports_unavailable_cleanly(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _name: None)
    result = validate_vulkan_glsl_pair("#version 450\nvoid main(){}", "#version 450\nvoid main(){}")
    assert result["format"] == "SHIFT.VulkanShaderValidation/1"
    assert result["status"] == "unavailable"


def test_vulkan_linked_pair_rejects_missing_vulkan_sources():
    result = validate_linked_shader_pair_vulkan({"format": "SHIFT.LinkedShaderPair/1"})
    assert result["status"] == "invalid"
    assert "linked-shader:vulkan-source-missing" in result["blocking_reasons"]


def test_vulkan_shader_sampler_target_uses_descriptor_set_one():
    from shader_asm import ShaderProgram, to_glsl

    program = ShaderProgram(
        stage="pixel",
        major=3,
        minor=0,
        offset=0,
        end=4,
        inputs=[],
        outputs=[],
        samplers=[1],
        constants=[],
        temps=[],
        unsupported_opcodes=[],
        instructions=[],
        const_ints=[],
        const_bools=[],
        sampler_types={1: "sampler2D"},
    )
    glsl = to_glsl(program, target="vulkan")
    assert "layout(set=1,binding=1) uniform sampler2D tex1;" in glsl
