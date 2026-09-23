from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

SCHEMA = "SHIFT.MaterialShaderLink/1"
REGISTER_SETS = {0: "bool", 1: "int4", 2: "float4", 3: "sampler"}


def norm_name(value: str | None) -> str:
    value = str(value or "").strip().lower()
    value = re.sub(r"\[[0-9]+\]$", "", value)
    return re.sub(r"[^a-z0-9]", "", value)


def _stem(value: str | None) -> str:
    value = str(value or "").replace("\\", "/")
    return norm_name(Path(value).stem)


def _records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("resources", "rows", "analyses"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return []


def _shader_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("shaders"), list):
        return payload["shaders"]
    if isinstance(payload, dict) and isinstance(payload.get("programs"), list):
        return payload["programs"]
    if isinstance(payload, list):
        return payload
    return []


def _material(record: dict[str, Any]) -> dict[str, Any]:
    return (record.get("analysis") or {}).get("material") or record.get("material") or {}


def _shader_candidates(material: dict[str, Any], shaders: list[dict[str, Any]], archive: str | None) -> list[dict[str, Any]]:
    ref = material.get("shader")
    if not ref:
        return []
    target = _stem(ref)
    out = []
    for row in shaders:
        paths = [row.get("path"), row.get("source")]
        if any(_stem(x) == target for x in paths if x):
            out.append(row)
    if archive:
        same = [x for x in out if x.get("archive") == archive]
        if same:
            out = same
    return out


def _bindings(material: dict[str, Any], shader: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    constants = shader.get("ctab") or []
    by_name: dict[str, list[dict[str, Any]]] = {}
    for c in constants:
        key = norm_name(c.get("name"))
        if key:
            by_name.setdefault(key, []).append(c)

    constant_bindings = []
    sampler_bindings = []
    unresolved = []
    for index, param in enumerate(material.get("shaderparams", []) or []):
        name = param.get("name")
        key = norm_name(name)
        hits = by_name.get(key, []) if key else []
        if len(hits) == 1:
            c = hits[0]
            reg_set = c.get("register_set")
            binding = {
                "param_index": index,
                "param": name,
                "constant": c.get("name"),
                "register_set": reg_set,
                "register_set_name": REGISTER_SETS.get(reg_set, f"unknown:{reg_set}"),
                "register_index": c.get("register_index"),
                "register_count": c.get("register_count"),
                "type": c.get("type"),
                "confidence": "exact-name",
            }
            if reg_set == 3:
                sampler_bindings.append(binding)
            else:
                constant_bindings.append(binding)
        elif len(hits) > 1:
            unresolved.append({
                "param_index": index, "param": name,
                "reason": "ambiguous-ctab-name",
                "candidates": [x.get("name") for x in hits],
            })
        else:
            unresolved.append({
                "param_index": index, "param": name,
                "reason": "no-ctab-name-match",
            })
    return constant_bindings, sampler_bindings, unresolved


def build_material_shader_links(records: list[dict[str, Any]], shaders: list[dict[str, Any]]) -> dict[str, Any]:
    materials = [
        r for r in records
        if str(r.get("path", "")).lower().endswith(".bmt")
        and ((_material(r)))
    ]
    links = []
    stats = {"materials": len(materials), "shader_matched": 0, "constant_bindings": 0, "sampler_bindings": 0, "unresolved_params": 0}

    for record in materials:
        mat = _material(record)
        candidates = _shader_candidates(mat, shaders, record.get("archive"))
        item = {
            "material": {"archive": record.get("archive"), "path": record.get("path")},
            "shader_ref": mat.get("shader"),
            "shader_candidates": [{"archive": x.get("archive"), "path": x.get("path")} for x in candidates],
            "bindings": {"constants": [], "samplers": [], "unresolved": []},
        }
        if len(candidates) == 1:
            stats["shader_matched"] += 1
            constants, samplers, unresolved = _bindings(mat, candidates[0])
            item["bindings"] = {"constants": constants, "samplers": samplers, "unresolved": unresolved}
            stats["constant_bindings"] += len(constants)
            stats["sampler_bindings"] += len(samplers)
            stats["unresolved_params"] += len(unresolved)
            item["confidence"] = "exact-name"
        elif len(candidates) > 1:
            item["confidence"] = "ambiguous-shader"
        else:
            item["confidence"] = "unresolved-shader"
    links.append(item)

    return {"schema": SCHEMA, "version": 1, "links": links, "stats": stats}


def main() -> int:
    ap = argparse.ArgumentParser(description="Link SHIFT BMT shader params to D3D9 CTAB registers")
    ap.add_argument("resource_analysis")
    ap.add_argument("shader_report")
    ap.add_argument("output")
    args = ap.parse_args()
    records = _records(json.loads(Path(args.resource_analysis).read_text(encoding="utf-8")))
    shaders = _shader_rows(json.loads(Path(args.shader_report).read_text(encoding="utf-8")))
    result = build_material_shader_links(records, shaders)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["stats"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
