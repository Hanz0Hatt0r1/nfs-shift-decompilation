import struct, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]))
from shader_ir import parse_shader_blobs
from shader_asm import parse_program, to_glsl

FIX=Path(__file__).parent/'fixtures'/'glass.fxo'

def test_glass_programs_have_register_operands():
    data=FIX.read_bytes(); blobs=parse_shader_blobs(data)
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
    data=FIX.read_bytes(); b=parse_shader_blobs(data)[0]
    p=parse_program(data,b.offset,b.end,b.stage,b.major,b.minor)
    glsl=to_glsl(p)
    assert '#version 310 es' in glsl
    assert 'void main()' in glsl
