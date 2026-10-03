"""Fail-closed exact-path preflight for external SGB render resources.

The legacy render pipeline supports basename fallback for older VHF workflows.
Process 3 must not use that fallback as resource identity proof.  This module
walks the exact resource closure needed by SGB render instances before the
legacy renderer is called.  Only unique normalized paths (plus the already
proven MTX->BMT alias) are admitted.
"""
from __future__ import annotations

import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Mapping, Sequence

from meb_format import read_meb
from imb_neutral_geometry import build_imb_neutral_geometry
from imx_neutral_geometry import build_imx_neutral_geometry
from resource_formats import parse_bmt_material

FORMAT = "SHIFT.OfflineExactIRResourceClosure/1"


def _norm(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip().lower().lstrip("./")


def _candidates(ref: Any) -> list[str]:
    value = _norm(ref)
    if not value:
        return []
    candidates = [value]
    if value.endswith(".mtx"):
        candidates.append(value[:-4] + ".bmt")
    return candidates


def _load_raw(root: Path, row: Mapping[str, Any]) -> bytes:
    relative = row.get("raw")
    if not relative:
        raise ValueError("IR manifest row has no raw payload")
    return (root / str(relative)).read_bytes()


def _semantic_refs(root: Path, row: Mapping[str, Any]) -> list[dict[str, str]]:
    path = str(row.get("path") or "")
    ext = Path(path).suffix.lower()
    data = _load_raw(root, row)
    refs: list[dict[str, str]] = []

    def add(value: Any, kind: str) -> None:
        text = str(value or "").replace("\\", "/").strip()
        if text and not any(existing["ref"] == text and existing["kind"] == kind for existing in refs):
            refs.append({"ref": text, "kind": kind})

    if ext == ".meb":
        mesh = read_meb(data)
        for primitive in mesh.primitives:
            add(primitive.material, "material")
    elif ext == ".imb":
        neutral = build_imb_neutral_geometry(data)
        if neutral.get("ready") is not True:
            reasons = ";".join(str(v) for v in neutral.get("blocking_reasons") or [])
            raise ValueError("IMB neutral geometry not ready" + (f":{reasons}" if reasons else ""))
        mesh = neutral.get("mesh") or {}
        for primitive in mesh.get("primitives") or []:
            add(primitive.get("material"), "material")
    elif ext == ".imx":
        neutral = build_imx_neutral_geometry(data)
        if neutral.get("ready") is not True:
            reasons = ";".join(str(v) for v in neutral.get("blocking_reasons") or [])
            raise ValueError("IMX neutral geometry not ready" + (f":{reasons}" if reasons else ""))
        mesh = neutral.get("mesh") or {}
        for primitive in mesh.get("primitives") or []:
            add(primitive.get("material"), "material")
    elif ext == ".bmt":
        material = parse_bmt_material(data).get("material") or {}
        add(material.get("shader"), "shader-source")
        for texture in material.get("textures") or []:
            add(texture, "texture")
        for parameter in material.get("shaderparams") or []:
            value = parameter.get("value")
            if isinstance(value, str) and Path(value.replace("\\", "/")).suffix.lower() == ".dds":
                add(value, "texture")
    return refs


def build_exact_ir_resource_closure(
    ir_root: str | Path,
    resource_references: Sequence[str],
) -> dict[str, Any]:
    root = Path(ir_root)
    manifest_value = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if not isinstance(manifest_value, list):
        raise ValueError("IR manifest.json must contain a list")
    rows = [
        row for row in manifest_value
        if isinstance(row, Mapping) and "error" not in row and row.get("path")
    ]
    by_path: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        by_path[_norm(row.get("path"))].append(row)

    blockers: list[str] = []
    resolved: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    queue: deque[tuple[str, str, str | None]] = deque()
    for ref in resource_references:
        queue.append((str(ref), "scene-resource", None))
    visited_rows: set[tuple[str, str, int | None]] = set()

    while queue:
        ref, kind, source_path = queue.popleft()
        candidates = _candidates(ref)
        hits: list[Mapping[str, Any]] = []
        seen_ids: set[tuple[str, str, int | None]] = set()
        for candidate in candidates:
            for row in by_path.get(candidate, []):
                identity = (
                    str(row.get("archive") or ""),
                    _norm(row.get("path")),
                    int(row["entry_index"]) if row.get("entry_index") is not None else None,
                )
                if identity not in seen_ids:
                    seen_ids.add(identity)
                    hits.append(row)

        edge = {
            "source_path": source_path,
            "ref": ref,
            "kind": kind,
            "candidate_paths": candidates,
            "resolution": "unique-exact-normalized-path",
            "targets": [
                {
                    "archive": row.get("archive"),
                    "path": row.get("path"),
                    "entry_index": row.get("entry_index"),
                    "sha256": row.get("sha256"),
                }
                for row in hits
            ],
        }
        if len(hits) != 1:
            status = "missing" if not hits else "ambiguous"
            edge["status"] = status
            blockers.append(f"exact-ir-{status}:{source_path or '<root>'}->{ref}")
            edges.append(edge)
            continue

        row = hits[0]
        edge["status"] = "resolved"
        edges.append(edge)
        identity = (
            str(row.get("archive") or ""),
            _norm(row.get("path")),
            int(row["entry_index"]) if row.get("entry_index") is not None else None,
        )
        if identity in visited_rows:
            continue
        visited_rows.add(identity)
        resolved.append({
            "archive": row.get("archive"),
            "path": row.get("path"),
            "entry_index": row.get("entry_index"),
            "sha256": row.get("sha256"),
            "raw": row.get("raw"),
            "output": row.get("output"),
        })

        try:
            dependencies = _semantic_refs(root, row)
        except Exception as exc:
            blockers.append(
                f"exact-ir-semantic-decode:{row.get('path')}:{type(exc).__name__}:{exc}"
            )
            continue
        for dependency in dependencies:
            queue.append((dependency["ref"], dependency["kind"], str(row.get("path") or "")))

    blockers = list(dict.fromkeys(blockers))
    ready = not blockers
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": blockers,
        "root_reference_count": len(resource_references),
        "resolved_resource_count": len(resolved),
        "edges": edges,
        "resources": resolved,
        "boundary": {
            "basename_fallback": False,
            "first_duplicate_wins": False,
            "exact_normalized_path_required": True,
            "known_aliases": [".mtx->.bmt"],
            "semantic_dependency_sources": [
                "MEB primitive material",
                "IMB neutral primitive material",
                "IMX neutral primitive material",
                "BMT shader and texture references",
            ],
            "unknown_format_dependency_inference": False,
            "shader_permutation_selection": False,
        },
    }
