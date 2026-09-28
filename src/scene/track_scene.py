"""Track-scene aggregation on top of the verified SGB chunk index."""
from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any, Iterable


FORMAT = "SHIFT.TrackScene/1"


def _norm(value: str) -> str:
    value = str(value or "").replace("\\", "/").lower()
    while "//" in value:
        value = value.replace("//", "/")
    return value.lstrip("/")


def _resolve(ref: str, resources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    key = _norm(ref)
    exact = [
        r for r in resources
        if _norm(r.get("path") or r.get("name") or "") == key
    ]
    if exact:
        return exact
    base = PurePosixPath(key).name
    return [
        r for r in resources
        if PurePosixPath(_norm(r.get("path") or r.get("name") or "")).name == base
    ]


def build_track_scene_manifest(
    sgb: dict[str, Any],
    resources: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Create a render-resource manifest without inventing SGB node semantics."""
    resources = list(resources)
    refs = list(sgb.get("resource_refs", []) or [])
    buckets: dict[str, list[dict[str, Any]]] = {}
    unresolved: list[dict[str, Any]] = []

    for ref in refs:
        item = dict(ref)
        matches = _resolve(ref.get("path", ""), resources)
        item["resolved"] = matches
        if not matches:
            unresolved.append(item)
        buckets.setdefault(ref.get("kind", "unknown"), []).append(item)

    meshes = buckets.get("geometry", [])
    materials = buckets.get("material", []) + buckets.get("material-source", [])
    textures = buckets.get("texture", [])
    collisions = buckets.get("collision", [])
    shader_sources = buckets.get("shader-source", []) + buckets.get("shader-cache", [])

    return {
        "format": FORMAT,
        "source": {
            "format": sgb.get("format"),
            "header_hex": sgb.get("header_hex"),
            "chunk_count": sgb.get("chunk_count", 0),
            "container_end": sgb.get("container_end"),
            "trailing_bytes": sgb.get("trailing_bytes", 0),
        },
        "placement": {
            "status": "unknown",
            "reason": "SGB NODE/FLAT/SUMM payload semantics are not yet proven",
        },
        "resource_refs": refs,
        "resource_ref_counts": sgb.get("resource_ref_counts", {}),
        "geometry": meshes,
        "materials": materials,
        "textures": textures,
        "collisions": collisions,
        "shaders": shader_sources,
        "unresolved": unresolved,
        "stats": {
            "references": len(refs),
            "unique_resolved_refs": sum(1 for ref in refs if ref.get("resolved")),
            "unresolved_refs": len(unresolved),
            "geometry_refs": len(meshes),
            "material_refs": len(materials),
            "texture_refs": len(textures),
            "collision_refs": len(collisions),
        },
    }
