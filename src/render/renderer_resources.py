"""Content-addressed renderer resource planning for SHIFT textures and samplers."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

from texture_pipeline import build_texture_contract


FORMAT = "SHIFT.RenderResources/1"


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _texture_identity(row: dict[str, Any], contract: dict[str, Any]) -> str:
    source_sha = str(row.get("sha256") or "")
    if source_sha:
        return "tex_" + source_sha[:24]
    return "tex_" + _digest(contract.get("dds", {}))[:24]


def _sampler_identity(binding: dict[str, Any], contract: dict[str, Any]) -> str:
    return "smp_" + _digest(contract.get("sampler", {}))[:24]


def _binding_identity(texture_id: str, sampler_id: str, color_space: str) -> str:
    return "tb_" + _digest({
        "texture": texture_id,
        "sampler": sampler_id,
        "color_space": color_space,
    })[:24]


def _capability_check(contract: dict[str, Any], extensions: set[str]) -> tuple[bool, list[str]]:
    reasons = [
        reason
        for reason in contract.get("blocking_reasons", [])
        if not (reason.startswith("gpu-extension-required:") and
                reason.split(":", 1)[1] in extensions)
    ]
    required = contract.get("dds", {}).get("required_extension")
    if required and required not in extensions:
        reasons.append("runtime-extension-missing:" + required)
    return not reasons, list(dict.fromkeys(reasons))


def build_resource_index(
    manifest_rows: Iterable[dict[str, Any]],
    texture_bindings: Iterable[dict[str, Any]] = (),
    *,
    extensions: Iterable[str] = (),
) -> dict[str, Any]:
    extset = {str(x) for x in extensions}
    textures: dict[str, dict[str, Any]] = {}
    samplers: dict[str, dict[str, Any]] = {}
    bindings: dict[str, dict[str, Any]] = {}
    unresolved: list[dict[str, Any]] = []

    rows = list(manifest_rows)
    by_path = {
        str(row.get("path", "")).replace("\\", "/").lower(): row
        for row in rows
        if row.get("path")
    }

    for row in rows:
        path = str(row.get("path", ""))
        if not path.lower().endswith(".dds"):
            continue
        metadata = dict(row.get("analysis") or {})
        if metadata.get("format") != "DDS":
            continue
        contract = build_texture_contract(metadata, {})
        texture_id = _texture_identity(row, contract)
        ready, reasons = _capability_check(contract, extset)
        record = {
            "id": texture_id,
            "path": path,
            "sha256": row.get("sha256"),
            "contract": contract,
            "gpu_ready": ready,
            "blocking_reasons": reasons,
        }
        previous = textures.get(texture_id)
        if previous and previous.get("sha256") not in (None, row.get("sha256")):
            unresolved.append({
                "kind": "texture-id-collision",
                "id": texture_id,
                "paths": [previous.get("path"), path],
            })
        else:
            textures[texture_id] = record

    for binding in texture_bindings:
        if binding.get("binding_source") != "fxo-ctab":
            unresolved.append({
                "kind": "unresolved-texture-binding",
                "ref": binding.get("ref"),
            })
            continue
        ref = str(binding.get("ref") or "").replace("\\", "/").lower()
        row = by_path.get(ref)
        if row is None:
            basename = ref.rsplit("/", 1)[-1]
            hits = [r for p, r in by_path.items() if p.rsplit("/", 1)[-1] == basename]
            row = hits[0] if len(hits) == 1 else None
        if row is None:
            unresolved.append({"kind": "texture-resource-missing", "ref": binding.get("ref")})
            continue

        metadata = dict(row.get("analysis") or {})
        contract = build_texture_contract(metadata, binding)
        texture_id = _texture_identity(row, contract)
        sampler_id = _sampler_identity(binding, contract)
        if texture_id not in textures:
            ready, reasons = _capability_check(contract, extset)
            textures[texture_id] = {
                "id": texture_id,
                "path": row.get("path"),
                "sha256": row.get("sha256"),
                "contract": contract,
                "gpu_ready": ready,
                "blocking_reasons": reasons,
            }

        sampler = samplers.setdefault(
            sampler_id,
            {
                "id": sampler_id,
                "state": contract.get("sampler"),
            },
        )
        sampler.setdefault("uses", 0)
        sampler["uses"] += 1

        binding_ready, binding_reasons = _capability_check(contract, extset)
        binding_id = _binding_identity(texture_id, sampler_id, contract.get("color_space", "unspecified"))
        bindings[binding_id] = {
            "id": binding_id,
            "texture_id": texture_id,
            "sampler_id": sampler_id,
            "color_space": contract.get("color_space", "unspecified"),
            "material_parameter": binding.get("material_parameter"),
            "d3d9_sampler_register": binding.get("d3d9_sampler_register"),
            "gpu_ready": textures[texture_id]["gpu_ready"] and binding_ready,
            "blocking_reasons": list(dict.fromkeys(
                textures[texture_id]["blocking_reasons"]
                + binding_reasons
            )),
        }

    return {
        "format": FORMAT,
        "extensions": sorted(extset),
        "textures": sorted(textures.values(), key=lambda x: x["id"]),
        "samplers": sorted(samplers.values(), key=lambda x: x["id"]),
        "bindings": sorted(bindings.values(), key=lambda x: x["id"]),
        "unresolved": unresolved,
        "stats": {
            "textures": len(textures),
            "samplers": len(samplers),
            "bindings": len(bindings),
            "gpu_ready_textures": sum(1 for x in textures.values() if x["gpu_ready"]),
            "gpu_ready_bindings": sum(1 for x in bindings.values() if x["gpu_ready"]),
            "unresolved": len(unresolved),
        },
    }
