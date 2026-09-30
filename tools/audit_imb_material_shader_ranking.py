#!/usr/bin/env python3
"""Rank FXO/VS-PS candidates for concrete IMB primitive material contexts."""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import zipfile
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from typing import Any, Iterable

from imb_neutral_geometry import build_imb_neutral_geometry
from material_linker import _selection_evidence_key, link_material
from render_pipeline import shader_family
from resource_formats import parse_bmt_material
from shift_importer import BFF

FORMAT = "SHIFT.IMBMaterialShaderRanking/1"


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
                tempfile.TemporaryDirectory(prefix="shift-material-shader-rank-")
            )
        )
        for name in archive.namelist():
            if not name.lower().endswith(".bff") or name.endswith("/"):
                continue
            target = root / Path(name).name
            target.write_bytes(archive.read(name))
            paths.append(target)
    return paths


def _candidate_identity(row: dict[str, Any] | None) -> str | None:
    row = row or {}
    permutation = row.get("permutation_identity") or {}
    if isinstance(permutation, dict) and permutation.get("identity_sha256"):
        return str(permutation["identity_sha256"])
    if row.get("pair_sha256"):
        return str(row["pair_sha256"])
    if row.get("pixel_sha256"):
        return str(row["pixel_sha256"])
    return None


def _compact_candidate(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None
    permutation = row.get("permutation_identity")
    return {
        "file": row.get("file"),
        "program_offset": row.get("program_offset"),
        "payload_sha256": row.get("payload_sha256"),
        "pixel_sha256": row.get("pixel_sha256"),
        "vertex_sha256": row.get("vertex_sha256"),
        "pair_sha256": row.get("pair_sha256"),
        "permutation_identity_sha256": (
            permutation.get("identity_sha256")
            if isinstance(permutation, dict)
            else None
        ),
        "exact": bool(row.get("exact")),
        "score": row.get("score"),
        "expected_count": row.get("expected_count"),
        "vertex_pair_valid": bool(row.get("vertex_pair_valid")),
        "vertex_pair_score": row.get("vertex_pair_score"),
        "vertex_pair_selection_status": row.get("vertex_pair_selection_status"),
        "uniform_coverage": row.get("uniform_coverage"),
        "specialization_score": row.get("specialization_score"),
        "specialization_contradicted": list(
            row.get("specialization_contradicted") or []
        ),
        "specialization_unexpected": list(
            row.get("specialization_unexpected") or []
        ),
    }


def _top_rank_candidates(binding: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        dict(row)
        for row in (binding.get("fxo_candidates") or [])
        if isinstance(row, dict)
    ]
    if not rows:
        return []
    best_rank = _selection_evidence_key(rows[0])
    return [
        row
        for row in rows
        if _selection_evidence_key(row) == best_rank
    ]


def summarize_ranking_rows(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = [dict(row) for row in rows]
    status_counts = Counter(str(row.get("selection_status") or "none") for row in rows)
    blocker_counts = Counter(
        reason
        for row in rows
        for reason in (row.get("blocking_reasons") or [])
    )
    families = Counter(str(row.get("shader_family") or "") for row in rows if row.get("shader_family"))
    unique = sum(row.get("selection_status") == "unique" for row in rows)
    ambiguous = sum(row.get("selection_status") == "ambiguous" for row in rows)
    heuristic = sum(row.get("selection_status") == "heuristic" for row in rows)
    none = len(rows) - unique - ambiguous - heuristic
    ready = bool(rows) and unique == len(rows) and not blocker_counts
    return {
        "format": FORMAT,
        "version": 1,
        "status": "selection-ready" if ready else ("empty" if not rows else "runtime-gated"),
        "ready": ready,
        "primitive_binding_count": len(rows),
        "unique_selection_count": unique,
        "ambiguous_selection_count": ambiguous,
        "heuristic_selection_count": heuristic,
        "no_selection_count": none,
        "runtime_target_count": len(rows) - unique,
        "selection_status_counts": dict(sorted(status_counts.items())),
        "blocking_reason_counts": dict(sorted(blocker_counts.items())),
        "shader_family_use_counts": dict(sorted(families.items())),
        "rows": rows,
        "boundary": {
            "ranking_engine": "material_linker.link_material",
            "ranking_scope": (
                "concrete IMB primitive + same-archive BMT + exact FX source + "
                "deduplicated same-family FXO payloads + IMB vertex properties"
            ),
            "unique_meaning": (
                "existing material-linker evidence selects one valid top-ranked "
                "permutation identity for this concrete primitive context"
            ),
            "ambiguous_policy": "preserve tied identities; do not select by file order",
            "heuristic_policy": "not render-admitted",
            "runtime_target_meaning": (
                "primitive context whose exact retail shader identity remains "
                "unproven after static ranking"
            ),
        },
    }


def audit_imb_material_shader_ranking(
    inputs: Iterable[str | Path],
    *,
    max_imb_per_archive: int = 0,
) -> dict[str, Any]:
    inputs = list(inputs)
    context_rows: list[dict[str, Any]] = []

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

        bmt_cache: dict[tuple[str, int], tuple[dict[str, Any], str]] = {}
        fx_cache: dict[tuple[str, int], bytes] = {}
        contexts: list[dict[str, Any]] = []
        target_families: set[str] = set()

        for archive in archives:
            local_index = archive_index[archive.path.name]
            texture_paths = [
                entry.path.replace("\\", "/")
                for entry in archive.entries
                if _norm(entry.path).endswith(".dds")
            ]
            imbs = [
                entry for entry in archive.entries
                if _norm(entry.path).endswith(".imb")
            ]
            if max_imb_per_archive:
                imbs = imbs[:max_imb_per_archive]

            for imb in imbs:
                try:
                    geometry = build_imb_neutral_geometry(
                        archive.extract_entry(imb, type2="lzx")
                    )
                except Exception as exc:
                    context_rows.append({
                        "archive": archive.path.name,
                        "imb_path": imb.path.replace("\\", "/"),
                        "primitive_index": None,
                        "selection_status": "none",
                        "blocking_reasons": ["imb-decode-exception"],
                        "error_kind": type(exc).__name__,
                        "error": str(exc),
                    })
                    continue

                vertex_properties = tuple(
                    str(value)
                    for value in ((geometry.get("mesh") or {}).get("vertex_properties") or [])
                )
                for primitive in geometry.get("primitives") or []:
                    primitive_index = int(primitive.get("index") or 0)
                    material_reference = str(primitive.get("material") or "")
                    bmt_ref = _bmt_ref(material_reference)
                    base = {
                        "archive": archive.path.name,
                        "imb_path": imb.path.replace("\\", "/"),
                        "imb_entry_index": int(imb.index),
                        "primitive_index": primitive_index,
                        "material_reference": material_reference.replace("\\", "/"),
                        "bmt": bmt_ref,
                        "vertex_properties": list(vertex_properties),
                    }
                    if not bmt_ref:
                        context_rows.append({
                            **base,
                            "selection_status": "none",
                            "blocking_reasons": [
                                "primitive-material-reference-not-mtx-or-bmt"
                            ],
                        })
                        continue

                    bmt_hits = local_index.get(_norm(bmt_ref), [])
                    if len(bmt_hits) != 1:
                        context_rows.append({
                            **base,
                            "selection_status": "none",
                            "blocking_reasons": [
                                "same-archive-bmt-missing"
                                if not bmt_hits
                                else f"same-archive-bmt-ambiguous:{len(bmt_hits)}"
                            ],
                        })
                        continue

                    bmt_entry = bmt_hits[0]
                    cache_key = (archive.path.name, int(bmt_entry.index))
                    try:
                        cached = bmt_cache.get(cache_key)
                        if cached is None:
                            raw_bmt = archive.extract_entry(bmt_entry, type2="lzx")
                            parsed = parse_bmt_material(raw_bmt)
                            material = parsed.get("material") or {}
                            digest = hashlib.sha256(raw_bmt).hexdigest()
                            cached = (material, digest)
                            bmt_cache[cache_key] = cached
                        material, bmt_sha = cached
                    except Exception as exc:
                        context_rows.append({
                            **base,
                            "bmt_entry_index": int(bmt_entry.index),
                            "selection_status": "none",
                            "blocking_reasons": ["bmt-parse-exception"],
                            "error_kind": type(exc).__name__,
                            "error": str(exc),
                        })
                        continue

                    shader_ref = str(material.get("shader") or "").replace("\\", "/")
                    if not shader_ref:
                        context_rows.append({
                            **base,
                            "bmt_entry_index": int(bmt_entry.index),
                            "bmt_sha256": bmt_sha,
                            "selection_status": "none",
                            "blocking_reasons": ["bmt-shader-reference-missing"],
                        })
                        continue

                    fx_hits = global_index.get(_norm(shader_ref), [])
                    if len(fx_hits) != 1:
                        context_rows.append({
                            **base,
                            "bmt_entry_index": int(bmt_entry.index),
                            "bmt_sha256": bmt_sha,
                            "shader": shader_ref,
                            "selection_status": "none",
                            "blocking_reasons": [
                                "shader-source-missing"
                                if not fx_hits
                                else f"shader-source-ambiguous:{len(fx_hits)}"
                            ],
                        })
                        continue

                    fx_owner, fx_entry = fx_hits[0]
                    fx_key = (fx_owner.path.name, int(fx_entry.index))
                    try:
                        fx_source = fx_cache.get(fx_key)
                        if fx_source is None:
                            fx_source = fx_owner.extract_entry(fx_entry, type2="lzx")
                            fx_cache[fx_key] = fx_source
                    except Exception as exc:
                        context_rows.append({
                            **base,
                            "bmt_entry_index": int(bmt_entry.index),
                            "bmt_sha256": bmt_sha,
                            "shader": shader_ref,
                            "selection_status": "none",
                            "blocking_reasons": ["shader-source-decode-exception"],
                            "error_kind": type(exc).__name__,
                            "error": str(exc),
                        })
                        continue

                    family = shader_family(shader_ref)
                    target_families.add(family)
                    contexts.append({
                        **base,
                        "bmt_entry_index": int(bmt_entry.index),
                        "bmt_sha256": bmt_sha,
                        "fx_source_sha256": hashlib.sha256(fx_source).hexdigest(),
                        "material": material,
                        "material_name": material.get("name"),
                        "technique": material.get("technique"),
                        "shader": shader_ref,
                        "shader_family": family,
                        "fx_source": fx_source,
                        "texture_paths": texture_paths,
                    })

        family_payloads: dict[str, list[tuple[str, bytes]]] = {
            family: [] for family in target_families
        }
        family_seen: dict[str, set[str]] = {
            family: set() for family in target_families
        }
        for archive in archives:
            for entry in archive.entries:
                norm_path = _norm(entry.path)
                if not norm_path.endswith(".fxo"):
                    continue
                family = shader_family(norm_path)
                if family not in target_families:
                    continue
                try:
                    payload = archive.extract_entry(entry, type2="lzx")
                except Exception:
                    continue
                digest = hashlib.sha256(payload).hexdigest()
                if digest in family_seen[family]:
                    continue
                family_seen[family].add(digest)
                family_payloads[family].append((
                    entry.path.replace("\\", "/"),
                    payload,
                ))

        result_cache: dict[
            tuple[str, str, str, tuple[str, ...], str],
            dict[str, Any],
        ] = {}
        for context in contexts:
            family = str(context["shader_family"])
            bmt_sha = str(context["bmt_sha256"])
            fx_sha = str(context["fx_source_sha256"])
            properties = tuple(context["vertex_properties"])
            cache_key = (
                str(context["archive"]),
                bmt_sha,
                fx_sha,
                properties,
                family,
            )
            linked = result_cache.get(cache_key)
            if linked is None:
                linked = link_material(
                    context["material"],
                    context["fx_source"],
                    fxo_candidates=family_payloads.get(family, []),
                    texture_paths=context["texture_paths"],
                    vertex_properties=properties,
                )
                result_cache[cache_key] = linked

            status = str(linked.get("selection_status") or "none")
            selected = _compact_candidate(linked.get("selected_fxo"))
            ambiguous = [
                candidate
                for candidate in (
                    _compact_candidate(row)
                    for row in (linked.get("ambiguous_candidates") or [])
                )
                if candidate is not None
            ]
            top_rank = [
                candidate
                for candidate in (
                    _compact_candidate(row)
                    for row in _top_rank_candidates(linked)
                )
                if candidate is not None
            ]
            blockers: list[str] = []
            if status != "unique":
                blockers.append(f"shader-selection:{status}")
            if linked.get("unresolved_textures"):
                blockers.append("material-texture-binding:unresolved")
            if status == "unique" and not selected:
                blockers.append("selected-fxo:missing")

            context_rows.append({
                key: value
                for key, value in context.items()
                if key not in {"material", "fx_source", "texture_paths"}
            } | {
                "fxo_unique_payload_count": len(
                    family_payloads.get(family, [])
                ),
                "selection_status": status,
                "selection_evidence": linked.get("selection_evidence"),
                "selected_identity": _candidate_identity(
                    linked.get("selected_fxo")
                ),
                "selected_fxo": selected,
                "ambiguous_candidates": ambiguous,
                "top_rank_candidate_count": len(top_rank),
                "top_rank_candidates": top_rank,
                "unresolved_textures": list(
                    linked.get("unresolved_textures") or []
                ),
                "blocking_reasons": blockers,
            })

    report = summarize_ranking_rows(context_rows)
    report["input_count"] = len(inputs)
    report["max_imb_per_archive"] = int(max_imb_per_archive)
    report["unique_rank_context_count"] = len({
        (
            row.get("archive"),
            row.get("bmt_sha256"),
            row.get("fx_source_sha256"),
            tuple(row.get("vertex_properties") or []),
            row.get("shader_family"),
        )
        for row in context_rows
        if row.get("bmt_sha256") and row.get("shader_family")
    })
    report["fxo_unique_payload_counts"] = {
        family: len(payloads)
        for family, payloads in sorted(family_payloads.items())
    }
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", help=".bff or .zip inputs")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--max-imb-per-archive", type=int, default=0)
    parser.add_argument("--require-selection-ready", action="store_true")
    args = parser.parse_args(argv)
    if args.max_imb_per_archive < 0:
        parser.error("--max-imb-per-archive must be non-negative")

    report = audit_imb_material_shader_ranking(
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
        "ready": report["ready"],
        "primitive_binding_count": report["primitive_binding_count"],
        "unique_selection_count": report["unique_selection_count"],
        "ambiguous_selection_count": report["ambiguous_selection_count"],
        "heuristic_selection_count": report["heuristic_selection_count"],
        "no_selection_count": report["no_selection_count"],
        "runtime_target_count": report["runtime_target_count"],
        "unique_rank_context_count": report["unique_rank_context_count"],
        "fxo_unique_payload_counts": report["fxo_unique_payload_counts"],
    }, ensure_ascii=False, indent=2))
    return 0 if (report["ready"] or not args.require_selection_ready) else 2


if __name__ == "__main__":
    raise SystemExit(main())
