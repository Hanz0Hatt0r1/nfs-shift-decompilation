import shutil
import struct
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

from shader_asm import parse_program
from shader_backend import program_to_ir, to_glsl, translate_pair


def _shader(stage: str) -> bytes:
    version = 0xFFFE0300 if stage == "vertex" else 0xFFFF0300
    words = [version]
    if stage == "vertex":
        # dcl_position0 v0; dcl_texcoord0 oT0; mov oT0, v0
        words += [
            (2 << 24) | 31, 0, 0x80000000 | 0 | (15 << 16) | (1 << 28),
            (2 << 24) | 31, 5, 0x80000000 | 0 | (15 << 16) | (6 << 28),
            (2 << 24) | 1, 0x80000000 | 0 | (15 << 16) | (6 << 28),
            0x80000000 | 0 | (0xE4 << 16) | (1 << 28),
        ]
    else:
        # dcl_texcoord0 v0; mov oC0, v0
        words += [
            (2 << 24) | 31, 5, 0x80000000 | 0 | (15 << 16) | (1 << 28),
            (2 << 24) | 1, 0x80000000 | 0 | (15 << 16) | (8 << 28),
            0x80000000 | 0 | (0xE4 << 16) | (1 << 28),
        ]
    words.append(0xFFFF)
    return struct.pack("<" + "I" * len(words), *words)


def test_shader_program_ir_schema():
    p = parse_program(_shader("vertex"))
    ir = program_to_ir(p)
    assert ir["schema"] == "SHIFT.ShaderProgram/1"
    assert ir["stage"] == "vertex"
    assert ir["instructions"]


@pytest.mark.parametrize("stage,validator_stage", [("vertex", "vert"), ("pixel", "frag")])
def test_backend_emits_compilable_gles31(stage, validator_stage, tmp_path):
    validator = shutil.which("glslangValidator")
    if validator is None:
        pytest.skip("glslangValidator is not installed")

    p = parse_program(_shader(stage))
    glsl = to_glsl(p)
    assert glsl.startswith("#version 310 es")
    assert "void main()" in glsl

    path = tmp_path / ("shader.vert" if stage == "vertex" else "shader.frag")
    path.write_text(glsl, encoding="utf-8")
    proc = subprocess.run(
        [validator, "-S", validator_stage, str(path)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_backend_reuses_canonical_glsl_lowering():
    import shader_asm
    assert to_glsl is shader_asm.to_glsl


def test_sampler_type_and_relative_addressing_are_preserved():
    # vs_3_0, dcl_cube s0, mov r0, c[a0.x+2]
    version = 0xFFFE0300
    dcl = (2 << 24) | 31
    cube = (3 << 27)
    sampler = 0x80000000 | ((10 & 7) << 28) | ((10 & 0x18) << 8) | (15 << 16)
    rel_const = 0x80000000 | (2 << 28) | 2 | (0xE4 << 16) | (1 << 13)
    rel_addr = 0x80000000 | (3 << 28) | (0 << 16)
    mov = (3 << 24) | 1
    dst = 0x80000000 | 0 | (15 << 16)
    end = 0xFFFF
    import struct
    data = struct.pack("<IIIIIIIIII", version, dcl, cube, sampler, mov, dst, rel_const, rel_addr, end, 0)
    p = parse_program(data[:-4])
    assert p.sampler_types[0] == "samplerCube"
    src = p.instructions[1].operands[1]
    assert src.relative is True
    assert src.relative_token == rel_addr
    glsl = to_glsl(p)
    assert "samplerCube tex0" in glsl
    assert "c[(int(a0.x)+2)]" in glsl


def _shader_pair_with_different_varying_registers() -> tuple:
    # VS: dcl_texcoord5 oT1; PS: dcl_texcoord5 v0.
    version_v = 0xFFFE0300
    version_p = 0xFFFF0300
    dcl = (2 << 24) | 31
    out_t1 = 0x80000000 | 1 | (15 << 16) | (6 << 28)
    in_v0 = 0x80000000 | 0 | (15 << 16) | (1 << 28)
    words_v = [
        version_v,
        dcl, 0 | (0 << 16), 0x80000000 | 0 | (15 << 16) | (1 << 28),
        dcl, 5 | (5 << 16), out_t1,
        0xFFFF,
    ]
    words_p = [version_p, dcl, 5 | (5 << 16), in_v0, 0xFFFF]
    vs = parse_program(struct.pack("<" + "I" * len(words_v), *words_v))
    ps = parse_program(struct.pack("<" + "I" * len(words_p), *words_p))
    return vs, ps


def test_linked_glsl_translation_shares_varying_locations_by_semantic():
    from shader_interface import build_varying_locations
    vs, ps = _shader_pair_with_different_varying_registers()
    locations = build_varying_locations(vs, ps)
    assert locations["valid"] is True
    assert locations["vertex_output_locations"] == {1: 0}
    assert locations["pixel_input_locations"] == {0: 0}

    linked = translate_pair(vs, ps)
    assert linked["format"] == "SHIFT.LinkedShaderPair/1"
    assert "layout(location=0) out vec4 out_1;" in linked["vertex_glsl"]
    assert "layout(location=0) in vec4 in_0;" in linked["pixel_glsl"]


def test_linked_glsl_translation_maps_vertex_inputs_to_target_layout_locations():
    vs, ps = _shader_pair_with_different_varying_registers()
    # Place POSITION0 at target location 1 by preceding it with another
    # attribute. The D3D9 shader still consumes v0.
    properties = ["220", "200"]
    linked = translate_pair(vs, ps, vertex_properties=properties)
    assert linked["vertex_input_locations"] == {0: 1}
    assert "layout(location=1) in vec4 in_0;" in linked["vertex_glsl"]


def test_linked_shader_pair_validator_rejects_invalid_format():
    from shader_backend import validate_linked_shader_pair
    result = validate_linked_shader_pair({"format": "SHIFT.NotARealShaderPair/1"})
    assert result["status"] == "invalid"
    assert "linked-shader:invalid-format" in result["blocking_reasons"]


def test_linked_shader_pair_validator_reports_compiler_state():
    from shader_backend import validate_linked_shader_pair
    vertex = """#version 310 es
precision highp float;
layout(location=0) in vec3 a_position;
layout(location=0) out vec2 v_uv;
void main() {
    v_uv = a_position.xy;
    gl_Position = vec4(a_position, 1.0);
}
"""
    pixel = """#version 310 es
precision highp float;
layout(location=0) in vec2 v_uv;
layout(location=0) out vec4 out_color;
void main() {
    out_color = vec4(v_uv, 0.0, 1.0);
}
"""
    result = validate_linked_shader_pair({
        "format": "SHIFT.LinkedShaderPair/1",
        "vertex_glsl": vertex,
        "pixel_glsl": pixel,
    })
    assert result["format"] == "SHIFT.GLESShaderValidation/1"
    if result["status"] == "unavailable":
        assert result["blocking_reasons"] == []
    else:
        assert result["status"] == "valid"
        assert result["stages"]["vertex"]["valid"] is True
        assert result["stages"]["pixel"]["valid"] is True
        assert result["link"]["valid"] is True


def test_linked_shader_pair_validator_reports_invalid_glsl_when_available():
    from shader_backend import validate_linked_shader_pair
    result = validate_linked_shader_pair({
        "format": "SHIFT.LinkedShaderPair/1",
        "vertex_glsl": """#version 310 es
void main() { gl_Position = vec4(0.0); }
""",
        "pixel_glsl": """#version 310 es
this is not valid GLSL
""",
    })
    if result["status"] == "unavailable":
        pytest.skip("glslangValidator is not installed")
    assert result["status"] == "invalid"
    assert "linked-shader:pixel-compile-failed" in result["blocking_reasons"]
