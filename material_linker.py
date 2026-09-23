"""Link SHIFT BMT materials to HLSL samplers and D3D9 FXO reflection.

BMT names texture parameters; FX source names samplers and declares their
filtering/addressing rules; FXO CTAB reflection supplies D3D9 sampler registers.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Iterable
from shader_ir import parse_shader_blobs
from shader_interface import pair_selected_pixel

def parse_fx_samplers(source: str | bytes) -> list[dict]:
    text = source.decode("utf-8", "replace") if isinstance(source, bytes) else source
    out = []
    pat = re.compile(r"\b(sampler(?:2D|CUBE|3D)?)\s+(\w+)\s*:\s*(?:SAMPLER|sample)\s*<(?P<meta>.*?)>\s*=\s*sampler_state", re.I | re.S)
    for m in pat.finditer(text):
        meta = m.group("meta")
        def get(key: str, default=None):
            q = re.search(rf"\b{re.escape(key)}\s*=\s*\"([^\"]*)\"", meta, re.I)
            return q.group(1) if q else default
        texture = get("SamplerTexture")
        if not texture: continue
        out.append({
            "sampler_type": m.group(1), "sampler": m.group(2),
            "texture_parameter": texture, "min_filter": get("MinFilter"),
            "mag_filter": get("MagFilter"), "mip_filter": get("MipFilter"),
            "address_u": get("AddressU"), "address_v": get("AddressV"),
            "address_w": get("AddressW"), "lod_bias": int(get("MipMapLODBias", "0")),
            "max_anisotropy": int(get("MaxAnisotropy", "1")),
            "srgb": "SET_SRGB_TEXTURE" in meta, "linear": "SET_LINEAR_TEXTURE" in meta,
        })
    return out

def _material_params(material: dict) -> dict[str, dict]:
    return {p["name"]: p for p in material.get("shaderparams", []) if p.get("name")}

def _norm_path(path: str) -> str:
    return path.replace("\\", "/").lower()

def _texture_lookup(texture_paths: Iterable[str]) -> dict[str, str]:
    return {_norm_path(p): p for p in texture_paths}

def reflect_fxo(data: bytes) -> list[dict]:
    return [{"offset":b.offset,"end":b.end,"stage":b.stage,"version":[b.major,b.minor],
             "instruction_count":b.instruction_count,"samplers":b.ctab_samplers,"constants":b.ctab_constants}
            for b in parse_shader_blobs(data)]

def link_material(material: dict, fx_source: str | bytes, *, fxo_candidates: Iterable[tuple[str, bytes]] = (), texture_paths: Iterable[str] = (), vertex_properties: Iterable[str | dict] = ()) -> dict:
    params = _material_params(material)
    samplers = parse_fx_samplers(fx_source)
    textures = _texture_lookup(texture_paths)
    bindings=[]; unresolved=[]
    for s in samplers:
        p=params.get(s["texture_parameter"])
        if p is None:
            bindings.append({**s,"binding":"external-or-specialised"}); continue
        value=p.get("value")
        resolved=textures.get(_norm_path(value)) if isinstance(value,str) else None
        b={**s,"texture":value,"texture_resolved":resolved,"binding":"material-texture" if resolved else "unresolved-texture"}
        if resolved is None: unresolved.append(value)
        bindings.append(b)
    expected={b["sampler"] for b in bindings if b.get("binding")=="material-texture"}
    param_names=set(params)
    if "environmentTexture" in {s["texture_parameter"] for s in samplers} and "motionBlurTexture" not in param_names:
        expected.add("environmentMap")
    fxo=[]
    fxo_payloads={}
    for name,data in fxo_candidates:
        for p in (p for p in reflect_fxo(data) if p["stage"]=="pixel"):
            names={s["name"] for s in p["samplers"]}
            score=len(expected & names)
            wrong_camera="motionBlurMap" in names and "motionBlurTexture" not in param_names
            exact=expected <= names and not wrong_camera
            if score and not wrong_camera:
                fxo_payloads[(name,p["offset"])]=data
                fxo.append({"file":name,"program_offset":p["offset"],"samplers":p["samplers"],
                            "score":score,"expected_count":len(expected),"exact":exact})
    seen=set(); uniq=[]
    for x in fxo:
        k=(x["file"],x["program_offset"])
        if k not in seen: seen.add(k); uniq.append(x)
    fxo=sorted(uniq,key=lambda x:(-int(x["exact"]),-x["score"],x["file"],x["program_offset"]))
    best=fxo[0] if fxo else None
    shader_pair=None
    if best and best["exact"]:
        regmap={s["name"]:s["register"] for s in best["samplers"]}
        for b in bindings:
            if b["sampler"] in regmap: b["d3d9_sampler_register"]=regmap[b["sampler"]]
        payload=fxo_payloads.get((best["file"],best["program_offset"]))
        if payload is not None:
            shader_pair=pair_selected_pixel(payload,best["program_offset"],properties=vertex_properties)
    return {"format":"SHIFT.MaterialBinding/1","material":material.get("name"),"shader":material.get("shader"),
            "technique":material.get("technique"),"bindings":bindings,"fxo_candidates":fxo,
            "selected_fxo":best if best and best["exact"] else None,
            "shader_pair":shader_pair,
            "unresolved_textures":sorted(set(unresolved))}

def link_from_files(material_json: str | Path, fx_source: str | Path, *, fxo_dir: str | Path | None = None, texture_paths: Iterable[str] = (), vertex_properties: Iterable[str | dict] = ()) -> dict:
    material=json.loads(Path(material_json).read_text(encoding="utf-8"))
    if "material" in material: material=material["material"]
    candidates=[]
    if fxo_dir:
        for p in sorted(Path(fxo_dir).glob("*.fxo")): candidates.append((p.name,p.read_bytes()))
    return link_material(material, Path(fx_source).read_bytes(), fxo_candidates=candidates, texture_paths=texture_paths, vertex_properties=vertex_properties)
