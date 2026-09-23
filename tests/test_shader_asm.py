import struct, sys
from pathlib import Path
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


def test_glsl_translation_covers_abs_and_derivative_aliases():
    abs_glsl = to_glsl(_program_with(35, "ABS"))
    ddx_glsl = to_glsl(_program_with(84, "DDX"))
    ddy_glsl = to_glsl(_program_with(85, "DDY"))
    assert "abs(r1)" in abs_glsl
    assert "dFdx(r1)" in ddx_glsl
    assert "dFdy(r1)" in ddy_glsl
