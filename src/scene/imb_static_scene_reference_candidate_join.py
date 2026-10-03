"""Join Phase 618 geometry ambiguity to exact source-backed SGB resource refs.

This is an offline narrowing/classification stage.  It scans decoded retail SGB
object graphs, records exact OBJECT -> IMB references and source-backed LOD
parent/slot metadata, and joins those references to Phase 618 candidate path +
payload identities.  It never turns a static scene reference into runtime draw
attribution without an independent instance/LOD selection witness.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from contextlib import ExitStack
from pathlib import Path
from typing import Any, Iterable, Mapping

from imb_material_constant_candidate_join import (
    _materialize_bffs,
    _norm,
    _valid_sha,
    resolve_input_path,
)
from sgb_runtime import parse_sgb_runtime
from shift_importer import BFF

FORMAT = "SHIFT.IMBStaticSceneReferenceCandidateJoin/1"
AMBIGUITY_FORMAT = "SHIFT.IMBDrawLocalAmbiguityAudit/1"
GEOMETRY_CLASSES = {
    "metadata-equivalent-lod-siblings",
    "metadata-equivalent-geometry-alternatives",
}


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")).hexdigest()


def _kind(report: Mapping[str, Any]) -> str | None:
    value = report.get("kind")
    if not isinstance(value, Mapping):
        return None
    text = value.get("text")
    return str(text) if text else None


def _resource_text(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None
    text = value.get("text")
    return str(text).replace("\\", "/") if text else None


def _wanted_candidate_paths(ambiguity: Mapping[str, Any]) -> set[str]:
    result: set[str] = set()
    for draw in ambiguity.get("ambiguous_draws") or []:
        if not isinstance(draw, Mapping) or draw.get("ambiguity_class") not in GEOMETRY_CLASSES:
            continue
        for candidate in draw.get("candidates") or []:
            if not isinstance(candidate, Mapping):
                continue
            for path in candidate.get("imb_paths") or []:
                key = _norm(path)
                if key:
                    result.add(key)
    return result


def _walk_object_references(
    report: Mapping[str, Any],
    *,
    object_path: tuple[int, ...] = (),
    lod_ancestry: tuple[dict[str, Any], ...] = (),
) -> list[dict[str, Any]]:
    """Return exact OBJECT resource refs with recursive LOD provenance."""
    rows: list[dict[str, Any]] = []
    kind = _kind(report)
    if kind == "OBJECT":
        ref = _resource_text(report.get("resource_filename"))
        if ref:
            rows.append({
                "reference_kind": "object-resource",
                "resource_path": ref,
                "normalized_resource_path": _norm(ref),
                "object_path": list(object_path),
                "object_kind": kind,
                "matrix_number": report.get("matrix_number"),
                "lod_ancestry": [dict(row) for row in lod_ancestry],
            })
        return rows

    if kind not in {"LOD", "HIERARCHY"}:
        return rows

    distances = list(report.get("lod_distances_serialized") or []) if kind == "LOD" else []
    for child in report.get("subobject_references") or []:
        if not isinstance(child, Mapping) or child.get("decoded") is not True:
            continue
        child_report = child.get("report")
        if not isinstance(child_report, Mapping):
            continue
        index = child.get("index")
        if not isinstance(index, int):
            continue
        next_lod = lod_ancestry
        if kind == "LOD":
            distance = distances[index] if index < len(distances) else None
            parent_identity = _canonical_hash({
                "object_path": list(object_path),
                "object_hash_sha256": report.get("hash_sha256"),
                "source_string": _resource_text(report.get("source_string")),
                "subobject_count": report.get("subobjects"),
            })
            next_lod = (*lod_ancestry, {
                "lod_parent_identity_sha256": parent_identity,
                "lod_parent_object_path": list(object_path),
                "child_index": index,
                "serialized_distance": distance,
                "distance_status": (
                    "serialized-nonzero"
                    if isinstance(distance, (int, float)) and float(distance) != 0.0
                    else "zero-uses-source-backed-runtime-fallback"
                    if isinstance(distance, (int, float))
                    else "distance-unavailable"
                ),
                "runtime_fallback_rule": (
                    report.get("lod_distance_runtime_rule") or {}
                ).get("zero_value_fallback"),
            })
        rows.extend(_walk_object_references(
            child_report,
            object_path=(*object_path, index),
            lod_ancestry=next_lod,
        ))
    return rows


def _index_imb_payloads(
    archives: list[tuple[Path, str]],
    stack: ExitStack,
    wanted_paths: set[str],
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "distinct_payloads": {},
        "occurrences": [],
    })
    for path, source_input in archives:
        try:
            archive = stack.enter_context(BFF(path))
        except Exception:
            continue
        for entry in archive.entries:
            key = _norm(entry.path)
            if key not in wanted_paths:
                continue
            try:
                payload = archive.extract_entry(entry, type2="lzx")
            except Exception:
                continue
            digest = hashlib.sha256(payload).hexdigest()
            occurrence = {
                "source_input": source_input,
                "archive": archive.path.name,
                "entry_path": str(entry.path).replace("\\", "/"),
                "entry_index": int(entry.index),
                "payload_sha256": digest,
            }
            grouped[key]["occurrences"].append(occurrence)
            grouped[key]["distinct_payloads"].setdefault(digest, []).append(occurrence)
    result: dict[str, dict[str, Any]] = {}
    for key, row in grouped.items():
        shas = sorted(row["distinct_payloads"])
        result[key] = {
            "normalized_path": key,
            "distinct_payload_sha256s": shas,
            "distinct_payload_count": len(shas),
            "unique_payload_sha256": shas[0] if len(shas) == 1 else None,
            "occurrences": sorted(row["occurrences"], key=lambda value: (
                str(value.get("source_input") or "").lower(),
                str(value.get("archive") or "").lower(),
                str(value.get("entry_path") or "").lower(),
                int(value.get("entry_index") or -1),
            )),
        }
    return result


def load_static_scene_reference_index(
    inputs: Iterable[str | Path],
    wanted_paths: set[str],
) -> dict[str, Any]:
    inputs = list(inputs)
    references: list[dict[str, Any]] = []
    blocked_sgbs: list[dict[str, Any]] = []
    decoded_sgb_count = ready_sgb_count = 0

    with ExitStack() as stack:
        materialized = _materialize_bffs(inputs, stack)
        # BFF objects cannot be shared with _index_imb_payloads because each is
        # an ExitStack-managed context. Re-materialized paths are stable for the
        # lifetime of this stack, so opening each archive twice is harmless.
        imb_index = _index_imb_payloads(materialized, stack, wanted_paths)

        for path, source_input in materialized:
            try:
                archive = stack.enter_context(BFF(path))
            except Exception:
                continue
            for entry in archive.entries:
                if not _norm(entry.path).endswith(".sgb"):
                    continue
                try:
                    payload = archive.extract_entry(entry, type2="lzx")
                    runtime = parse_sgb_runtime(payload, strict=False)
                except Exception as exc:
                    blocked_sgbs.append({
                        "source_input": source_input,
                        "archive": archive.path.name,
                        "sgb_path": str(entry.path).replace("\\", "/"),
                        "status": "decode-exception",
                        "error": f"{type(exc).__name__}: {exc}",
                    })
                    continue
                decoded_sgb_count += 1
                sgb_sha = hashlib.sha256(payload).hexdigest()
                if runtime.get("ready") is not True:
                    blocked_sgbs.append({
                        "source_input": source_input,
                        "archive": archive.path.name,
                        "sgb_path": str(entry.path).replace("\\", "/"),
                        "sgb_sha256": sgb_sha,
                        "status": "runtime-decode-not-ready",
                        "blocking_reasons": list(runtime.get("blockers") or []),
                    })
                    continue
                ready_sgb_count += 1

                for chunk in runtime.get("chunks") or []:
                    if not isinstance(chunk, Mapping) or chunk.get("tag") not in {"NODE", "SUMM"}:
                        continue
                    if chunk.get("decode_status") != "decoded":
                        continue
                    tag = str(chunk.get("tag"))
                    for record in chunk.get("records") or []:
                        if not isinstance(record, Mapping):
                            continue
                        record_index = record.get("index")
                        wrapper_resource = _resource_text(record.get("resource"))
                        raw_rows = []
                        if wrapper_resource and _norm(wrapper_resource) in wanted_paths:
                            raw_rows.append({
                                "reference_kind": "wrapper-resource",
                                "resource_path": wrapper_resource,
                                "normalized_resource_path": _norm(wrapper_resource),
                                "object_path": [],
                                "object_kind": None,
                                "matrix_number": None,
                                "lod_ancestry": [],
                            })
                        payload_row = record.get("object_payload")
                        object_report = payload_row.get("report") if isinstance(payload_row, Mapping) else None
                        if isinstance(object_report, Mapping) and object_report.get("decoded") is True:
                            raw_rows.extend(_walk_object_references(object_report))

                        for raw in raw_rows:
                            normalized = str(raw.get("normalized_resource_path") or "")
                            if normalized not in wanted_paths:
                                continue
                            target = imb_index.get(normalized) or {}
                            target_sha = _valid_sha(target.get("unique_payload_sha256"))
                            source_identity = {
                                "source_input": source_input,
                                "archive": archive.path.name,
                                "sgb_path": str(entry.path).replace("\\", "/"),
                                "sgb_sha256": sgb_sha,
                                "chunk": tag,
                                "source_record_index": record_index,
                                "reference_kind": raw.get("reference_kind"),
                                "object_path": raw.get("object_path"),
                                "resource_path": raw.get("resource_path"),
                                "target_resource_sha256": target_sha,
                            }
                            references.append({
                                **raw,
                                "source_input": source_input,
                                "archive": archive.path.name,
                                "sgb_path": str(entry.path).replace("\\", "/"),
                                "sgb_entry_index": int(entry.index),
                                "sgb_sha256": sgb_sha,
                                "chunk": tag,
                                "source_record_index": record_index,
                                "wrapper_name": _resource_text(record.get("name")),
                                "wrapper_resource": wrapper_resource,
                                "target_path_distinct_payload_count": int(target.get("distinct_payload_count") or 0),
                                "target_path_distinct_payload_sha256s": list(target.get("distinct_payload_sha256s") or []),
                                "target_resource_sha256": target_sha,
                                "target_identity_ready": target_sha is not None,
                                "scene_reference_identity_sha256": _canonical_hash(source_identity),
                            })

    references.sort(key=lambda row: (
        str(row.get("normalized_resource_path") or ""),
        str(row.get("source_input") or ""),
        str(row.get("archive") or ""),
        str(row.get("sgb_path") or ""),
        str(row.get("chunk") or ""),
        int(row.get("source_record_index") or -1),
        tuple(row.get("object_path") or []),
    ))
    return {
        "wanted_path_count": len(wanted_paths),
        "decoded_sgb_count": decoded_sgb_count,
        "ready_sgb_count": ready_sgb_count,
        "blocked_sgb_count": len(blocked_sgbs),
        "imb_path_identity_count": len(imb_index),
        "references": references,
        "blocked_sgbs": blocked_sgbs,
        "imb_path_index": imb_index,
    }


def _candidate_matches(
    candidate: Mapping[str, Any],
    references_by_path: Mapping[str, list[Mapping[str, Any]]],
) -> dict[str, Any]:
    digest = _valid_sha(candidate.get("imb_sha256"))
    paths = sorted({_norm(value) for value in (candidate.get("imb_paths") or []) if _norm(value)})
    refs: list[dict[str, Any]] = []
    unresolved_paths = []
    for path in paths:
        path_refs = list(references_by_path.get(path) or [])
        for ref in path_refs:
            target_sha = _valid_sha(ref.get("target_resource_sha256"))
            if target_sha is None:
                unresolved_paths.append(path)
                continue
            if digest and target_sha == digest:
                refs.append(dict(ref))
    lod_parent_ids = sorted({
        str(lod.get("lod_parent_identity_sha256"))
        for ref in refs
        for lod in (ref.get("lod_ancestry") or [])[-1:]
        if isinstance(lod, Mapping) and lod.get("lod_parent_identity_sha256")
    })
    return {
        "content_group_sha256": _valid_sha(candidate.get("content_group_sha256")),
        "imb_sha256": digest,
        "imb_paths": [str(value).replace("\\", "/") for value in (candidate.get("imb_paths") or []) if value],
        "archive_hints": list(candidate.get("archives") or []),
        "exact_scene_reference_count": len(refs),
        "exact_scene_referenced": bool(refs),
        "unresolved_reference_paths": sorted(set(unresolved_paths)),
        "lod_parent_identity_sha256s": lod_parent_ids,
        "scene_references": refs,
    }


def _lod_groups(candidate_rows: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for candidate in candidate_rows:
        content_sha = _valid_sha(candidate.get("content_group_sha256"))
        for ref in candidate.get("scene_references") or []:
            if not isinstance(ref, Mapping):
                continue
            ancestry = [row for row in (ref.get("lod_ancestry") or []) if isinstance(row, Mapping)]
            if not ancestry:
                continue
            lod = ancestry[-1]
            identity = _valid_sha(lod.get("lod_parent_identity_sha256"))
            if not identity:
                continue
            group = groups.setdefault(identity, {
                "lod_parent_identity_sha256": identity,
                "candidate_content_group_sha256s": set(),
                "slots": [],
                "source_occurrences": set(),
            })
            if content_sha:
                group["candidate_content_group_sha256s"].add(content_sha)
            slot = {
                "content_group_sha256": content_sha,
                "resource_path": ref.get("resource_path"),
                "resource_sha256": ref.get("target_resource_sha256"),
                "child_index": lod.get("child_index"),
                "serialized_distance": lod.get("serialized_distance"),
                "distance_status": lod.get("distance_status"),
                "runtime_fallback_rule": lod.get("runtime_fallback_rule"),
                "sgb_path": ref.get("sgb_path"),
                "chunk": ref.get("chunk"),
                "source_record_index": ref.get("source_record_index"),
                "lod_parent_object_path": lod.get("lod_parent_object_path"),
            }
            group["slots"].append(slot)
            group["source_occurrences"].add((
                ref.get("source_input"), ref.get("archive"), ref.get("sgb_path"),
                ref.get("chunk"), ref.get("source_record_index"),
            ))
    result = []
    for group in groups.values():
        candidate_shas = sorted(group.pop("candidate_content_group_sha256s"))
        occurrences = sorted(group.pop("source_occurrences"), key=lambda row: tuple(str(value or "") for value in row))
        slots = sorted(group["slots"], key=lambda row: (
            int(row.get("child_index")) if isinstance(row.get("child_index"), int) else 2**31 - 1,
            str(row.get("content_group_sha256") or ""),
            str(row.get("resource_path") or ""),
        ))
        result.append({
            **group,
            "candidate_content_group_sha256s": candidate_shas,
            "candidate_count": len(candidate_shas),
            "slots": slots,
            "source_occurrences": [
                {
                    "source_input": row[0], "archive": row[1], "sgb_path": row[2],
                    "chunk": row[3], "source_record_index": row[4],
                }
                for row in occurrences
            ],
        })
    result.sort(key=lambda row: (-int(row["candidate_count"]), str(row["lod_parent_identity_sha256"])))
    return result


def build_static_scene_reference_candidate_join(
    ambiguity: Mapping[str, Any],
    scene_index: Mapping[str, Any],
) -> dict[str, Any]:
    if ambiguity.get("format") != AMBIGUITY_FORMAT:
        raise ValueError(f"ambiguity report must be {AMBIGUITY_FORMAT}")

    references_by_path: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for ref in scene_index.get("references") or []:
        if not isinstance(ref, Mapping):
            continue
        path = str(ref.get("normalized_resource_path") or "")
        if path:
            references_by_path[path].append(ref)

    rows = []
    resolution_counts: Counter[str] = Counter()
    referenced_candidate_count = 0
    lod_family_draw_count = 0
    single_referenced_draw_count = 0

    for draw in ambiguity.get("ambiguous_draws") or []:
        if not isinstance(draw, Mapping) or draw.get("ambiguity_class") not in GEOMETRY_CLASSES:
            continue
        candidates = [
            _candidate_matches(candidate, references_by_path)
            for candidate in (draw.get("candidates") or [])
            if isinstance(candidate, Mapping)
        ]
        referenced = [row for row in candidates if row.get("exact_scene_referenced")]
        referenced_candidate_count += len(referenced)
        lod_groups = _lod_groups(candidates)
        shared_lod = [row for row in lod_groups if int(row.get("candidate_count") or 0) >= 2]

        if shared_lod:
            resolution = "source-backed-lod-family-needs-selection-witness"
            lod_family_draw_count += 1
        elif len(referenced) == 1:
            resolution = "single-static-scene-referenced-candidate-unproven-draw"
            single_referenced_draw_count += 1
        elif len(referenced) > 1:
            resolution = "multiple-static-scene-referenced-candidates"
        else:
            resolution = "no-exact-static-scene-reference"
        resolution_counts[resolution] += 1

        rows.append({
            "event_index": draw.get("event_index"),
            "frame": draw.get("frame"),
            "draw_evidence_sha256": _valid_sha(draw.get("draw_evidence_sha256")),
            "candidate_set_sha256": _valid_sha(draw.get("candidate_set_sha256")),
            "ambiguity_class": draw.get("ambiguity_class"),
            "input_candidate_count": len(candidates),
            "exact_scene_referenced_candidate_count": len(referenced),
            "resolution_status": resolution,
            "selected_content_group_sha256": None,
            "candidate_results": candidates,
            "lod_groups": lod_groups,
            "blocking_reasons": (
                ["runtime-or-static-instance-selection-witness-still-required"]
                if referenced else
                ["exact-static-scene-reference-not-found-in-ready-sgb-corpus"]
            ),
        })

    rows.sort(key=lambda row: (
        int(row["event_index"]) if isinstance(row.get("event_index"), int) else 2**63 - 1,
        str(row.get("candidate_set_sha256") or ""),
    ))
    return {
        "format": FORMAT,
        "version": 1,
        "status": "observed" if rows else "no-geometry-ambiguity",
        "summary": {
            "geometry_ambiguous_draw_count": len(rows),
            "exact_scene_referenced_candidate_count": referenced_candidate_count,
            "single_scene_referenced_candidate_draw_count": single_referenced_draw_count,
            "source_backed_lod_family_draw_count": lod_family_draw_count,
            "draw_attribution_resolved_count": 0,
            "remaining_geometry_ambiguous_draw_count": len(rows),
            "resolution_status_counts": dict(sorted(resolution_counts.items())),
            "ready_sgb_count": int(scene_index.get("ready_sgb_count") or 0),
            "blocked_sgb_count": int(scene_index.get("blocked_sgb_count") or 0),
        },
        "draws": rows,
        "scene_index": {
            key: scene_index.get(key)
            for key in (
                "wanted_path_count", "decoded_sgb_count", "ready_sgb_count",
                "blocked_sgb_count", "imb_path_identity_count",
            )
        },
        "boundary": {
            "scene_reference_proof": "ready source-backed SGB recursive OBJECT resource field + globally unique decoded IMB path payload SHA-256",
            "lod_relation_proof": "source-backed LOD parent, child slot index and serialized distance table",
            "zero_lod_distance_policy": "preserve the proven runtime fallback rule; do not invent the effective threshold",
            "path_name_lod_diagnostic_used_for_selection": False,
            "unreferenced_candidate_is_contradicted": False,
            "single_static_scene_reference_is_draw_attribution": False,
            "source_backed_lod_family_is_selected_lod": False,
            "render_admission": False,
            "capture_requirement": "none; attach exact instance/LOD selection evidence before considering VB/IB payload capture",
        },
    }


def build_report(
    ambiguity: Mapping[str, Any],
    corpus: Iterable[str | Path],
) -> dict[str, Any]:
    corpus = list(corpus)
    wanted_paths = _wanted_candidate_paths(ambiguity)
    scene_index = load_static_scene_reference_index(corpus, wanted_paths)
    report = build_static_scene_reference_candidate_join(ambiguity, scene_index)
    report["corpus_inputs"] = [str(value) for value in corpus]
    report["wanted_imb_paths"] = sorted(wanted_paths)
    report["blocked_sgbs"] = list(scene_index.get("blocked_sgbs") or [])
    report["evidence_sha256"] = _canonical_hash({
        "summary": report["summary"],
        "draws": report["draws"],
    })
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ambiguity_audit")
    parser.add_argument("output")
    parser.add_argument("--corpus", action="append", required=True)
    args = parser.parse_args(argv)

    ambiguity = json.loads(resolve_input_path(args.ambiguity_audit).read_text(encoding="utf-8"))
    report = build_report(ambiguity, args.corpus)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
