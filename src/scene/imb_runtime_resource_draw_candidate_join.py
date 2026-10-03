"""Resolve Phase 623 geometry candidates with exact same-draw runtime resource proof.

The join consumes ``SHIFT.IMBStaticSceneReferenceCandidateJoin/1`` and
``SHIFT.IMBRuntimeCapturePipeline/1``.  A geometry candidate is selected only
when the capture pipeline already attributed one exact IMB resource and the
strong attributed match contains the *same* raw D3D9 draw event index as the
Phase 623 ambiguity row.  Path+SHA equality is required in addition to the
same-instance gate and strong shader-variant attribution.

This stage can prove which IMB/LOD resource produced a draw.  It does not claim
which repeated SGB placement instance produced that draw when the same exact
resource is referenced by multiple scene objects.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.IMBRuntimeResourceDrawCandidateJoin/1"
SCENE_FORMAT = "SHIFT.IMBStaticSceneReferenceCandidateJoin/1"
PIPELINE_FORMAT = "SHIFT.IMBRuntimeCapturePipeline/1"
MIN_STRONG_SCORE = 80


def _norm(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def _sha256(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    if len(text) != 64:
        return None
    try:
        int(text, 16)
    except ValueError:
        return None
    return text


def _safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _selected_variant_key(result: Mapping[str, Any]) -> tuple[int, tuple[str, ...]] | None:
    if result.get("attributed") is not True:
        return None
    selected = result.get("selected_variant")
    if not isinstance(selected, Mapping):
        return None
    score = _safe_int(selected.get("score"))
    key = selected.get("variant_key")
    if score is None or score < MIN_STRONG_SCORE:
        return None
    if not isinstance(key, list) or not key:
        return None
    return score, tuple(str(value) for value in key)


def _match_contains_selected_variant(
    match: Mapping[str, Any],
    selected_score: int,
    selected_key: tuple[str, ...],
) -> bool:
    for variant in match.get("variant_matches") or []:
        if not isinstance(variant, Mapping):
            continue
        score = _safe_int(variant.get("score"))
        key = variant.get("variant_key")
        if (
            score == selected_score
            and isinstance(key, list)
            and tuple(str(value) for value in key) == selected_key
        ):
            return True
    return False


def _runtime_event_witnesses(pipeline: Mapping[str, Any]) -> dict[int, list[dict[str, Any]]]:
    by_event: dict[int, list[dict[str, Any]]] = defaultdict(list)
    seen: set[tuple[Any, ...]] = set()

    for resource in pipeline.get("resource_results") or []:
        if not isinstance(resource, Mapping):
            continue
        path = str(resource.get("resource_path") or "").replace("\\", "/")
        path_key = _norm(path)
        resource_sha = _sha256(resource.get("resource_sha256"))
        runtime = resource.get("runtime_evidence")
        gate = runtime.get("same_instance_gate") if isinstance(runtime, Mapping) else None
        gate_ready = isinstance(gate, Mapping) and gate.get("ready") is True
        if not path_key or resource_sha is None or not gate_ready:
            continue

        variant_match = resource.get("variant_match")
        results = (
            variant_match.get("candidate_binding_results")
            if isinstance(variant_match, Mapping)
            else None
        )
        for result in results or []:
            if not isinstance(result, Mapping):
                continue
            selected = _selected_variant_key(result)
            if selected is None:
                continue
            selected_score, selected_key = selected

            binding_index = _safe_int(result.get("binding_index"))
            result_path = _norm(result.get("imb_path"))
            result_sha = _sha256(result.get("imb_sha256"))
            if binding_index is None:
                continue
            if result_path != path_key or result_sha != resource_sha:
                # Resource container and per-binding identity must agree exactly.
                continue

            for match in result.get("matches") or []:
                if not isinstance(match, Mapping):
                    continue
                draw = match.get("draw")
                if not isinstance(draw, Mapping):
                    continue
                event_index = _safe_int(draw.get("event_index"))
                if event_index is None:
                    continue
                if not _match_contains_selected_variant(
                    match,
                    selected_score,
                    selected_key,
                ):
                    continue
                identity = (
                    event_index,
                    binding_index,
                    path_key,
                    resource_sha,
                    selected_score,
                    selected_key,
                    match.get("frame"),
                    match.get("draw_index"),
                )
                if identity in seen:
                    continue
                seen.add(identity)
                by_event[event_index].append({
                    "event_index": event_index,
                    "frame": match.get("frame"),
                    "draw_index": match.get("draw_index"),
                    "binding_index": binding_index,
                    "resource_index": resource.get("resource_index"),
                    "archive": resource.get("archive"),
                    "resource_path": path,
                    "normalized_resource_path": path_key,
                    "resource_sha256": resource_sha,
                    "same_instance_gate_ready": True,
                    "strong_variant_score": selected_score,
                    "selected_variant_key": list(selected_key),
                    "selected_variant": dict(result.get("selected_variant") or {}),
                    "draw_range": dict(result.get("draw_range") or {}),
                    "primitive_index": result.get("primitive_index"),
                    "material_reference": result.get("material_reference"),
                    "shader_family": result.get("shader_family"),
                    "resource_identity_status": match.get("resource_identity_status"),
                    "gate_descriptor_match_count": match.get("gate_descriptor_match_count"),
                    "runtime_hashes": dict(match.get("runtime_hashes") or {}),
                    "captured_draw": dict(draw),
                })

    for rows in by_event.values():
        rows.sort(key=lambda row: (
            int(row.get("binding_index") or -1),
            str(row.get("normalized_resource_path") or ""),
            str(row.get("resource_sha256") or ""),
            int(row.get("draw_index") or -1),
        ))
    return dict(by_event)


def _candidate_identity(candidate: Mapping[str, Any]) -> tuple[str | None, set[str]]:
    digest = _sha256(candidate.get("imb_sha256"))
    paths = {
        _norm(value)
        for value in (candidate.get("imb_paths") or [])
        if _norm(value)
    }
    return digest, paths


def _candidate_matches_witness(
    candidate: Mapping[str, Any],
    witness: Mapping[str, Any],
) -> bool:
    digest, paths = _candidate_identity(candidate)
    return bool(
        digest
        and paths
        and digest == _sha256(witness.get("resource_sha256"))
        and _norm(witness.get("resource_path")) in paths
    )


def _compact_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "content_group_sha256": _sha256(candidate.get("content_group_sha256")),
        "imb_sha256": _sha256(candidate.get("imb_sha256")),
        "imb_paths": [
            str(value).replace("\\", "/")
            for value in (candidate.get("imb_paths") or [])
            if value
        ],
        "exact_scene_referenced": candidate.get("exact_scene_referenced") is True,
        "exact_scene_reference_count": _safe_int(candidate.get("exact_scene_reference_count")) or 0,
        "lod_parent_identity_sha256s": list(candidate.get("lod_parent_identity_sha256s") or []),
        "scene_references": [
            dict(row)
            for row in (candidate.get("scene_references") or [])
            if isinstance(row, Mapping)
        ],
    }


def build_runtime_resource_draw_candidate_join(
    scene_geometry: Mapping[str, Any],
    pipeline: Mapping[str, Any],
) -> dict[str, Any]:
    if scene_geometry.get("format") != SCENE_FORMAT:
        raise ValueError(f"scene geometry must be {SCENE_FORMAT}")
    if pipeline.get("format") != PIPELINE_FORMAT:
        raise ValueError(f"capture pipeline must be {PIPELINE_FORMAT}")

    witnesses_by_event = _runtime_event_witnesses(pipeline)
    rows: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    exact_resource_draw_count = 0
    exact_scene_draw_count = 0
    repeated_instance_count = 0
    conflict_count = 0

    for draw in scene_geometry.get("draws") or []:
        if not isinstance(draw, Mapping):
            continue
        event_index = _safe_int(draw.get("event_index"))
        candidates = [
            _compact_candidate(candidate)
            for candidate in (draw.get("candidate_results") or [])
            if isinstance(candidate, Mapping)
        ]
        witnesses = list(witnesses_by_event.get(event_index, [])) if event_index is not None else []

        candidate_witnesses: dict[str, list[dict[str, Any]]] = defaultdict(list)
        unmatched_witnesses: list[dict[str, Any]] = []
        for witness in witnesses:
            matched = [
                candidate
                for candidate in candidates
                if _candidate_matches_witness(candidate, witness)
            ]
            if not matched:
                unmatched_witnesses.append(dict(witness))
                continue
            for candidate in matched:
                content_sha = _sha256(candidate.get("content_group_sha256"))
                if content_sha:
                    candidate_witnesses[content_sha].append(dict(witness))

        exact_content = sorted(candidate_witnesses)
        selected_sha = exact_content[0] if len(exact_content) == 1 and not unmatched_witnesses else None
        selected_candidate = next(
            (
                candidate
                for candidate in candidates
                if _sha256(candidate.get("content_group_sha256")) == selected_sha
            ),
            None,
        ) if selected_sha else None

        if event_index is None:
            status = "draw-event-index-missing"
            blockers = ["phase623-draw-event-index-missing"]
        elif not witnesses:
            status = "no-exact-runtime-resource-draw-witness"
            blockers = ["strong-attributed-same-event-runtime-resource-witness-missing"]
        elif unmatched_witnesses:
            status = "runtime-resource-not-in-phase623-candidate-set"
            blockers = ["exact-runtime-witness-conflicts-with-phase623-candidate-set"]
            conflict_count += 1
        elif len(exact_content) > 1:
            status = "multiple-exact-runtime-resource-candidates"
            blockers = ["same-event-runtime-evidence-identifies-multiple-phase623-candidates"]
            conflict_count += 1
        elif selected_candidate is None:
            status = "runtime-resource-candidate-not-selected"
            blockers = ["runtime-resource-witness-did-not-select-a-content-group"]
        elif selected_candidate.get("exact_scene_referenced") is not True:
            status = "exact-runtime-resource-not-exact-scene-referenced"
            blockers = ["selected-runtime-resource-lacks-phase623-exact-scene-reference"]
            exact_resource_draw_count += 1
        else:
            exact_resource_draw_count += 1
            scene_reference_count = int(selected_candidate.get("exact_scene_reference_count") or 0)
            if scene_reference_count == 1:
                status = "exact-scene-resource-draw"
                blockers = []
                exact_scene_draw_count += 1
            elif scene_reference_count > 1:
                status = "exact-resource-draw-repeated-scene-instance"
                blockers = ["repeated-scene-instance-needs-transform-or-spatial-witness"]
                repeated_instance_count += 1
            else:
                status = "exact-runtime-resource-scene-reference-count-invalid"
                blockers = ["phase623-scene-reference-count-not-positive"]

        status_counts[status] += 1
        rows.append({
            "event_index": event_index,
            "frame": draw.get("frame"),
            "draw_evidence_sha256": _sha256(draw.get("draw_evidence_sha256")),
            "candidate_set_sha256": _sha256(draw.get("candidate_set_sha256")),
            "ambiguity_class": draw.get("ambiguity_class"),
            "input_candidate_count": len(candidates),
            "runtime_event_witness_count": len(witnesses),
            "runtime_candidate_content_group_sha256s": exact_content,
            "unmatched_runtime_witness_count": len(unmatched_witnesses),
            "selected_content_group_sha256": selected_sha,
            "selected_candidate": dict(selected_candidate) if isinstance(selected_candidate, Mapping) else None,
            "status": status,
            "ready": status == "exact-scene-resource-draw",
            "runtime_witnesses": witnesses,
            "unmatched_runtime_witnesses": unmatched_witnesses,
            "blocking_reasons": blockers,
        })

    rows.sort(key=lambda row: (
        int(row.get("event_index")) if isinstance(row.get("event_index"), int) else 2**63 - 1,
        str(row.get("candidate_set_sha256") or ""),
    ))
    total = len(rows)
    remaining = total - exact_scene_draw_count
    return {
        "format": FORMAT,
        "version": 1,
        "status": (
            "ready" if total > 0 and remaining == 0
            else "partial" if exact_resource_draw_count
            else "not-resolved" if total
            else "not-needed"
        ),
        "ready": total > 0 and remaining == 0,
        "summary": {
            "input_geometry_draw_count": total,
            "runtime_event_witness_count": sum(len(row["runtime_witnesses"]) for row in rows),
            "exact_resource_draw_count": exact_resource_draw_count,
            "exact_scene_resource_draw_count": exact_scene_draw_count,
            "repeated_scene_instance_draw_count": repeated_instance_count,
            "conflict_draw_count": conflict_count,
            "remaining_scene_draw_ambiguity_count": remaining,
            "resolution_status_counts": dict(sorted(status_counts.items())),
            "pipeline_ready": pipeline.get("pipeline_ready") is True,
            "pipeline_attribution_complete": pipeline.get("attribution_complete") is True,
        },
        "draws": rows,
        "source_reports": {
            "scene_geometry": SCENE_FORMAT,
            "capture_pipeline": PIPELINE_FORMAT,
        },
        "boundary": {
            "same_draw_join": "exact raw draw event_index equality",
            "runtime_resource_identity": "same-instance-gated exact IMB path+SHA",
            "shader_attribution": f"unique strong selected variant score >= {MIN_STRONG_SCORE}",
            "candidate_identity": "exact Phase 623 IMB path+SHA",
            "requires_phase623_exact_scene_reference": True,
            "unique_scene_reference_closes_scene_resource_draw": True,
            "repeated_scene_resource_reference_is_instance_attribution": False,
            "resource_draw_identity_is_world_transform_identity": False,
            "lod_name_pattern_used": False,
            "buffer_payload_used": False,
            "new_capture_required": False,
            "next_stage_for_repeated_instances": (
                "join exact captured world-matrix/transform evidence to the surviving repeated SGB scene references"
            ),
        },
        "evidence_sha256": _canonical_hash({
            "draws": rows,
            "summary": {
                "input_geometry_draw_count": total,
                "exact_resource_draw_count": exact_resource_draw_count,
                "exact_scene_resource_draw_count": exact_scene_draw_count,
                "repeated_scene_instance_draw_count": repeated_instance_count,
                "remaining_scene_draw_ambiguity_count": remaining,
            },
        }),
    }


def validate_files(
    scene_geometry_path: str | Path,
    pipeline_path: str | Path,
) -> dict[str, Any]:
    scene = json.loads(Path(scene_geometry_path).read_text(encoding="utf-8"))
    pipeline = json.loads(Path(pipeline_path).read_text(encoding="utf-8"))
    if not isinstance(scene, Mapping) or not isinstance(pipeline, Mapping):
        raise ValueError("inputs must be JSON objects")
    return build_runtime_resource_draw_candidate_join(scene, pipeline)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene_geometry")
    parser.add_argument("capture_pipeline")
    parser.add_argument("output")
    args = parser.parse_args(argv)
    report = validate_files(args.scene_geometry, args.capture_pipeline)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
