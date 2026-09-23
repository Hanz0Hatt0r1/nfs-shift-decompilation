from __future__ import annotations
import re
from itertools import product
from typing import Iterable
from shader_asm import ShaderProgram, parse_program
from shader_ir import parse_shader_blobs

D3D9_DECL_USAGE={0:"POSITION",1:"BLENDWEIGHT",2:"BLENDINDICES",3:"NORMAL",4:"PSIZE",5:"TEXCOORD",6:"TANGENT",7:"BINORMAL",8:"TESSFACTOR",9:"POSITIONT",10:"COLOR",11:"FOG",12:"DEPTH",13:"SAMPLE"}
MEB_SEMANTICS={"200":("POSITION",0),"460":("COLOR",0),"220":("NORMAL",0),"240":("TANGENT",0),"250":("BINORMAL",0),"310":("BLENDWEIGHT",0),"580":("BLENDINDICES",0)}
for i,pid in enumerate(("130","131","132","133","134")): MEB_SEMANTICS[pid]=("TEXCOORD",i)
for i,pid in enumerate(("230","231","232","233","234")): MEB_SEMANTICS[pid]=("TEXCOORD",i)

def semantic_key(d:dict)->tuple[str,int]:
    return str(d.get("usage")),int(d.get("index",0))

def register_index(register:str|None)->int|None:
    if not register:return None
    m=re.search(r"(?:v|oT|oC|oD|oDepth)(\d+)",register)
    return int(m.group(1)) if m else None

def program_interface(program:ShaderProgram)->dict:
    return {"stage":program.stage,"version":[program.major,program.minor],"inputs":[dict(x) for x in program.inputs],"outputs":[dict(x) for x in program.outputs],"samplers":list(program.samplers),"constants":list(program.constants),"temps":list(program.temps)}

def link_vertex_pixel(vertex:ShaderProgram,pixel:ShaderProgram)->dict:
    outputs={semantic_key(x):x for x in vertex.outputs}
    pixel_keys={semantic_key(x) for x in pixel.inputs}
    links=[]; missing=[]
    for pin in pixel.inputs:
        key=semantic_key(pin); out=outputs.get(key)
        rec={"semantic":{"usage":key[0],"index":key[1]},"pixel_register":pin.get("register"),"vertex_register":out.get("register") if out else None,"matched":out is not None,"pixel_decl":pin,"vertex_decl":out}
        if out is None: missing.append(rec)
        else:
            rec["pixel_register_index"]=register_index(pin.get("register"))
            rec["vertex_register_index"]=register_index(out.get("register"))
        links.append(rec)
    extra=[{"semantic":{"usage":k[0],"index":k[1]},"vertex_register":v.get("register"),"vertex_decl":v} for k,v in outputs.items() if k not in pixel_keys]
    matched=len(pixel.inputs)-len(missing)
    return {"valid":not missing,"matched":matched,"pixel_inputs":len(pixel.inputs),"missing_inputs":missing,"extra_vertex_outputs":extra,"links":links,"score":matched/len(pixel.inputs) if pixel.inputs else 1.0}

def infer_meb_semantics(properties:Iterable[str|dict])->list[dict]:
    out=[]
    for value in properties:
        pid=str(value.get("id")) if isinstance(value,dict) else str(value)
        if pid in MEB_SEMANTICS:
            usage,index=MEB_SEMANTICS[pid]; out.append({"property_id":pid,"usage":usage,"usage_index":index})
    return out

def match_vertex_format(program:ShaderProgram,properties:Iterable[str|dict])->dict:
    available={(x["usage"],x["usage_index"]) for x in infer_meb_semantics(properties)}
    required={semantic_key(x) for x in program.inputs}
    missing=sorted(({"usage":u,"index":i} for u,i in required-available),key=lambda x:(x["usage"],x["index"]))
    unused=sorted(({"usage":u,"index":i} for u,i in available-required),key=lambda x:(x["usage"],x["index"]))
    matched=len(required)-len(missing)
    return {"valid":not missing,"required":len(required),"available":len(available),"matched":matched,"missing":missing,"unused":unused,"score":matched/len(required) if required else 1.0,"available_semantics":sorted(({"usage":u,"index":i} for u,i in available),key=lambda x:(x["usage"],x["index"]))}

def enumerate_shader_pairs(programs:Iterable[ShaderProgram],properties:Iterable[str|dict]=())->list[dict]:
    programs=list(programs); props=list(properties)
    vertices=[p for p in programs if p.stage=="vertex"]; pixels=[p for p in programs if p.stage=="pixel"]; candidates=[]
    for vs,ps in product(vertices,pixels):
        interface=link_vertex_pixel(vs,ps)
        vf=match_vertex_format(vs,props) if props else {"valid":True,"score":1.0,"missing":[],"unused":[]}
        candidates.append({"vertex_offset":vs.offset,"pixel_offset":ps.offset,"score":0.65*interface["score"]+0.35*vf["score"],"interface":interface,"vertex_format":vf,"pixel_samplers":list(ps.samplers)})
    return sorted(candidates,key=lambda x:(-x["score"],-x["interface"]["score"],-x["vertex_format"]["score"],x["vertex_offset"],x["pixel_offset"]))

def pair_selected_pixel(data:bytes,pixel_offset:int,*,properties:Iterable[str|dict]=())->dict|None:
    programs=[parse_program(data,b.offset,b.end,b.stage,b.major,b.minor) for b in parse_shader_blobs(data)]
    pixel=next((p for p in programs if p.offset==pixel_offset),None)
    if pixel is None or pixel.stage!="pixel": return None
    candidates=[]
    for vs in (p for p in programs if p.stage=="vertex"):
        interface=link_vertex_pixel(vs,pixel); vf=match_vertex_format(vs,properties)
        candidates.append({"vertex_offset":vs.offset,"pixel_offset":pixel.offset,"score":0.65*interface["score"]+0.35*vf["score"],"interface":interface,"vertex_format":vf,"pixel_samplers":list(pixel.samplers)})
    return max(candidates,key=lambda x:(x["score"],x["interface"]["score"],x["vertex_format"]["score"],-x["vertex_offset"]),default=None)
