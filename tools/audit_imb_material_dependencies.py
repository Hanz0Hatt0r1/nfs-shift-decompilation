#!/usr/bin/env python3
"""Audit IMB->BMT shader/texture dependency closure across BFF corpora."""
from __future__ import annotations

import argparse
import json
import tempfile
import zipfile
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from typing import Any, Iterable

from imb_neutral_geometry import build_imb_neutral_geometry
from resource_formats import parse_bmt_material
from shift_importer import BFF

FORMAT = "SHIFT.IMBMaterialDependencyAudit/1"


def _norm(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def _bmt_ref(material: str) -> str | None:
    value = str(material or "").replace("\\", "/")
    if value.lower().endswith(".mtx"):
        return value[:-4] + ".bmt"
    if value.lower().endswith(".bmt"):
        return value
    return None


def _materialize_bffs(
    inputs: Iterable[str | Path],
    stack: ExitStack,
) -> list[Path]:
    paths: list[Path] = []
    for source in inputs:
        path = Path(source)
        if path.suffix.lower() != ".zip":
            paths.append(path)
            continue
        archive = zipfile.ZipFile(path)
        stack.callback(archive.close)
        root = Path(
            stack.enter_context(
                tempfile.TemporaryDirectory(prefix="shift-material-deps-")
            )
        )
        for name in archive.namelist():
            if not name.lower().endswith(".bff") or name.endswith("/"):
                continue
            target = root / Path(name).name
            target.write_bytes(archive.read(name))
            paths.append(target)
    return paths


def summarize_dependency_rows(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = [dict(row) for row in rows]
    blockers = Counter()
    shader_uses = Counter()
    texture_uses = Counter()
    parsed = 0
    local_ready = 0
    ready = 0

    for row in rows:
        for reason in row.get("blocking_reasons") or []:
            blockers[str(reason)] += 1
        shader = _norm(row.get("shader"))
        if shader:
            shader_uses[shader] += 1
        for texture in row.get("textures") or []:
            texture_uses[_norm(texture)] += 1
        if row.get("material_parsed") is True:
            parsed += 1
        if row.get("local_ready") is True:
            local_ready += 1
        if row.get("ready") is True:
            ready += 1

    total = len(rows)
    return {
        "format": FORMAT,
        "version": 1,
        "status": (
            "ready" if total and ready == total
            else "empty" if not total
            else "external-blocked" if local_ready == total
            else "partial"
        ),
        "ready": bool(total) and ready == total,
        "local_ready": bool(total) and local_ready == total,
        "material_occurrence_count": total,
        "material_parse_count": parsed,
        "local_ready_count": local_ready,
        "ready_count": ready,
        "blocked_count": total - ready,
        "shader_reference_count": sum(shader_uses.values()),
        "unique_shader_reference_count": len(shader_uses),
        "shader_reference_use_counts": dict(sorted(shader_uses.items())),
        "texture_reference_count": sum(texture_uses.values()),
        "unique_texture_reference_count": len(texture_uses),
        "texture_reference_use_counts": dict(sorted(texture_uses.items())),
        "blocking_reason_counts": dict(sorted(blockers.items())),
        "rows": rows,
        "boundary": {
            "material_parser": "resource_formats.parse_bmt_material",
            "texture_scope": "exact same-BFF path",
            "shader_scope": "exact path across all supplied BFFs",
            "local_ready_meaning": (
                "BMT parsed and all texture references resolve in the same BFF"
            ),
            "ready_meaning": (
                "local_ready plus exactly one supplied shader-source match"
            ),
            "fxo_permutation_resolution": "not evaluated",
            "native_draw_readiness": "not evaluated",
        },
    }


def audit_imb_material_dependencies(
    inputs: Iterable[str | Path],
    *,
    max_imb_per_archive: int = 0,
) -> dict[str, Any]:
    inputs = list(inputs)
    rows: list[dict[str, Any]] = []
    archive_rows: list[dict[str, Any]] = []

    with ExitStack() as stack:
        paths = _materialize_bffs(inputs, stack)
        archives = [stack.enter_context(BFF(path)) for path in paths]

        global_index: dict[str, list[tuple[BFF, Any]]] = {}
        archive_index: dict[str, dict[str, list[Any]]] = {}
        for archive in archives:
            local: dict[str, list[Any]] = {}
            for entry in archive.entries:
                key = _norm(entry.path)
                local.setdefault(key, []).append(entry)
                global_index.setdefault(key, []).append((archive, entry))
            archive_index[archive.path.name] = local

        parsed_cache: dict[tuple[str, str], dict[str, Any]] = {}
        material_seen: set[tuple[str, str]] = set()

        for archive in archives:
            local_index = archive_index[archive.path.name]
            imbs = [
                entry for entry in archive.entries
                if Path(entry.path.replace("\\", "/")).suffix.lower() == ".imb"
            ]
            if max_imb_per_archive:
                imbs = imbs[:max_imb_per_archive]

            archive_materials = 0
            for imb in imbs:
                try:
                    geometry = build_imb_neutral_geometry(
                        archive.extract_entry(imb, type2="lzx")
                    )
                except Exception:
                    continue

                for primitive in geometry.get("primitives") or []:
                    ref = _bmt_ref(str(primitive.get("material") or ""))
                    if not ref:
                        continue
                    key = (archive.path.name, _norm(ref))
                    if key in material_seen:
                        continue
                    material_seen.add(key)
                    archive_materials += 1

                    blockers: list[str] = []
                    bmt_hits = local_index.get(key[1], [])
                    if len(bmt_hits) != 1:
                        blockers.append(
                            "same-archive-bmt-missing"
                            if not bmt_hits
                            else f"same-archive-bmt-ambiguous:{len(bmt_hits)}"
                        )
                        rows.append({
                            "archive": archive.path.name,
                            "bmt": ref.replace("\\", "/"),
                            "material_parsed": False,
                            "shader": None,
                            "textures": [],
                            "local_ready": False,
                            "ready": False,
                            "blocking_reasons": blockers,
                        })
                        continue

                    bmt_entry = bmt_hits[0]
                    try:
                        parsed = parsed_cache.get(key)
                        if parsed is None:
                            parsed = parse_bmt_material(
                                archive.extract_entry(bmt_entry, type2="lzx")
                            )
                            parsed_cache[key] = parsed
                        material = parsed.get("material") or {}
                    except Exception as exc:
                        blockers.append("bmt-parse-exception")
                        rows.append({
                            "archive": archive.path.name,
                            "bmt": ref.replace("\\", "/"),
                            "material_parsed": False,
                            "error_kind": type(exc).__name__,
                            "error": str(exc),
                            "shader": None,
                            "textures": [],
                            "local_ready": False,
                            "ready": False,
                            "blocking_reasons": blockers,
                        })
                        continue

                    shader = str(material.get("shader") or "").replace("\\", "/")
                    textures = [
                        str(value).replace("\\", "/")
                        for value in (material.get("textures") or [])
                        if value
                    ]
                    if not shader:
                        blockers.append("bmt-shader-reference-missing")

                    texture_matches = []
                    for texture in textures:
                        hits = local_index.get(_norm(texture), [])
                        texture_matches.append({
                            "path": texture,
                            "match_count": len(hits),
                            "matches": [
                                {
                                    "entry_index": int(hit.index),
                                    "path": hit.path.replace("\\", "/"),
                                    "type": int(hit.type),
                                }
                                for hit in hits
                            ],
                        })
                        if not hits:
                            blockers.append(
                                "same-archive-texture-missing:" + _norm(texture)
                            )
                        elif len(hits) != 1:
                            blockers.append(
                                "same-archive-texture-ambiguous:"
                                + _norm(texture)
                                + f":{len(hits)}"
                            )

                    shader_hits = global_index.get(_norm(shader), []) if shader else []
                    if shader and not shader_hits:
                        blockers.append("shader-source-missing:" + _norm(shader))
                    elif shader and len(shader_hits) != 1:
                        blockers.append(
                            "shader-source-ambiguous:"
                            + _norm(shader)
                            + f":{len(shader_hits)}"
                        )

                    local_blockers = [
                        reason for reason in blockers
                        if not reason.startswith("shader-source-")
                    ]
                    rows.append({
                        "archive": archive.path.name,
                        "bmt": ref.replace("\\", "/"),
                        "bmt_entry_index": int(bmt_entry.index),
                        "material_name": material.get("name"),
                        "technique": material.get("technique"),
                        "material_parsed": True,
                        "shader": shader,
                        "shader_match_count": len(shader_hits),
                        "shader_matches": [
                            {
                                "archive": owner.path.name,
                                "entry_index": int(hit.index),
                                "path": hit.path.replace("\\", "/"),
                                "type": int(hit.type),
                            }
                            for owner, hit in shader_hits
                        ],
                        "textures": textures,
                        "texture_matches": texture_matches,
                        "local_ready": not local_blockers,
                        "ready": not blockers,
                        "blocking_reasons": blockers,
                    })

            archive_rows.append({
                "archive": archive.path.name,
                "imb_count": len(imbs),
                "unique_material_occurrence_count": archive_materials,
            })

    report = summarize_dependency_rows(rows)
    report["input_count"] = len(inputs)
    report["archive_count"] = len(archive_rows)
    report["max_imb_per_archive"] = int(max_imb_per_archive)
    report["archives"] = archive_rows
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", help=".bff or .zip inputs")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--max-imb-per-archive", type=int, default=0)
    parser.add_argument("--require-local-ready", action="store_true")
    parser.add_argument("--require-all-ready", action="store_true")
    args = parser.parse_args(argv)
    if args.max_imb_per_archive < 0:
        parser.error("--max-imb-per-archive must be non-negative")

    report = audit_imb_material_dependencies(
        args.inputs,
        max_imb_per_archive=args.max_imb_per_archive,
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "material_occurrence_count": report["material_occurrence_count"],
        "material_parse_count": report["material_parse_count"],
        "local_ready": report["local_ready"],
        "ready": report["ready"],
        "unique_shader_reference_count": report["unique_shader_reference_count"],
        "unique_texture_reference_count": report["unique_texture_reference_count"],
        "blocking_reason_counts": report["blocking_reason_counts"],
    }, ensure_ascii=False, indent=2))

    if args.require_all_ready and not report["ready"]:
        return 2
    if args.require_local_ready and not report["local_ready"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
