import struct, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from shader_asm import parse_program
from shader_interface import vertex_attribute_bindings

def shader_with_usage():
    # VS: POSITION0=v0, COLOR0=v1, TEXCOORD2=v2.
    # MOV keeps v2.xy only, so the linker should choose MEB property 132 (FLOAT2).
    words=[0xFFFE0300,
           (2<<24)|31, 0|(0<<16), 0x80000000|0|(15<<16)|(1<<28),
           (2<<24)|31, 10|(0<<16), 0x80000000|1|(15<<16)|(1<<28),
           (2<<24)|31, 5|(2<<16), 0x80000000|2|(15<<16)|(1<<28),
           (3<<24)|1, 0x80000000|3|(15<<16)|(6<<28), 0x80000000|2|(0x3<<16)|(1<<28),
           0xFFFF]
    return struct.pack("<"+"I"*len(words),*words)

def test_component_usage_selects_float2_uv():
    p=parse_program(shader_with_usage())
    r=vertex_attribute_bindings(p,["200","460","130","132"])
    by={x["semantic"]["usage"]+str(x["semantic"]["index"]):x for x in r["bindings"]}
    assert by["TEXCOORD2"]["property_id"]=="132"
    assert by["TEXCOORD2"]["required_components"]==2
    assert r["valid"] is True
