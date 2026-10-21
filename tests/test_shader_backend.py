import hashlib
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

from shader_asm import parse_program
from shader_backend import (
    program_to_ir,
    to_glsl,
    translate_pair,
    validate_linked_shader_pair_vulkan,
    validate_vulkan_glsl_pair,
)


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


def test_vulkan_sincos_lowering_uses_scalar_components():
    validator = shutil.which("glslangValidator")
    if validator is None:
        pytest.skip("glslangValidator is not installed")

    words = list(struct.unpack("<" + "I" * (len(_shader("vertex")) // 4), _shader("vertex")))
    words[-1:-1] = [
        (2 << 24) | 37,  # sincos r0.xy, r1.x
        0x80030000,
        0x80000001,
    ]
    vertex = to_glsl(parse_program(struct.pack("<" + "I" * len(words), *words)), target="vulkan")
    pixel = to_glsl(parse_program(_shader("pixel")), target="vulkan")

    assert "vec4(sin(vec4(r1.x)).x,cos(vec4(r1.x)).x,0.0,0.0)" in vertex
    validation = validate_vulkan_glsl_pair(vertex, pixel)
    assert validation["status"] == "valid", validation


def test_vulkan_loop_reads_iteration_control_from_integer_register():
    validator = shutil.which("glslangValidator")
    if validator is None:
        pytest.skip("glslangValidator is not installed")

    source_words = _shader("vertex")
    words = list(struct.unpack("<" + "I" * (len(source_words) // 4), source_words))
    words[-1:-1] = [
        (2 << 24) | 27,  # loop aL0, i0
        0xF0E40800,
        0xF0E40000,
        29,  # endloop
    ]
    vertex = to_glsl(parse_program(struct.pack("<" + "I" * len(words), *words)), target="vulkan")
    pixel = to_glsl(parse_program(_shader("pixel")), target="vulkan")

    assert "for(int shift_loop=i[0].y, shift_iter=0; shift_iter<i[0].x" in vertex
    validation = validate_vulkan_glsl_pair(vertex, pixel)
    assert validation["status"] == "valid", validation


def test_vulkan_if_bool_register_emits_valid_condition_from_frame_12613(tmp_path):
    fixture_dir = Path(__file__).parent / "fixtures" / "d3d9"
    pixel_bytes = (fixture_dir / "shift_frame_12613_ps_da32197956d1cb89.bin").read_bytes()

    # Exact PS token stream bound at retail DrawIndexedPrimitive event
    # 13640309/frame 12613; capture SHA-256:
    # 82f21548b1bad937e7ee8d6253d27a8fabe4f8223574180eb3a697ec57bbcab4.
    assert hashlib.sha256(pixel_bytes).hexdigest() == (
        "c7378d4462603bbe9fcce35ee6f1d397c9bf97879d726bfb1c4f6c38cfe6baa3"
    )
    assert pixel_bytes[:4] == struct.pack("<I", 0xFFFF0300)

    pixel_program = parse_program(pixel_bytes, stage="pixel")
    if_instructions = [
        (instruction.name, instruction.opcode)
        for instruction in pixel_program.instructions
        if instruction.name == "IF"
    ]
    assert if_instructions == [("IF", 40)]

    pixel = to_glsl(
        pixel_program,
        target="vulkan",
        constant_binding=15,
        bool_constants={0: True},
    )
    assert "if (all(b[0])) {" in pixel
    assert "b[0]=bvec4(true);" in pixel
    validator = shutil.which("glslangValidator")
    if validator is None:
        pytest.skip("glslangValidator is not installed")
    pixel_path = tmp_path / "retail_frame_12613.frag"
    pixel_path.write_text(pixel, encoding="utf-8")
    validation = subprocess.run(
        [
            validator,
            "-V",
            "-S",
            "frag",
            "-o",
            str(tmp_path / "retail_frame_12613.spv"),
            str(pixel_path),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert validation.returncode == 0, validation.stdout + validation.stderr


def test_unset_bool_registers_are_initialized_before_vulkan_if():
    words = [
        0xFFFF0300,
        (1 << 24) | 40,
        0xE0E40800,
        42,
        43,
        0xFFFF,
    ]
    pixel = to_glsl(
        parse_program(struct.pack("<" + "I" * len(words), *words)),
        target="vulkan",
    )

    assert "b[0]=bvec4(false);" in pixel


def test_shader_defb_overrides_draw_state_for_defined_bool_register():
    words = [
        0xFFFF0300,
        (2 << 24) | 47,  # defb b0, true
        0xE0000800,
        1,
        (1 << 24) | 40,  # if b0
        0xE0E40800,
        42,
        43,
        0xFFFF,
    ]
    pixel = to_glsl(
        parse_program(struct.pack("<" + "I" * len(words), *words)),
        target="vulkan",
        bool_constants={0: False},
    )

    assert "b[0]=bvec4(true);" in pixel


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
    # VS: dcl_texcoord5 oT1 plus unused texcoord0 oT2; PS: texcoord5 v0.
    version_v = 0xFFFE0300
    version_p = 0xFFFF0300
    dcl = (2 << 24) | 31
    out_t1 = 0x80000000 | 1 | (15 << 16) | (6 << 28)
    in_v0 = 0x80000000 | 0 | (15 << 16) | (1 << 28)
    words_v = [
        version_v,
        dcl, 0 | (0 << 16), 0x80000000 | 0 | (15 << 16) | (1 << 28),
        dcl, 5 | (5 << 16), out_t1,
        dcl, 5 | (0 << 16), 0x80000000 | 2 | (15 << 16) | (6 << 28),
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
    assert "layout(location=1) out vec4 out_2;" in linked["vertex_glsl"]
    assert "layout(location=0) in vec4 in_0;" in linked["pixel_glsl"]
    validation = validate_linked_shader_pair_vulkan(linked)
    assert validation["status"] == "valid", validation


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
        assert result["status"] == "valid", result
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


def test_parser_decodes_setp_destination_as_predicate():
    version = 0xFFFF0300
    setp = (3 << 24) | 94
    dst_predicate = 0x80000000 | (3 << 28) | (16 << 8)
    src_c0 = 0x80000000 | (2 << 28) | 0
    src_c1 = 0x80000000 | (2 << 28) | 1
    end = 0xFFFF
    data = struct.pack(
        "<IIIII",
        version,
        setp,
        dst_predicate,
        src_c0,
        src_c1,
    ) + struct.pack("<I", end)

    program = parse_program(data)

    assert program.instructions[0].name == "SETP"
    assert program.instructions[0].operands[0].kind == "dest"
    assert program.instructions[0].operands[0].reg_type == 19
    assert program.instructions[0].operands[1].kind == "source"
    assert program.instructions[0].operands[2].reg_type == 2
