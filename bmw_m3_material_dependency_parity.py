#!/usr/bin/env python3
"""Build a real BMW M3 BMT -> shader/texture dependency closure."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

from shift_importer import BFF
from resource_formats import parse_bmt_material

FORMAT = "SHIFT.BMWM3MaterialDependencyParity/1"
TARGET_RESOURCE = "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb"
TARGET_SHA256 = "960ac728db8dc1e870ae348cf77fa3a18feb1a359bc6f31a865b528b931b2c2c"


def _norm(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _find_exact(rows: list[tuple[BFF, Any]], path: str) -> tuple[BFF, Any] | None:
    target = _norm(path)
    hits = [(a, e) for a, e in rows if _norm(e.path) == target]
    if len(hits) == 1:
        return hits[0]
    return None


def _load_meb_material_refs(path: Path) -> tuple[str, str, list[dict[str, Any]]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    golden = document.get("golden") if isinstance(document.get("golden"), Mapping) else {}
    mesh = document.get("mesh") if isinstance(document.get("mesh"), Mapping) else document
    resource = _norm(golden.get("resource") or document.get("resource") or TARGET_RESOURCE)
    resource_sha = str(
        golden.get("resource_sha256")
        or document.get("resource_sha256")
        or document.get("source_sha256")
        or TARGET_SHA256
    ).lower()

    primitives = list(mesh.get("primitives") or [])
    if not primitives:
        raise ValueError("MEB document contains no primitives")

    rows = []
    for index, primitive in enumerate(primitives):
        material = str(primitive.get("material") or "").replace("\\", "/")
        if not material.lower().endswith(".mtx"):
            raise ValueError(f"primitive {index} material is not .mtx: {material}")
        index_count = int(primitive.get("index_count", 0))
        if index_count <= 0 or index_count % 3:
            raise ValueError(f"primitive {index} has invalid index_count: {index_count}")
        rows.append({
            "primitive_index": index,
            "material_ref": material,
            "bmt_ref": material[:-4] + ".bmt",
            "triangle_count": index_count // 3,
        })
    return resource, resource_sha, rows


def build_dependency_report(
    material_refs: list[Mapping[str, Any]],
    material_payloads: Mapping[str, Mapping[str, Any]],
    resources: Mapping[str, Mapping[str, Any]],
    *,
    resource: str = TARGET_RESOURCE,
    resource_sha256: str = TARGET_SHA256,
) -> dict[str, Any]:
    blockers: list[str] = []
    if _norm(resource) != _norm(TARGET_RESOURCE):
        blockers.append("dependency:unexpected-target-resource")
    if resource_sha256.lower() != TARGET_SHA256:
        blockers.append("dependency:unexpected-target-sha256")

    correlations = []
    for ref in material_refs:
        bmt = _norm(ref["bmt_ref"])
        payload = material_payloads.get(bmt)
        if payload is None:
            blockers.append(f"dependency:bmt-payload-missing:{bmt}")
            correlations.append({**ref, "status": "missing"})
            continue

        material = payload.get("material") if isinstance(payload.get("material"), Mapping) else {}
        name = str(material.get("name") or "")
        shader = _norm(material.get("shader"))
        textures = [_norm(x) for x in (material.get("textures") or []) if x]
        refs = [shader, *textures]
        unresolved = [x for x in refs if x and x not in resources]

        for missing in unresolved:
            blockers.append(f"dependency:resource-missing:{bmt}:{missing}")

        bmt_stem = bmt.rsplit("/", 1)[-1][:-4]
        if name and name.lower() != bmt_stem.lower():
            blockers.append(f"dependency:bmt-name-mismatch:{bmt}:{name}")

        correlations.append({
            **ref,
            "status": "match" if not unresolved else "blocked",
            "bmt": {
                "path": bmt,
                "name": name,
                "payload_sha256": payload.get("payload_sha256"),
                "archive": payload.get("archive"),
                "entry_index": payload.get("entry_index"),
                "decoded_size": payload.get("decoded_size"),
            },
            "shader": shader,
            "shader_resource": resources.get(shader),
            "textures": [
                {"path": x, "resource": resources.get(x)}
                for x in textures
            ],
            "unresolved": unresolved,
        })

    unique_bmts = sorted({_norm(x["bmt_ref"]) for x in material_refs})
    unique_shaders = sorted({x["shader"] for x in correlations if x.get("shader")})
    unique_textures = sorted({
        t["path"]
        for x in correlations
        for t in x.get("textures", [])
    })

    return {
        "format": FORMAT,
        "status": "match" if not blockers else "blocked",
        "ready": not blockers,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "resource": {
            "path": _norm(resource),
            "sha256": resource_sha256.lower(),
        },
        "primitive_count": len(material_refs),
        "unique_bmt_count": len(unique_bmts),
        "unique_shader_count": len(unique_shaders),
        "unique_texture_count": len(unique_textures),
        "material_reference_use_count": dict(
            sorted(Counter(_norm(x["bmt_ref"]) for x in material_refs).items())
        ),
        "primitive_materials": correlations,
        "closure": {
            "bmt_paths": unique_bmts,
            "shader_paths": unique_shaders,
            "texture_paths": unique_textures,
        },
        "boundary": {
            "payload_decoded": True,
            "dependency_resolution": True,
            "shader_execution_proven": False,
            "runtime_same_instance_proven": False,
        },
    }


def build_report(
    meb_json: Path,
    primary_bff: Path,
    supplemental_bffs: Iterable[Path] = (),
) -> dict[str, Any]:
    resource, resource_sha, refs = _load_meb_material_refs(meb_json)
    archive_paths = [primary_bff, *supplemental_bffs]
    archives = [BFF(path) for path in archive_paths]
    try:
        rows = [(archive, entry) for archive in archives for entry in archive.entries]
        payloads: dict[str, Mapping[str, Any]] = {}
        resources: dict[str, Mapping[str, Any]] = {}

        for bmt in sorted({_norm(x["bmt_ref"]) for x in refs}):
            found = _find_exact(rows, bmt)
            if found is None:
                continue
            archive, entry = found
            raw = archive.extract_entry(entry)
            parsed = parse_bmt_material(raw)
            payloads[bmt] = {
                "material": parsed.get("material") or {},
                "payload_sha256": _sha256(raw),
                "archive": archive.path.name,
                "entry_index": entry.index,
                "decoded_size": len(raw),
            }

        wanted: set[str] = set()
        for payload in payloads.values():
            material = payload.get("material") or {}
            shader = _norm(material.get("shader"))
            if shader:
                wanted.add(shader)
            wanted.update(
                _norm(x) for x in (material.get("textures") or []) if x
            )

        for path in sorted(wanted):
            found = _find_exact(rows, path)
            if found is None:
                continue
            archive, entry = found
            resources[path] = {
                "archive": archive.path.name,
                "entry_index": entry.index,
                "path": entry.path,
                "type": entry.type,
                "compressed_size": entry.compressed_size,
                "uncompressed_size": entry.uncompressed_size,
            }

        return build_dependency_report(
            refs,
            payloads,
            resources,
            resource=resource,
            resource_sha256=resource_sha,
        )
    finally:
        for archive in archives:
            archive.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("meb_json", type=Path)
    ap.add_argument("bff", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--supplemental-bff", action="append", default=[], type=Path)
    args = ap.parse_args(argv)

    report = build_report(args.meb_json, args.bff, args.supplemental_bffs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
