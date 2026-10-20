import struct, sys
from pathlib import Path

import pytest

sys.path.insert(0,str(Path(__file__).parents[1]))
from shader_ir import parse_shader_blobs
from shader_asm import parse_program, to_glsl

from synthetic_fixtures import glass_fxo

FIX=None

def test_glass_programs_have_register_operands():
    data=glass_fxo(); blobs=parse_shader_blobs(data)
    assert len(blobs)==4
    for b in blobs:
        p=parse_program(data,b.offset,b.end,b.stage,b.major,b.minor)
        assert p.instructions
        assert p.instructions[0].name in ('DCL','DEF','DEFI','MOV','DCL')
        assert all(i.length >= 0 for i in p.instructions)

def test_operand_encoding_roundtrip():
    # temp r3, write xy, source c7.zwzy
    dst=0x80000000 | 3 | (0x3<<16)
    src=0x80000000 | 7 | (2 | (3<<2) | (0<<4) | (1<<6))<<16
    # MOV instruction length 2
    data=struct.pack('<IIII',0xFFFE0300, (2<<24)|1, dst, src)+struct.pack('<I',0xFFFF)
    p=parse_program(data)
    assert p.instructions[0].name=='MOV'
    assert p.instructions[0].operands[0].write_mask=='xy'
    assert p.instructions[0].operands[1].swizzle=='zwxy'

def test_glsl_translation_is_nonempty():
    data=glass_fxo(); b=parse_shader_blobs(data)[0]
    p=parse_program(data,b.offset,b.end,b.stage,b.major,b.minor)
    glsl=to_glsl(p)
    assert '#version 310 es' in glsl
    assert 'void main()' in glsl


def _program_with(opcode: int, name: str):
    from shader_asm import Operand, Instruction, ShaderProgram
    dst = Operand(token=0x80000000, kind="dest", reg_type=0, index=0, write_mask="xyzw")
    srcs = [
        Operand(token=0x80000000 + i, kind="source", reg_type=0, index=i, swizzle="xyzw")
        for i in (1, 2, 3)
    ]
    return ShaderProgram(
        offset=0, end=0, stage="pixel", major=3, minor=0,
        instructions=[Instruction(0, opcode, name, 0, 4, 0, False, [dst, *srcs])],
        inputs=[], outputs=[], samplers=[], constants=[], temps=[0, 1, 2, 3],
        unsupported_opcodes=[],
    )


def test_glsl_cmp_lrp_preserve_d3d9_semantics():
    from shader_asm import to_glsl
    cmp_glsl = to_glsl(_program_with(88, "CMP"))
    lrp_glsl = to_glsl(_program_with(18, "LRP"))
    assert "mix(r3,r2,greaterThanEqual(r1,vec4(0.0)))" in cmp_glsl
    assert "mix(r3,r2,r1)" in lrp_glsl


def test_scalar_swizzles_replicate_and_masked_results_select_written_lanes():
    from shader_asm import Operand, Instruction, ShaderProgram, _glsl_reg, to_glsl

    dst = Operand(token=0, kind="dest", reg_type=0, index=0, write_mask="z")
    left = Operand(token=0, kind="source", reg_type=0, index=1, swizzle="xyzw")
    right = Operand(token=0, kind="source", reg_type=0, index=2, swizzle="xyzw")
    scalar_x = Operand(token=0, kind="source", reg_type=0, index=1, swizzle="x")
    program = ShaderProgram(
        0, 0, "pixel", 3, 0,
        [
            Instruction(0, 8, "DP3", 0, 3, 0, False, [dst, left, right]),
            Instruction(3, 1, "MOV", 0, 2, 0, False, [
                Operand(token=0, kind="dest", reg_type=0, index=3, write_mask="z"),
                scalar_x,
            ]),
        ],
        [], [], [], [], [0, 1, 2, 3], [], [], [], {}
    )

    glsl = to_glsl(program, target="vulkan")

    assert "r1.xyz" in glsl
    assert "r0.z = (vec4(dot(r1.xyz,r2.xyz))).z;" in glsl
    assert "r3.z = (vec4(r1.x)).z;" in glsl
    assert _glsl_reg(
        Operand(token=0, kind="source", reg_type=14, index=0, swizzle="x"),
        "pixel",
    ) == "bvec4(b[0].x)"
    assert _glsl_reg(
        Operand(token=0, kind="source", reg_type=3, index=0, swizzle="x"),
        "vertex",
    ) == "ivec4(a0.x)"


def test_vertex_position_semantic_uses_gl_position():
    from shader_asm import Operand, Instruction, ShaderProgram, to_glsl

    position = Operand(token=0, kind="dest", reg_type=6, index=0)
    varying = Operand(token=0, kind="dest", reg_type=6, index=1)
    source = Operand(token=0, kind="source", reg_type=1, index=0)
    program = ShaderProgram(
        0, 0, "vertex", 3, 0,
        [
            Instruction(0, 1, "MOV", 0, 2, 0, False, [position, source]),
            Instruction(2, 1, "MOV", 0, 2, 0, False, [varying, source]),
        ],
        [], [
            {"usage": "POSITION", "index": 0, "register": "oT0"},
            {"usage": "TEXCOORD", "index": 0, "register": "oT1"},
        ], [], [], [0], [], [], [], {}
    )

    glsl = to_glsl(program, target="vulkan", output_locations={1: 0})

    assert "gl_Position = in_0;" in glsl
    assert "out vec4 out_0" not in glsl
    assert "out vec4 out_1" in glsl


def test_shader_def_float_constants_are_embedded_in_translated_glsl():
    from shader_asm import Operand, Instruction, ShaderProgram, to_glsl

    destination = Operand(token=0, kind="dest", reg_type=2, index=12)
    literals = [
        Operand(token=0, kind="literal", value=value)
        for value in (0.5, -1.0, 2.0, 0.0)
    ]
    temp = Operand(token=0, kind="dest", reg_type=0, index=0)
    constant = Operand(token=0, kind="source", reg_type=2, index=12, swizzle="xyzw")
    program = ShaderProgram(
        offset=0,
        end=0,
        stage="vertex",
        major=3,
        minor=0,
        instructions=[
            Instruction(0, 81, "DEF", 0, 5, 0, False, [destination, *literals]),
            Instruction(5, 1, "MOV", 0, 2, 0, False, [temp, constant]),
        ],
        inputs=[],
        outputs=[],
        samplers=[],
        constants=[12],
        temps=[0],
        unsupported_opcodes=[],
        const_ints=[],
        const_bools=[],
        sampler_types={},
    )

    glsl = to_glsl(program, target="vulkan")

    assert "const vec4 shift_vs_constants_def_c12 = vec4(0.5, -1.0, 2.0, 0.0);" in glsl
    assert "r0 = shift_vs_constants_def_c12;" in glsl
    assert "shift_vs_constants.c[12]" not in glsl


def test_predication_is_preserved_in_ir():
    from shader_asm import Operand, Instruction, ShaderProgram, to_glsl
    dst = Operand(token=0x80000000, kind="dest", reg_type=0, index=0, write_mask="xyzw")
    src = Operand(token=0x80000000, kind="source", reg_type=0, index=1, swizzle="xyzw")
    pred = Operand(token=0x80000000, kind="source", reg_type=19, index=0, swizzle="xxxx")
    p = ShaderProgram(
        0, 0, "pixel", 3, 0,
        [Instruction(0, 1, "MOV", 0, 3, 0, True, [dst, src], pred)],
        [], [], [], [], [0,1], [], [], [], {}
    )
    glsl = to_glsl(p)
    assert "mix(r0,r1,predicate.xxxx)" in glsl


def test_glsl_translation_covers_abs_and_d3d9_derivatives():
    abs_glsl = to_glsl(_program_with(35, "ABS"))
    dsx_glsl = to_glsl(_program_with(91, "DSX"))
    dsy_glsl = to_glsl(_program_with(92, "DSY"))
    assert "abs(r1)" in abs_glsl
    assert "dFdx(r1)" in dsx_glsl
    assert "dFdy(r1)" in dsy_glsl


def test_glsl_float_constants_use_shift_d3d9_ubo():
    glsl = to_glsl(_program_with(1, "MOV"))
    assert "layout(std140, binding = 14) uniform ShiftD3D9Constants" in glsl
    assert glsl.count("vec4 c[") == 1
    assert "} shift_ps_constants;" in glsl


def test_d3d9_opcode_table_preserves_authoritative_numeric_holes():
    from shader_asm import OPCODES

    assert 49 not in OPCODES
    assert 63 not in OPCODES
    assert OPCODES[64] == "TEXCOORD"
    assert OPCODES[65] == "TEXKILL"
    assert OPCODES[66] == "TEX"
    assert OPCODES[75] == "RESERVED0"
    assert OPCODES[81] == "DEF"
    assert OPCODES[82] == "TEXREG2RGB"
    assert OPCODES[91] == "DSX"
    assert OPCODES[92] == "DSY"
    assert OPCODES[93] == "TEXLDD"
    assert OPCODES[95] == "TEXLDL"


def test_texkill_is_not_decoded_as_def():
    src = 0x80000000
    data = struct.pack('<III', 0xFFFF0300, (1<<24)|65, src) + struct.pack('<I', 0xFFFF)
    p = parse_program(data)

    assert p.instructions[0].name == "TEXKILL"
    assert p.instructions[0].operands[0].kind == "source"
    assert p.constants == []


def test_def_uses_opcode_81_and_literal_payload():
    dst_c0 = 0x80000000 | (2<<28) | (0xF<<16)
    values = [struct.unpack('<I', struct.pack('<f', value))[0] for value in (1.0, 2.0, 3.0, 4.0)]
    data = struct.pack('<II', 0xFFFF0300, (5<<24)|81)
    data += struct.pack('<I', dst_c0)
    data += struct.pack('<4I', *values)
    data += struct.pack('<I', 0xFFFF)
    p = parse_program(data)

    assert p.instructions[0].name == "DEF"
    assert p.instructions[0].operands[0].kind == "dest"
    assert all(o.kind == "literal" for o in p.instructions[0].operands[1:])
    assert p.constants == [0]


def test_glsl_translation_fails_closed_by_default():
    with pytest.raises(ValueError, match="unsupported CND opcode=80"):
        to_glsl(_program_with(80, "CND"))

    glsl = to_glsl(_program_with(80, "CND"), strict=False)
    assert "unsupported CND opcode=80" in glsl


def test_vertex_output_written_without_dcl_is_declared():
    from shader_asm import Operand, Instruction, ShaderProgram

    dst = Operand(token=0, kind="dest", reg_type=6, index=0, write_mask="xyzw")
    src = Operand(token=0, kind="source", reg_type=0, index=0, swizzle="xyzw")
    p = ShaderProgram(
        0, 0, "vertex", 3, 0,
        [Instruction(0, 1, "MOV", 0, 2, 0, False, [dst, src])],
        [], [], [], [], [0], [], [], [], {}
    )

    glsl = to_glsl(p)
    assert "layout(location=0) out vec4 out_0;" in glsl
    assert "out_0 = r0;" in glsl


def test_pixel_mrt_outputs_are_declared_from_written_registers():
    from shader_asm import Operand, Instruction, ShaderProgram

    src = Operand(token=0, kind="source", reg_type=0, index=0, swizzle="xyzw")
    dst0 = Operand(token=0, kind="dest", reg_type=8, index=0, write_mask="xyzw")
    dst1 = Operand(token=0, kind="dest", reg_type=8, index=1, write_mask="xyzw")
    p = ShaderProgram(
        0, 0, "pixel", 3, 0,
        [
            Instruction(0, 1, "MOV", 0, 2, 0, False, [dst0, src]),
            Instruction(0, 1, "MOV", 0, 2, 0, False, [dst1, src]),
        ],
        [], [], [], [], [0], [], [], [], {}
    )

    glsl = to_glsl(p)
    assert "layout(location=0) out vec4 fragColor0;" in glsl
    assert "layout(location=1) out vec4 fragColor1;" in glsl


def test_gles_constant_binding_uses_portable_guaranteed_range():
    with pytest.raises(ValueError, match="0..23"):
        to_glsl(_program_with(1, "MOV"), constant_binding=24)
    assert "binding = 24" in to_glsl(_program_with(1, "MOV"), constant_binding=24, target="vulkan")
