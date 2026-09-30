"""Orchestrate the Silverstone IMB D3D9 attribution pipeline.

Pipeline:
  runtime target set -> raw shader prefilter -> draw-range routing
  -> exact IMB runtime binding evidence -> same-instance shader variant match.

The pipeline narrows expensive runtime reconstruction to candidate IMB
resources, but does not weaken any Phase 572 attribution gate.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from d3d9_runtime_trace import build_runtime_binding_evidence, load_events
from imb_raw_capture_shader_prefilter import prefilter_imb_raw_capture
from imb_runtime_resource_evidence import build_imb_runtime_resource_evidence_set
from imb_runtime_shader_variant_match import match_imb_runtime_shader_variants

FORMAT = "SHIFT.IMBRuntimeCapturePipeline/1"
TARGET_FORMAT = "SHIFT.IMBRuntimeShaderTargetSet/1"


def _load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object expected: {path}")
    return value


def _load_usage_map(path: str | Path | None) -> dict[int, int] | None:
    if path is None:
        return None
    value = _load_json(path)
    raw = value.get("usage_map") if isinstance(value.get("usage_map"), dict) else value
    if not isinstance(raw, dict):
        raise ValueError("usage map must be a JSON object")
    return {int(key): int(item) for key, item in raw.items()}


def _draw_matches_binding(
    draw: Mapping[str, Any],
    binding: Mapping[str, Any],
) -> bool:
    draw_range = binding.get("draw_range")
    if not isinstance(draw_range, Mapping):
        return False
    try:
        start_index = int(draw.get("start_index"))
        primitive_count = int(draw.get("primitive_count"))
        first_index = int(draw_range.get("first_index"))
        index_count = int(draw_range.get("index_count"))
    except (TypeError, ValueError):
        return False
    return (
        index_count > 0
        and index_count % 3 == 0
        and start_index == first_index
        and primitive_count == index_count // 3
    )


def route_prefilter_candidate_bindings(
    target_set: Mapping[str, Any],
    prefilter: Mapping[str, Any],
) -> dict[str, Any]:
    """Route shader hits to bindings using only source-backed draw ranges.

    This stage is still not resource proof. It only rejects bindings whose
    source draw range cannot equal the observed raw DrawIndexedPrimitive.
    """
    by_index = {
        int(row.get("binding_index")): row
        for row in (target_set.get("binding_targets") or [])
        if isinstance(row, Mapping) and row.get("binding_index") is not None
    }
    routed_indices: set[int] = set()
    route_rows: list[dict[str, Any]] = []

    for draw in prefilter.get("candidate_draws") or []:
        if not isinstance(draw, Mapping):
            continue
        matched: list[int] = []
        for raw_index in draw.get("candidate_binding_indices") or []:
            try:
                binding_index = int(raw_index)
            except (TypeError, ValueError):
                continue
            binding = by_index.get(binding_index)
            if binding is None or not _draw_matches_binding(draw, binding):
                continue
            matched.append(binding_index)
            routed_indices.add(binding_index)
        route_rows.append({
            "line": draw.get("line"),
            "frame": draw.get("frame"),
            "event_index": draw.get("event_index"),
            "draw_ordinal": draw.get("draw_ordinal"),
            "start_index": draw.get("start_index"),
            "primitive_count": draw.get("primitive_count"),
            "shader_candidate_binding_indices": sorted({
                int(value)
                for value in (draw.get("candidate_binding_indices") or [])
                if str(value).lstrip("-").isdigit()
            }),
            "routed_binding_indices": sorted(set(matched)),
        })

    return {
        "format": "SHIFT.IMBRuntimeCaptureRoute/1",
        "candidate_draw_count": len(route_rows),
        "routed_binding_count": len(routed_indices),
        "routed_binding_indices": sorted(routed_indices),
        "draw_routes": route_rows,
        "boundary": {
            "shader_identity": "Phase 569 prefilter evidence",
            "draw_identity": "exact source-backed first_index/index_count",
            "resource_identity_proven": False,
            "same_instance_proven": False,
        },
    }


def _candidate_resources(
    resource_set: Mapping[str, Any],
    routed_binding_indices: Iterable[int],
) -> list[Mapping[str, Any]]:
    wanted = {int(value) for value in routed_binding_indices}
    rows: list[Mapping[str, Any]] = []
    for resource in resource_set.get("resources") or []:
        if not isinstance(resource, Mapping):
            continue
        owned = {
            int(value)
            for value in (resource.get("binding_indices") or [])
        }
        if wanted & owned:
            rows.append(resource)
    return rows


def _runtime_draw_snapshot(
    runtime: Mapping[str, Any],
    frame_id: Any,
    draw_index: Any,
) -> Mapping[str, Any] | None:
    for frame in runtime.get("frames") or []:
        if not isinstance(frame, Mapping):
            continue
        if frame.get("frame") != frame_id:
            continue
        for snapshot in frame.get("draw_snapshots") or []:
            if (
                isinstance(snapshot, Mapping)
                and snapshot.get("draw_index") == draw_index
            ):
                return snapshot
    return None


def _selected_runtime_draw_keys(
    result: Mapping[str, Any],
) -> list[tuple[Any, Any]]:
    if result.get("attributed") is not True:
        return []
    selected = result.get("selected_variant")
    if not isinstance(selected, Mapping):
        return []
    selected_key = tuple(selected.get("variant_key") or [])
    try:
        best_score = int(selected.get("score"))
    except (TypeError, ValueError):
        return []
    if not selected_key or best_score < 80:
        return []

    keys: set[tuple[Any, Any]] = set()
    for observed in result.get("matches") or []:
        if not isinstance(observed, Mapping):
            continue
        for variant in observed.get("variant_matches") or []:
            if not isinstance(variant, Mapping):
                continue
            try:
                score = int(variant.get("score"))
            except (TypeError, ValueError):
                continue
            if (
                score == best_score
                and tuple(variant.get("variant_key") or [])
                == selected_key
            ):
                keys.add(
                    (
                        observed.get("frame"),
                        observed.get("draw_index"),
                    )
                )
    return sorted(
        keys,
        key=lambda row: (
            str(row[0]),
            int(row[1]) if isinstance(row[1], int) else -1,
        ),
    )


def _attributed_texture_observations(
    runtime: Mapping[str, Any],
    candidate_results: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[int, Any, Any]] = set()
    for result in candidate_results:
        if not isinstance(result, Mapping):
            continue
        try:
            binding_index = int(result.get("binding_index"))
        except (TypeError, ValueError):
            continue
        for frame_id, draw_index in _selected_runtime_draw_keys(result):
            key = (binding_index, frame_id, draw_index)
            if key in seen:
                continue
            seen.add(key)
            snapshot = _runtime_draw_snapshot(
                runtime,
                frame_id,
                draw_index,
            )
            if snapshot is None:
                rows.append({
                    "binding_index": binding_index,
                    "frame": frame_id,
                    "draw_index": draw_index,
                    "status": "blocked",
                    "blocking_reasons": [
                        "runtime-draw-snapshot-not-found"
                    ],
                    "active_texture_bindings": [],
                })
                continue

            textures: list[dict[str, Any]] = []
            for binding in (
                snapshot.get("active_texture_bindings") or []
            ):
                if not isinstance(binding, Mapping):
                    continue
                try:
                    stage = int(binding.get("stage"))
                except (TypeError, ValueError):
                    continue
                creation = binding.get("resource_creation")
                textures.append({
                    "stage": stage,
                    "texture_ptr": binding.get("texture_ptr"),
                    "resource_creation_status": binding.get(
                        "resource_creation_status"
                    ),
                    "resource_creation": (
                        dict(creation)
                        if isinstance(creation, Mapping)
                        else None
                    ),
                    "snapshot_status": binding.get("snapshot_status"),
                    "snapshot_paths": [
                        str(path)
                        for path in (
                            binding.get("snapshot_paths") or []
                        )
                        if isinstance(path, str)
                    ],
                })
            rows.append({
                "binding_index": binding_index,
                "frame": frame_id,
                "draw_index": draw_index,
                "status": "observed",
                "blocking_reasons": [],
                "active_texture_bindings": textures,
            })
    return rows


def _compact_runtime(
    runtime: Mapping[str, Any],
) -> dict[str, Any]:
    gate = runtime.get("same_instance_gate") or {}
    return {
        "format": runtime.get("format"),
        "status": runtime.get("status"),
        "trace": dict(runtime.get("trace") or {}),
        "same_instance_gate": {
            "status": gate.get("status"),
            "ready": gate.get("ready") is True,
            "candidate_count": len(gate.get("candidate_frames") or []),
            "blocking_reasons": list(gate.get("blocking_reasons") or []),
        },
        "blocking_reasons": list(runtime.get("blocking_reasons") or []),
    }


def build_imb_runtime_capture_pipeline(
    target_set: Mapping[str, Any],
    events: Iterable[Mapping[str, Any]],
    *,
    usage_ordinal_map: Mapping[int, int] | None = None,
) -> dict[str, Any]:
    if target_set.get("format") != TARGET_FORMAT:
        raise ValueError(
            "target input must be SHIFT.IMBRuntimeShaderTargetSet/1"
        )

    event_rows = [dict(row) for row in events]
    prefilter = prefilter_imb_raw_capture(target_set, event_rows)
    routing = route_prefilter_candidate_bindings(target_set, prefilter)
    resource_set = build_imb_runtime_resource_evidence_set(target_set)

    blockers: list[str] = []
    blockers.extend(prefilter.get("blocking_reasons") or [])
    blockers.extend(resource_set.get("blocking_reasons") or [])
    if target_set.get("same_instance_match_ready") is not True:
        blockers.append("target-set:same-instance-match-not-ready")
    if usage_ordinal_map is None:
        blockers.append("usage-ordinal-map:not-supplied")

    candidate_resources = _candidate_resources(
        resource_set, routing["routed_binding_indices"]
    )
    resource_results: list[dict[str, Any]] = []
    attributed_candidate_indices: set[int] = set()
    observed_candidate_indices: set[int] = set()
    routed = set(routing["routed_binding_indices"])

    for resource in candidate_resources:
        runtime_input = resource.get("runtime_binding_input")
        if not isinstance(runtime_input, Mapping):
            blockers.append(
                f"resource-{resource.get('resource_index')}:runtime-input-missing"
            )
            continue
        runtime = build_runtime_binding_evidence(
            event_rows,
            meb_resource=runtime_input,
            usage_ordinal_map=(
                dict(usage_ordinal_map)
                if usage_ordinal_map is not None
                else None
            ),
        )
        match = match_imb_runtime_shader_variants(target_set, runtime)
        candidate_indices = sorted(
            routed & {
                int(value)
                for value in (resource.get("binding_indices") or [])
            }
        )
        candidate_results = [
            row
            for row in (match.get("binding_results") or [])
            if isinstance(row, Mapping)
            and int(row.get("binding_index")) in candidate_indices
        ]
        for row in candidate_results:
            index = int(row["binding_index"])
            if row.get("observed") is True:
                observed_candidate_indices.add(index)
            if row.get("attributed") is True:
                attributed_candidate_indices.add(index)

        texture_observations = _attributed_texture_observations(
            runtime,
            candidate_results,
        )
        resource_results.append({
            "resource_index": resource.get("resource_index"),
            "archive": resource.get("archive"),
            "resource_path": resource.get("resource_path"),
            "resource_sha256": resource.get("resource_sha256"),
            "candidate_binding_indices": candidate_indices,
            "runtime_evidence": _compact_runtime(runtime),
            "attributed_texture_observations": texture_observations,
            "variant_match": {
                "format": match.get("format"),
                "status": match.get("status"),
                "ready": match.get("ready") is True,
                "blocking_reasons": list(
                    match.get("blocking_reasons") or []
                ),
                "summary": dict(match.get("summary") or {}),
                "candidate_binding_results": candidate_results,
            },
        })

    pipeline_ready = (
        target_set.get("same_instance_match_ready") is True
        and prefilter.get("prefilter_ready") is True
        and resource_set.get("ready") is True
        and usage_ordinal_map is not None
        and not blockers
    )
    routed_count = len(routed)
    attributed_count = len(attributed_candidate_indices)
    observed_count = len(observed_candidate_indices)
    attribution_complete = (
        pipeline_ready
        and routed_count > 0
        and attributed_count == routed_count
    )

    if not pipeline_ready:
        status = "blocked"
    elif routed_count == 0:
        status = "not-found"
    elif attribution_complete:
        status = "ready"
    elif observed_count:
        status = "partial"
    else:
        status = "not-attributed"

    return {
        "format": FORMAT,
        "version": 1,
        "status": status,
        "pipeline_ready": pipeline_ready,
        "attribution_complete": attribution_complete,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "summary": {
            "event_count": len(event_rows),
            "prefilter_candidate_draw_count": int(
                (prefilter.get("summary") or {}).get(
                    "candidate_draw_count", 0
                )
            ),
            "routed_binding_count": routed_count,
            "candidate_resource_count": len(candidate_resources),
            "runtime_report_count": len(resource_results),
            "attributed_texture_observation_count": sum(
                len(
                    row.get(
                        "attributed_texture_observations"
                    ) or []
                )
                for row in resource_results
            ),
            "observed_candidate_binding_count": observed_count,
            "attributed_candidate_binding_count": attributed_count,
            "blocked_candidate_binding_count": (
                routed_count - attributed_count
            ),
        },
        "prefilter": prefilter,
        "routing": routing,
        "resource_evidence": {
            "format": resource_set.get("format"),
            "ready": resource_set.get("ready") is True,
            "resource_count": resource_set.get("resource_count"),
            "binding_target_count": resource_set.get(
                "binding_target_count"
            ),
            "blocking_reasons": list(
                resource_set.get("blocking_reasons") or []
            ),
        },
        "resource_results": resource_results,
        "boundary": {
            "candidate_routing_claims_resource_identity": False,
            "runtime_resource_identity": (
                "proven only inside D3D9RuntimeBindingEvidence/1"
            ),
            "attribution_contract": (
                "SHIFT.IMBRuntimeShaderVariantMatch/1"
            ),
            "retains_full_runtime_frames": False,
            "retains_attributed_draw_texture_observations": True,
            "texture_observation_scope": (
                "only runtime draw snapshots supporting the selected "
                "strong shader variant"
            ),
            "purpose": (
                "orchestrate authentic Silverstone capture attribution "
                "without repeating full runtime reconstruction for "
                "shader/draw-incompatible IMB resources"
            ),
        },
    }


def validate_files(
    target_set_path: str | Path,
    capture_jsonl_path: str | Path,
    *,
    usage_map_path: str | Path | None = None,
) -> dict[str, Any]:
    target_set = _load_json(target_set_path)
    events = load_events(capture_jsonl_path)
    usage = _load_usage_map(usage_map_path)
    return build_imb_runtime_capture_pipeline(
        target_set,
        events,
        usage_ordinal_map=usage,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target_set")
    parser.add_argument("capture_jsonl")
    parser.add_argument("output")
    parser.add_argument("--usage-map")
    args = parser.parse_args(argv)

    report = validate_files(
        args.target_set,
        args.capture_jsonl,
        usage_map_path=args.usage_map,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "pipeline_ready": report["pipeline_ready"],
        "attribution_complete": report["attribution_complete"],
        "summary": report["summary"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["attribution_complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
