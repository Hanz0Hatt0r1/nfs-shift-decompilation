from __future__ import annotations
import re
from itertools import product
from typing import Iterable
from shader_asm import ShaderProgram, parse_program
from shader_ir import parse_shader_blobs
from meb_format import PROP_NAMES
from vertex_layout import build_layout_from_summary
from skeleton_ir import skinning_contract

D3D9_DECL_USAGE={0:"POSITION",1:"BLENDWEIGHT",2:"BLENDINDICES",3:"NORMAL",4:"PSIZE",5:"TEXCOORD",6:"TANGENT",7:"BINORMAL",8:"TESSFACTOR",9:"POSITIONT",10:"COLOR",11:"FOG",12:"DEPTH",13:"SAMPLE"}
MEB_SEMANTICS={"200":("POSITION",0),"460":("COLOR",0),"461":("COLOR",1),"220":("NORMAL",0),"240":("TANGENT",0),"250":("BINORMAL",0),"310":("BLENDWEIGHT",0),"580":("BLENDINDICES",0)}
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

def build_varying_locations(vertex:ShaderProgram, pixel:ShaderProgram) -> dict:
    """Assign shared GLSL locations to matched VS/PS varyings by semantic key."""
    link = link_vertex_pixel(vertex, pixel)
    semantics = sorted(
        (
            (str(x["semantic"]["usage"]), int(x["semantic"]["index"]))
            for x in link["links"]
            if x.get("matched")
        ),
        key=lambda x: (x[0], x[1]),
    )
    location_by_semantic = {key: i for i, key in enumerate(dict.fromkeys(semantics))}
    vertex_outputs: dict[int, int] = {}
    pixel_inputs: dict[int, int] = {}
    for item in link["links"]:
        if not item.get("matched"):
            continue
        key = (str(item["semantic"]["usage"]), int(item["semantic"]["index"]))
        location = location_by_semantic[key]
        vreg = register_index(item.get("vertex_register"))
        preg = register_index(item.get("pixel_register"))
        if vreg is not None:
            vertex_outputs[vreg] = location
        if preg is not None:
            pixel_inputs[preg] = location
    return {
        "valid": bool(link["valid"]),
        "semantic_locations": [
            {"usage": usage, "index": index, "location": location_by_semantic[(usage, index)]}
            for usage, index in sorted(location_by_semantic, key=lambda x: (x[0], x[1]))
        ],
        "vertex_output_locations": vertex_outputs,
        "pixel_input_locations": pixel_inputs,
        "link": link,
    }

def infer_meb_semantics(properties:Iterable[str|dict])->list[dict]:
    out=[]
    for value in properties:
        pid=str(value.get("id")) if isinstance(value,dict) else str(value)
        if pid in MEB_SEMANTICS:
            usage,index=MEB_SEMANTICS[pid]; out.append({"property_id":pid,"usage":usage,"usage_index":index})
    return out

def _used_components(program:ShaderProgram, register:int)->set[str]:
    used=set()
    for ins in program.instructions:
        for op in ins.operands:
            if op.kind=="source" and op.reg_type==1 and op.index==register:
                sw=op.swizzle or "xyzw"
                used.update(sw)
    return used

def _component_count(chars:set[str])->int:
    order={"x":1,"y":2,"z":3,"w":4}
    return max((order.get(x,0) for x in chars), default=4)

def vertex_attribute_bindings(program:ShaderProgram,properties:Iterable[str|dict])->dict:
    props=list(properties)
    candidates={}
    for value in props:
        pid=str(value.get("id")) if isinstance(value,dict) else str(value)
        sem=MEB_SEMANTICS.get(pid)
        if not sem: continue
        candidates.setdefault(sem,[]).append(value)
    props_by_id={str(v.get("id")) if isinstance(v,dict) else str(v):v for v in props}
    target_layout=build_layout_from_summary({"property_layouts": props}) if props else {"attributes":[]}
    locations={x["property_id"]:x.get("location") for x in target_layout.get("attributes",[])}
    bindings=[]; missing=[]
    for decl in program.inputs:
        key=semantic_key(decl)
        reg=register_index(decl.get("register"))
        used=_used_components(program,reg if reg is not None else -1)
        need=_component_count(used)
        choices=candidates.get(key,[])
        scored=[]
        for value in choices:
            pid=str(value.get("id")) if isinstance(value,dict) else str(value)
            width=None
            if pid in {"200","220","240","250","230","231","232","233","234"}: width=3
            elif pid in {"130","131","132","133","134"}: width=2
            elif pid in {"310","460","461","580"}: width=4
            if width is None: continue
            # Prefer the narrowest attribute that still covers all shader uses.
            scored.append((0 if width==need else 1 if width>need else 2, abs(width-need), pid, value))
        chosen=min(scored,key=lambda x:(x[0],x[1],x[2])) if scored else None
        rec={"semantic":{"usage":key[0],"index":key[1]},"shader_register":decl.get("register"),"used_components":"".join(sorted(used,key="xyzw".index)) if used else "xyzw","required_components":need}
        if chosen is None:
            rec["matched"]=False; missing.append(rec)
        else:
            rec.update({"matched":True,"property_id":chosen[2],"property_name":PROP_NAMES.get(chosen[2],"unknown"),"selection":"exact-width" if chosen[0]==0 else "wider-source-coverage","target_location":locations.get(chosen[2])})

        bindings.append(rec)
    return {"valid":not missing,"bindings":bindings,"missing":missing,"score":1.0-len(missing)/len(program.inputs) if program.inputs else 1.0}

def build_vertex_input_locations(
    program: ShaderProgram,
    properties: Iterable[str | dict],
) -> dict:
    """Map D3D9 vertex input registers to target VertexLayout locations."""
    bindings = vertex_attribute_bindings(program, properties)
    register_locations: dict[int, int] = {}
    unresolved: list[dict] = []
    for binding in bindings["bindings"]:
        reg = register_index(binding.get("shader_register"))
        location = binding.get("target_location")
        if not binding.get("matched") or reg is None or location is None:
            unresolved.append(binding)
            continue
        register_locations[reg] = int(location)
    return {
        "valid": not unresolved,
        "input_locations": register_locations,
        "bindings": bindings["bindings"],
        "unresolved": unresolved,
        "score": bindings["score"],
    }


def match_vertex_format(program:ShaderProgram,properties:Iterable[str|dict])->dict:
    available={(x["usage"],x["usage_index"]) for x in infer_meb_semantics(properties)}
    required={semantic_key(x) for x in program.inputs}
    missing=sorted(({"usage":u,"index":i} for u,i in required-available),key=lambda x:(x["usage"],x["index"]))
    unused=sorted(({"usage":u,"index":i} for u,i in available-required),key=lambda x:(x["usage"],x["index"]))
    prop_list=list(properties)
    bindings=vertex_attribute_bindings(program,prop_list)
    matched=len(required)-len(missing)
    skin_shader={(x.get("usage"),x.get("index")) for x in program.inputs if x.get("usage") in {"BLENDWEIGHT","BLENDINDICES"}}
    skin_contract=skinning_contract(prop_list)
    shader_skinned=bool(skin_shader)
    skin_compatible=(shader_skinned == skin_contract["skinned"]) and skin_contract["valid"]
    skin_score=1.0 if skin_compatible else 0.0
    score=0.45*(matched/len(required) if required else 1.0)+0.35*bindings["score"]+0.20*skin_score
    return {"valid":bindings["valid"] and not missing and skin_compatible,"required":len(required),"available":len(available),"matched":matched,"missing":missing,"unused":unused,"score":score,"available_semantics":sorted(({"usage":u,"index":i} for u,i in available),key=lambda x:(x["usage"],x["index"])),"vertex_bindings":bindings["bindings"],"skinning":{**skin_contract,"shader_skinned":shader_skinned,"compatible":skin_compatible}}

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
        candidates.append({"vertex_offset":vs.offset,"pixel_offset":pixel.offset,"score":0.65*interface["score"]+0.35*vf["score"],"interface":interface,"vertex_format":vf,"vertex_bindings":vertex_attribute_bindings(vs,properties)["bindings"],"pixel_samplers":list(pixel.samplers)})
    if not candidates: return None
    ranked=sorted(candidates,key=lambda x:(-x["score"],-x["interface"]["score"],-x["vertex_format"]["score"],x["vertex_offset"]))
    best=ranked[0]
    evidence=(best["score"],best["interface"]["score"],best["vertex_format"]["score"])
    tied=[x for x in ranked if (x["score"],x["interface"]["score"],x["vertex_format"]["score"])==evidence]
    result=dict(best)
    result["selection_status"]="ambiguous" if len({x["vertex_offset"] for x in tied})>1 else "unique"
    result["ambiguous_candidates"]=[{"vertex_offset":x["vertex_offset"],"pixel_offset":x["pixel_offset"],"score":x["score"]} for x in tied] if result["selection_status"]=="ambiguous" else []
    return result
