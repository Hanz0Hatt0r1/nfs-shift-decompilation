from __future__ import annotations
from typing import Iterable
from shader_ir import parse_shader_blobs

RESOURCE_TYPES={"EPT_F32","EPT_VEC2","EPT_VEC3","EPT_VEC4","EPT_INT","EPT_BOOL"}

def _params(material:dict)->dict[str,dict]:
    return {p["name"]:p for p in material.get("shaderparams",[]) if p.get("name")}

def _value_components(param:dict)->int:
    typ=str(param.get("type") or param.get("resource_type") or "").upper()
    value=param.get("value")
    if isinstance(value,list): return len(value)
    if typ.endswith("VEC4"): return 4
    if typ.endswith("VEC3"): return 3
    if typ.endswith("VEC2"): return 2
    return 1

def _ctab_type_label(info:dict)->str:
    t=info.get("type") or {}
    cls=int(t.get("class",0)); typ=int(t.get("type",0)); rows=int(t.get("rows",1)); cols=int(t.get("columns",1))
    if cls==3 and rows==4 and cols==4: return "float4x4"
    if cls==1: return f"float{cols}" if cols>1 else "float"
    if cls==0 and typ==3: return "float"
    return f"class{cls}:type{typ}:{rows}x{cols}"

def reflect_constants(data:bytes, program_offset:int)->list[dict]:
    for b in parse_shader_blobs(data):
        if b.offset==program_offset:
            return list(b.ctab_constants)
    return []

def link_material_uniforms(material:dict, data:bytes, program_offsets:Iterable[int]) -> dict:
    params=_params(material)
    programs=[]
    seen=set()
    for off in program_offsets:
        if off in seen: continue
        seen.add(off)
        for c in reflect_constants(data,off):
            programs.append({"program_offset":off,"stage":next((b.stage for b in parse_shader_blobs(data) if b.offset==off),"unknown"),"constant":c})
    by_name={}
    for p in programs:
        name=p["constant"].get("name")
        if name: by_name.setdefault(name,[]).append(p)
    bindings=[]; unresolved=[]; optimized_out=[]
    for name,param in params.items():
        typ=str(param.get("type") or param.get("resource_type") or "").upper()
        if "TEXTURE" in typ: continue
        matches=by_name.get(name,[])
        if not matches:
            optimized_out.append({"name":name,"type":typ,"value":param.get("value")})
            continue
        value_count=_value_components(param)
        for m in matches:
            c=m["constant"]
            item={"name":name,"type":typ,"value":param.get("value"),"program_offset":m["program_offset"],"stage":m["stage"],
                  "register_set":c.get("register_set"),"register_index":c.get("register_index"),"register_count":c.get("register_count"),
                  "ctab_type":_ctab_type_label(c)}
            expected=int(c.get("register_count",0))
            item["component_count"]=value_count
            item["binding"]="material-constant" if c.get("register_set")==2 else "unexpected-register-set"
            if expected and value_count>expected*4: item["shape_warning"]="value-exceeds-register-range"
            bindings.append(item)
    return {"format":"SHIFT.MaterialUniformBinding/1","bindings":bindings,"optimized_out_or_unreflected":optimized_out,"unresolved":[]}

def link_selected_pair(material:dict, data:bytes, shader_pair:dict|None) -> dict|None:
    if not shader_pair: return None
    return link_material_uniforms(material,data,[shader_pair["vertex_offset"],shader_pair["pixel_offset"]])
