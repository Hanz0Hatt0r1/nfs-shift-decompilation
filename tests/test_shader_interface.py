import struct, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from shader_asm import parse_program
from shader_interface import link_vertex_pixel, match_vertex_format

def shader(stage,dcls):
    version=0xFFFE0300 if stage=="vertex" else 0xFFFF0300
    words=[version]
    for usage,index,regtype,regindex in dcls:
        words += [(2<<24)|31, usage|(index<<16), 0x80000000|regindex|(15<<16)|((regtype&7)<<28)]
    words += [0xFFFF]
    return struct.pack("<"+"I"*len(words),*words)

def test_d3d9_usage_codes_are_official():
    p=parse_program(shader("vertex",[(10,0,1,1),(6,0,1,2),(7,0,1,3),(13,0,1,4)]))
    assert [(x["usage"],x["index"]) for x in p.inputs]==[("COLOR",0),("TANGENT",0),("BINORMAL",0),("SAMPLE",0)]

def test_varying_link_uses_semantics_not_register_numbers():
    vs=parse_program(shader("vertex",[(0,0,6,0),(5,2,6,1),(5,0,6,2)]))
    ps=parse_program(shader("pixel",[(5,2,1,0),(5,0,1,1)]))
    r=link_vertex_pixel(vs,ps)
    assert r["valid"] is True
    assert [(x["pixel_register"],x["vertex_register"]) for x in r["links"]]==[("v0","oT1"),("v1","oT2")]

def test_meb_vertex_format_matches_shader():
    vs=parse_program(shader("vertex",[(0,0,1,0),(10,0,1,1),(5,2,1,2),(3,0,1,3)]))
    r=match_vertex_format(vs,["200","460","220","130","132"])
    assert r["valid"] is True and not r["missing"]
