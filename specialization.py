from __future__ import annotations
import re
from typing import Iterable

def parse_specialisation_params(source: str | bytes) -> list[dict]:
    text = source.decode("utf-8", "replace") if isinstance(source, bytes) else source
    pat = re.compile(r"SPECIALISATION_PARAM\\s*\\(\\s*([A-Za-z_]\\w*)\\s*,\\s*\"([^\"]*)\"\\s*,\\s*\"([A-Z][A-Z0-9_]*)\"", re.I)
    out=[]
    seen=set()
    for m in pat.finditer(text):
        flag=m.group(3).upper()
        if flag in seen: continue
        seen.add(flag)
        out.append({"variable":m.group(1),"label":m.group(2),"flag":flag})
    return out

def material_specialisations(material: dict) -> list[str]:
    explicit=material.get("specializations") or material.get("specialisations") or []
    flags={str(x).upper() for x in explicit if isinstance(x,str)}
    params={p.get("name"):p for p in material.get("shaderparams",[]) if p.get("name")}
    # These two inferences are data-backed by the stock Bodywork BMTs: the
    # corresponding parameter groups only occur when the shader feature is requested.
    if "fresnelFactor" in params: flags.add("USE_FRESNEL")
    if any(x in params for x in ("metallicColour","metallicPower","fleckMaterialColour","fleckScale","fleckLocality","fleckShininess")):
        flags.add("METALLIC")
    if "scratchControlTexture" in params or "dirtBasis" in params: flags.add("DIRT_SCRATCH")
    if "noiseTexture" in params: flags.add("METALFLAKE")
    return sorted(flags)

def feature_indicators(material: dict, fx_source: str | bytes) -> dict:
    definitions=parse_specialisation_params(fx_source)
    flags=set(material_specialisations(material))
    return {"requested":sorted(flags),"declared":definitions,
            "missing_declarations":sorted(flags-{x['flag'] for x in definitions}),
            "unexpected_declarations":sorted({x['flag'] for x in definitions}-flags)}

def feature_signature_score(material: dict, *, constants: Iterable[str], samplers: Iterable[str]) -> dict:
    flags=set(material_specialisations(material)); c={str(x) for x in constants}; s={str(x) for x in samplers}
    evidence={
      "USE_FRESNEL": int("fresnelFactor" in c),
      "METALLIC": int(any(x in c for x in ("metallicColour","metallicPower","fleckMaterialColour","fleckScale","fleckLocality","fleckShininess"))),
      "DIRT_SCRATCH": int("scratchControlMap" in s and "dirtBasis" in c),
      "METALFLAKE": int(any("fleck" in x.lower() for x in c) or "noiseMap" in s),
      "NORMAL_MAPPING": int("normalMapL2" in s),
      "USE_LAYER_2": int(any(x in s for x in ("diffuseMapL2","specularMapL2","normalMapL2","fresnelMapL2"))),
    }
    matched=[]; contradicted=[]
    for flag in flags:
        if flag in evidence and evidence[flag]: matched.append(flag)
        elif flag in evidence and not evidence[flag]: contradicted.append(flag)
    unexpected=sorted(flag for flag,active in evidence.items() if active and flag not in flags)
    requested_score=len(matched)/len(flags) if flags else 1.0
    penalty=len(unexpected)/(len(unexpected)+len(flags)+1)
    score=max(0.0,requested_score-penalty)
    return {"requested":sorted(flags),"matched":sorted(matched),"contradicted":sorted(contradicted),"unexpected":unexpected,"score":score,"evidence":evidence}