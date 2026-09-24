"""Link SHIFT BMT materials to HLSL samplers and D3D9 FXO reflection.

BMT names texture parameters; FX source names samplers and declares their
filtering/addressing rules; FXO CTAB reflection supplies D3D9 sampler registers.
"""
from __future__ import annotations
import json
import re
import hashlib
from pathlib import Path
from typing import Iterable
from shader_ir import parse_shader_blobs
from shader_interface import pair_selected_pixel
from uniform_linker import link_selected_pair, reflect_constants
from specialization import feature_indicators, feature_signature_score, material_specialisations
from shader_backend import translate_pair_blob
from shader_permutation_identity import build_shader_permutation_identity

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
        # A BMT texture parameter may exist even when D3D9 optimizes its sampler out.
        # Count actual sampling calls in source; declarations alone do not make a
        # sampler mandatory for a compiled permutation.
        body=text[m.end():]
        usage_count=len(re.findall(r"\b(?:tex\w*|sample\w*)\s*\(\s*"+re.escape(m.group(2))+r"\b", body, re.I))
        out.append({
            "sampler_type": m.group(1), "sampler": m.group(2),
            "texture_parameter": texture, "min_filter": get("MinFilter"),
            "mag_filter": get("MagFilter"), "mip_filter": get("MipFilter"),
            "address_u": get("AddressU"), "address_v": get("AddressV"),
            "address_w": get("AddressW"), "lod_bias": int(get("MipMapLODBias", "0")),
            "max_anisotropy": int(get("MaxAnisotropy", "1")),
            "usage_count": usage_count,
            "source_used": usage_count > 0,
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

def _selection_evidence_key(candidate: dict) -> tuple:
    """Return only evidence-bearing ranking fields; exclude file/offset identity."""
    return (
        bool(candidate.get("exact")),
        int(candidate.get("score", 0)),
        bool(candidate.get("vertex_pair_valid", False)),
        float(candidate.get("vertex_pair_score", 0.0)),
        float(candidate.get("uniform_coverage", 0.0)),
        float(candidate.get("specialization_score", 0.0)),
        len(candidate.get("specialization_contradicted", [])),
        len(candidate.get("specialization_unexpected", [])),
        len(candidate.get("uniform_matches", [])),
    )


def _selection_sort_key(candidate: dict) -> tuple:
    evidence = _selection_evidence_key(candidate)
    return (
        -int(evidence[0]),
        -evidence[1],
        -int(evidence[2]),
        -evidence[3],
        -evidence[4],
        -evidence[5],
        evidence[6],
        evidence[7],
        -evidence[8],
        candidate["file"],
        candidate["program_offset"],
    )


def link_material(material: dict, fx_source: str | bytes, *, fxo_candidates: Iterable[tuple[str, bytes]] = (), texture_paths: Iterable[str] = (), vertex_properties: Iterable[str | dict] = ()) -> dict:
    params = _material_params(material)
    samplers = parse_fx_samplers(fx_source)
    specialization = feature_indicators(material, fx_source)
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
    sampler_by_texture={s["texture_parameter"]:s for s in samplers}
    expected={b["sampler"] for b in bindings if b.get("binding")=="material-texture" and sampler_by_texture.get(b["texture_parameter"],{}).get("usage_count",0)>0}
    param_names=set(params)
    env_sampler=sampler_by_texture.get("environmentTexture")
    if env_sampler and env_sampler.get("usage_count",0)>0 and "motionBlurTexture" not in param_names:
        expected.add("environmentMap")
    material_uniform_names={n for n,p in params.items() if "TEXTURE" not in str(p.get("type") or p.get("resource_type") or "").upper()}
    fxo=[]
    fxo_payloads={}
    for name,data in fxo_candidates:
        programs=reflect_fxo(data)
        for p in (x for x in programs if x["stage"]=="pixel"):
            names={s["name"] for s in p["samplers"]}
            sampler_score=len(expected & names)
            wrong_camera="motionBlurMap" in names and "motionBlurTexture" not in param_names
            exact=expected <= names and not wrong_camera
            if not wrong_camera and (sampler_score or not expected):
                pair=pair_selected_pixel(data,p["offset"],properties=vertex_properties) if exact else None
                pair_score=pair["score"] if pair else 0.0
                pair_ok=bool(pair and pair.get("interface",{}).get("valid") and pair.get("vertex_format",{}).get("valid",True))
                pair_selection_status=pair.get("selection_status","unique") if pair else "none"
                offsets=[p["offset"]] + ([pair["vertex_offset"]] if pair else [])
                all_constants=set()
                for off in offsets:
                    all_constants.update(x["name"] for x in reflect_constants(data,off) if x.get("register_set")==2 and x.get("name"))
                uniform_matches=sorted(material_uniform_names & all_constants)
                uniform_score=(len(uniform_matches)/len(material_uniform_names)) if material_uniform_names else 1.0
                feature_score=feature_signature_score(material, constants=all_constants, samplers=names)
                pixel_sha256=hashlib.sha256(data[p["offset"]:p["end"]]).hexdigest()
                vertex_sha256=None
                pair_sha256=None
                permutation_identity=None
                if pair:
                    try:
                        for vb in parse_shader_blobs(data):
                            if vb.offset==pair["vertex_offset"]:
                                vertex_sha256=hashlib.sha256(data[vb.offset:vb.end]).hexdigest()
                                pair_sha256=hashlib.sha256(data[vb.offset:vb.end]+data[p["offset"]:p["end"]]).hexdigest()
                                try:
                                    permutation_identity=build_shader_permutation_identity(
                                        data,
                                        vertex_offset=int(vb.offset),
                                        pixel_offset=int(p["offset"]),
                                    )
                                except Exception:
                                    permutation_identity=None
                                break
                    except Exception:
                        pass
                fxo_payloads[(name,p["offset"])]=data
                fxo.append({
                    "file":name,"program_offset":p["offset"],"samplers":p["samplers"],
                    "score":sampler_score,"expected_count":len(expected),"exact":exact,
                    "uniform_matches":uniform_matches,"uniform_expected":len(material_uniform_names),
                    "uniform_coverage":uniform_score,
                    "vertex_pair_score":pair_score,"vertex_pair_valid":pair_ok,
                    "vertex_pair_selection_status":pair_selection_status,
                    "pixel_sha256":pixel_sha256,
                    "vertex_sha256":vertex_sha256,
                    "pair_sha256":pair_sha256,
                    "permutation_identity":permutation_identity,
                    "specialization_score":feature_score["score"],
                    "specialization_matched":feature_score["matched"],
                    "specialization_contradicted":feature_score["contradicted"],
                    "specialization_unexpected":feature_score.get("unexpected",[]),
                })
    seen=set(); uniq=[]
    for x in fxo:
        k=(x["file"],x["program_offset"])
        if k not in seen:
            seen.add(k); uniq.append(x)
    fxo=sorted(uniq, key=_selection_sort_key)
    best=fxo[0] if fxo else None
    selection_status="none"
    ambiguous_candidates=[]
    if best:
        top=[x for x in fxo if _selection_evidence_key(x) == _selection_evidence_key(best)]
        pair_ids={(x.get("file"), x.get("program_offset"), x.get("vertex_sha256"), x.get("pair_sha256")) for x in top}
        # A tie is still ambiguous when byte hashes are unavailable. The
        # stable file/program offsets are enough to distinguish candidates.
        ambiguous_candidates=top if len(pair_ids)>1 else []
        pair_ambiguous=best.get("vertex_pair_selection_status")=="ambiguous"
        selection_status="ambiguous" if ambiguous_candidates or pair_ambiguous else ("unique" if best.get("vertex_pair_valid") else "heuristic")
    shader_pair=None
    linked_shader_pair=None
    linked_shader_error=None
    uniform_binding=None
    if best and best["exact"]:
        regmap={s["name"]:s["register"] for s in best["samplers"]}
        for b in bindings:
            if b["sampler"] in regmap: b["d3d9_sampler_register"]=regmap[b["sampler"]]
        payload=fxo_payloads.get((best["file"],best["program_offset"]))
        if payload is not None:
            shader_pair=pair_selected_pixel(payload,best["program_offset"],properties=vertex_properties)
            if shader_pair and shader_pair.get("selection_status") == "unique":
                try:
                    linked_shader_pair = translate_pair_blob(
                        payload,
                        int(shader_pair["vertex_offset"]),
                        int(shader_pair["pixel_offset"]),
                        vertex_properties=tuple(vertex_properties),
                    )
                except Exception as exc:
                    linked_shader_error = f"{type(exc).__name__}: {exc}"
            uniform_binding=link_selected_pair(material,payload,shader_pair)
    return {"format":"SHIFT.MaterialBinding/1","material":material.get("name"),"shader":material.get("shader"),
            "technique":material.get("technique"),"specialization":specialization,"bindings":bindings,"fxo_candidates":fxo,
            "selected_fxo":best if best and best["exact"] else None,
            "permutation_identity":(best or {}).get("permutation_identity") if best else None,
            "selection_status":selection_status,
            "selection_evidence":(
                {"rank":list(_selection_evidence_key(best)), "ambiguous_count":len(ambiguous_candidates)}
                if best else None
            ),
            "ambiguous_candidates":ambiguous_candidates[:8],
            "shader_pair":shader_pair,
            "linked_shader_pair":linked_shader_pair,
            "linked_shader_error":linked_shader_error,
            "uniform_binding":uniform_binding if best and best["exact"] and shader_pair else None,
            "unresolved_textures":sorted(set(unresolved))}

def link_from_files(material_json: str | Path, fx_source: str | Path, *, fxo_dir: str | Path | None = None, texture_paths: Iterable[str] = (), vertex_properties: Iterable[str | dict] = ()) -> dict:
    material=json.loads(Path(material_json).read_text(encoding="utf-8"))
    if "material" in material: material=material["material"]
    candidates=[]
    if fxo_dir:
        for p in sorted(Path(fxo_dir).glob("*.fxo")): candidates.append((p.name,p.read_bytes()))
    return link_material(material, Path(fx_source).read_bytes(), fxo_candidates=candidates, texture_paths=texture_paths, vertex_properties=vertex_properties)
