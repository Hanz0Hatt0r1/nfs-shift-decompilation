"""Resolve repeated SGB placements for Phase 624 exact resource draws.

Phase 624 can prove the exact IMB/LOD resource that produced one raw D3D9 draw
while still leaving multiple scene placements of that same resource.  This
stage joins those rows to ``SHIFT.SGBRuntimeObjectCandidateJoin/1`` and to the
already captured draw-local vertex constant state in
``SHIFT.IMBRuntimeCapturePipeline/1``.

A repeated instance is selected only when every relevant same-draw observation
matches exactly one complete source-backed scene world matrix by IEEE-754
float32 bytes, and all observations select the same scene candidate.  As in
Phase 591, both row-major and transpose layouts are tested without assigning a
semantic name to the register window.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.IMBRepeatedSceneInstanceTransformJoin/1"
RESOURCE_DRAW_FORMAT = "SHIFT.IMBRuntimeResourceDrawCandidateJoin/1"
OBJECT_JOIN_FORMAT = "SHIFT.SGBRuntimeObjectCandidateJoin/1"
PIPELINE_FORMAT = "SHIFT.IMBRuntimeCapturePipeline/1"


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


def _matrix16(value: Any) -> list[float] | None:
    if isinstance(value, list) and len(value) == 16:
        raw = list(value)
    elif (
        isinstance(value, list)
        and len(value) == 4
        and all(isinstance(row, list) and len(row) == 4 for row in value)
    ):
        raw = [item for row in value for item in row]
    else:
        return None
    result: list[float] = []
    for item in raw:
        if not isinstance(item, (int, float)) or isinstance(item, bool):
            return None
        number = float(item)
        if not math.isfinite(number):
            return None
        result.append(number)
    return result


def _f32_bytes(values: list[float]) -> bytes:
    return struct.pack("<16f", *[float(value) for value in values])


def _transpose(values: list[float]) -> list[float]:
    return [
        values[row + column * 4]
        for row in range(4)
        for column in range(4)
    ]


def _vertex_constant_windows(constant_state: Mapping[str, Any]) -> list[dict[str, Any]]:
    vertex = constant_state.get("vertex")
    if not isinstance(vertex, Mapping):
        return []
    registers: dict[int, list[float]] = {}
    for raw_register, raw_values in vertex.items():
        register = _safe_int(raw_register)
        if register is None or register < 0:
            continue
        if (
            not isinstance(raw_values, list)
            or len(raw_values) != 4
            or not all(
                isinstance(value, (int, float)) and not isinstance(value, bool)
                for value in raw_values
            )
        ):
            continue
        values = [float(value) for value in raw_values]
        if not all(math.isfinite(value) for value in values):
            continue
        registers[register] = values

    windows: list[dict[str, Any]] = []
    for start in sorted(registers):
        if not all(start + offset in registers for offset in range(4)):
            continue
        values = [
            value
            for offset in range(4)
            for value in registers[start + offset]
        ]
        windows.append({
            "start_register": start,
            "registers": [start + offset for offset in range(4)],
            "float32_hex": _f32_bytes(values).hex(),
        })
    return windows


def _scene_candidate_identity(candidate: Mapping[str, Any]) -> str:
    return _canonical_hash({
        "scene_candidate_index": candidate.get("scene_candidate_index"),
        "placement_index": candidate.get("placement_index"),
        "placement_mode": candidate.get("placement_mode"),
        "placement_identity": candidate.get("placement_identity"),
        "wrapper": candidate.get("wrapper"),
        "object_path": candidate.get("object_path"),
        "wrapper_object_ordinal": candidate.get("wrapper_object_ordinal"),
        "normalized_resource_reference": candidate.get("normalized_resource_reference"),
        "transform_mode": candidate.get("transform_mode"),
        "matrix_number": candidate.get("matrix_number"),
        "world_matrix": candidate.get("world_matrix"),
    })


def _compact_scene_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    matrix = _matrix16(candidate.get("world_matrix"))
    return {
        "scene_candidate_identity_sha256": _scene_candidate_identity(candidate),
        "scene_candidate_index": candidate.get("scene_candidate_index"),
        "placement_index": candidate.get("placement_index"),
        "placement_mode": candidate.get("placement_mode"),
        "placement_identity": candidate.get("placement_identity"),
        "placement_spatial": candidate.get("placement_spatial"),
        "wrapper": dict(candidate.get("wrapper") or {}),
        "object_path": list(candidate.get("object_path") or []),
        "wrapper_object_ordinal": candidate.get("wrapper_object_ordinal"),
        "resource_reference": candidate.get("resource_reference"),
        "normalized_resource_reference": _norm(
            candidate.get("normalized_resource_reference")
            or candidate.get("resource_reference")
        ),
        "handoff_ready": candidate.get("handoff_ready") is True,
        "transform_mode": candidate.get("transform_mode"),
        "matrix_number": candidate.get("matrix_number"),
        "numeric_world_matrix_ready": (
            candidate.get("numeric_world_matrix_ready") is True and matrix is not None
        ),
        "world_matrix": matrix,
    }


def _object_resource_candidates(
    object_join: Mapping[str, Any],
) -> dict[tuple[str, str], dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for resource in object_join.get("resources") or []:
        if not isinstance(resource, Mapping):
            continue
        path = _norm(resource.get("resource_path"))
        digest = _sha256(resource.get("resource_sha256"))
        if not path or digest is None:
            continue
        key = (path, digest)
        group = grouped.setdefault(key, {
            "exact_runtime_resource_ready": True,
            "resource_rows": [],
            "scene_candidates": {},
        })
        group["resource_rows"].append(dict(resource))
        if resource.get("exact_runtime_resource_ready") is not True:
            group["exact_runtime_resource_ready"] = False
        for candidate in resource.get("scene_candidates") or []:
            if not isinstance(candidate, Mapping):
                continue
            compact = _compact_scene_candidate(candidate)
            identity = compact["scene_candidate_identity_sha256"]
            group["scene_candidates"].setdefault(identity, compact)

    result: dict[tuple[str, str], dict[str, Any]] = {}
    for key, group in grouped.items():
        candidates = sorted(
            group["scene_candidates"].values(),
            key=lambda row: row["scene_candidate_identity_sha256"],
        )
        result[key] = {
            "exact_runtime_resource_ready": group["exact_runtime_resource_ready"],
            "resource_row_count": len(group["resource_rows"]),
            "scene_candidate_count": len(candidates),
            "scene_candidates": candidates,
        }
    return result


def _capture_observation_index(
    pipeline: Mapping[str, Any],
) -> dict[tuple[str, str, int, str, int], list[dict[str, Any]]]:
    result: dict[tuple[str, str, int, str, int], list[dict[str, Any]]] = defaultdict(list)
    seen: set[str] = set()
    for resource in pipeline.get("resource_results") or []:
        if not isinstance(resource, Mapping):
            continue
        path = _norm(resource.get("resource_path"))
        digest = _sha256(resource.get("resource_sha256"))
        if not path or digest is None:
            continue
        for observation in resource.get("attributed_texture_observations") or []:
            if not isinstance(observation, Mapping) or observation.get("status") != "observed":
                continue
            binding = _safe_int(observation.get("binding_index"))
            draw_index = _safe_int(observation.get("draw_index"))
            frame = observation.get("frame")
            if binding is None or draw_index is None:
                continue
            key = (path, digest, binding, str(frame), draw_index)
            compact = {
                "binding_index": binding,
                "frame": frame,
                "draw_index": draw_index,
                "constant_state": dict(observation.get("constant_state") or {}),
            }
            identity = _canonical_hash({"key": key, "constant_state": compact["constant_state"]})
            if identity in seen:
                continue
            seen.add(identity)
            result[key].append(compact)
    return dict(result)


def _candidate_matrix_matches(
    candidates: list[Mapping[str, Any]],
    observation: Mapping[str, Any],
) -> dict[str, Any]:
    incomplete = [
        candidate.get("scene_candidate_identity_sha256")
        for candidate in candidates
        if candidate.get("numeric_world_matrix_ready") is not True
        or _matrix16(candidate.get("world_matrix")) is None
    ]
    constant_state = observation.get("constant_state")
    constant_state = constant_state if isinstance(constant_state, Mapping) else {}
    windows = _vertex_constant_windows(constant_state)
    if incomplete:
        return {
            "status": "blocked-incomplete-scene-world-matrices",
            "selected_scene_candidate_identity_sha256": None,
            "matching_scene_candidate_identity_sha256s": [],
            "witnesses": [],
            "blocking_reasons": [
                f"scene-world-matrix-incomplete:{len(incomplete)}"
            ],
        }
    if not windows:
        return {
            "status": "blocked-vertex-constant-window-missing",
            "selected_scene_candidate_identity_sha256": None,
            "matching_scene_candidate_identity_sha256s": [],
            "witnesses": [],
            "blocking_reasons": ["vertex-constant-window-missing"],
        }

    witnesses: list[dict[str, Any]] = []
    matched_ids: set[str] = set()
    for candidate in candidates:
        identity = str(candidate.get("scene_candidate_identity_sha256") or "")
        matrix = _matrix16(candidate.get("world_matrix"))
        if not identity or matrix is None:
            continue
        row_bytes = _f32_bytes(matrix)
        transpose_bytes = _f32_bytes(_transpose(matrix))
        for window in windows:
            raw = bytes.fromhex(str(window["float32_hex"]))
            layouts: list[str] = []
            if raw == row_bytes:
                layouts.append("row-major")
            if raw == transpose_bytes:
                layouts.append("transpose")
            if not layouts:
                continue
            matched_ids.add(identity)
            witnesses.append({
                "scene_candidate_identity_sha256": identity,
                "start_register": window["start_register"],
                "registers": list(window["registers"]),
                "layouts": layouts,
                "float32_hex": window["float32_hex"],
            })

    matched = sorted(matched_ids)
    selected = matched[0] if len(matched) == 1 else None
    if selected:
        status = "exact-single-scene-world-matrix"
        reasons: list[str] = []
    elif matched:
        status = "ambiguous-multiple-scene-world-matrices"
        reasons = [f"scene-world-matrix-match-count:{len(matched)}"]
    else:
        status = "no-scene-world-matrix-match"
        reasons = ["exact-scene-world-matrix-window-not-found"]
    return {
        "status": status,
        "selected_scene_candidate_identity_sha256": selected,
        "matching_scene_candidate_identity_sha256s": matched,
        "witnesses": witnesses,
        "blocking_reasons": reasons,
    }


def _selected_resource_identity(row: Mapping[str, Any]) -> tuple[str, str] | None:
    candidate = row.get("selected_candidate")
    if not isinstance(candidate, Mapping):
        return None
    digest = _sha256(candidate.get("imb_sha256"))
    paths = {
        _norm(value)
        for value in (candidate.get("imb_paths") or [])
        if _norm(value)
    }
    if digest is None or not paths:
        return None
    witnesses = [
        witness
        for witness in (row.get("runtime_witnesses") or [])
        if isinstance(witness, Mapping)
        and _sha256(witness.get("resource_sha256")) == digest
        and _norm(witness.get("resource_path")) in paths
    ]
    identities = {
        (_norm(witness.get("resource_path")), digest)
        for witness in witnesses
        if _norm(witness.get("resource_path"))
    }
    return next(iter(identities)) if len(identities) == 1 else None


def build_repeated_scene_instance_transform_join(
    resource_draw: Mapping[str, Any],
    object_join: Mapping[str, Any],
    pipeline: Mapping[str, Any],
) -> dict[str, Any]:
    if resource_draw.get("format") != RESOURCE_DRAW_FORMAT:
        raise ValueError(f"resource draw must be {RESOURCE_DRAW_FORMAT}")
    if object_join.get("format") != OBJECT_JOIN_FORMAT:
        raise ValueError(f"object candidate join must be {OBJECT_JOIN_FORMAT}")
    if pipeline.get("format") != PIPELINE_FORMAT:
        raise ValueError(f"capture pipeline must be {PIPELINE_FORMAT}")

    object_index = _object_resource_candidates(object_join)
    observation_index = _capture_observation_index(pipeline)
    rows: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    resolved_count = 0

    upstream_rows = [
        row for row in (resource_draw.get("draws") or [])
        if isinstance(row, Mapping)
    ]
    repeated_rows = [
        row for row in upstream_rows
        if row.get("status") == "exact-resource-draw-repeated-scene-instance"
    ]
    non_instance_ambiguity = sum(
        row.get("status") not in {
            "exact-scene-resource-draw",
            "exact-resource-draw-repeated-scene-instance",
        }
        for row in upstream_rows
    )

    for row in repeated_rows:
        resource_identity = _selected_resource_identity(row)
        row_reasons: list[str] = []
        object_resource = object_index.get(resource_identity) if resource_identity else None
        if resource_identity is None:
            row_reasons.append("selected-runtime-resource-identity-not-unique")
        if object_join.get("ready") is not True:
            row_reasons.append("runtime-object-candidate-join-not-ready")
        if object_resource is None:
            row_reasons.append("exact-runtime-resource-not-found-in-object-candidate-join")
            candidates: list[dict[str, Any]] = []
        else:
            if object_resource.get("exact_runtime_resource_ready") is not True:
                row_reasons.append("object-candidate-resource-not-exact-runtime-ready")
            candidates = [dict(value) for value in object_resource.get("scene_candidates") or []]
            if len(candidates) < 2:
                row_reasons.append(
                    f"repeated-scene-candidate-coverage-insufficient:{len(candidates)}"
                )

        selected_sha = _sha256(
            (row.get("selected_candidate") or {}).get("imb_sha256")
            if isinstance(row.get("selected_candidate"), Mapping)
            else None
        )
        selected_paths = {
            _norm(value)
            for value in (
                (row.get("selected_candidate") or {}).get("imb_paths") or []
                if isinstance(row.get("selected_candidate"), Mapping)
                else []
            )
            if _norm(value)
        }
        runtime_witnesses = [
            dict(witness)
            for witness in (row.get("runtime_witnesses") or [])
            if isinstance(witness, Mapping)
            and selected_sha is not None
            and _sha256(witness.get("resource_sha256")) == selected_sha
            and _norm(witness.get("resource_path")) in selected_paths
        ]
        if not runtime_witnesses:
            row_reasons.append("phase624-selected-runtime-witness-missing")

        observation_rows: list[dict[str, Any]] = []
        selected_scene_ids: set[str] = set()
        all_observations_resolved = True
        for witness in runtime_witnesses:
            path = _norm(witness.get("resource_path"))
            digest = _sha256(witness.get("resource_sha256"))
            binding = _safe_int(witness.get("binding_index"))
            draw_index = _safe_int(witness.get("draw_index"))
            frame = witness.get("frame")
            if not path or digest is None or binding is None or draw_index is None:
                observation_rows.append({
                    "status": "blocked-runtime-witness-key-incomplete",
                    "runtime_witness": witness,
                    "capture_observation_count": 0,
                    "matches": [],
                    "blocking_reasons": ["runtime-witness-key-incomplete"],
                })
                all_observations_resolved = False
                continue
            observations = observation_index.get(
                (path, digest, binding, str(frame), draw_index),
                [],
            )
            if not observations:
                observation_rows.append({
                    "status": "blocked-draw-local-constant-observation-missing",
                    "runtime_witness": witness,
                    "capture_observation_count": 0,
                    "matches": [],
                    "blocking_reasons": ["same-resource-binding-frame-draw-constant-observation-missing"],
                })
                all_observations_resolved = False
                continue

            match_rows = [
                _candidate_matrix_matches(candidates, observation)
                for observation in observations
            ]
            local_selected = {
                str(match.get("selected_scene_candidate_identity_sha256"))
                for match in match_rows
                if match.get("selected_scene_candidate_identity_sha256")
            }
            local_ready = (
                len(match_rows) > 0
                and all(match.get("status") == "exact-single-scene-world-matrix" for match in match_rows)
                and len(local_selected) == 1
            )
            if local_ready:
                selected_scene_ids.update(local_selected)
            else:
                all_observations_resolved = False
            observation_rows.append({
                "status": "resolved" if local_ready else "blocked",
                "runtime_witness": witness,
                "capture_observation_count": len(observations),
                "selected_scene_candidate_identity_sha256s": sorted(local_selected),
                "matches": match_rows,
                "blocking_reasons": list(dict.fromkeys(
                    reason
                    for match in match_rows
                    for reason in (match.get("blocking_reasons") or [])
                )),
            })

        if len(selected_scene_ids) > 1:
            row_reasons.append(
                f"same-draw-transform-observations-disagree:{len(selected_scene_ids)}"
            )
            all_observations_resolved = False
        if observation_rows and not all_observations_resolved:
            row_reasons.append("same-draw-transform-observation-unresolved")

        selected_scene_id = (
            next(iter(selected_scene_ids))
            if all_observations_resolved and len(selected_scene_ids) == 1 and not row_reasons
            else None
        )
        selected_scene_candidate = next(
            (
                candidate
                for candidate in candidates
                if candidate.get("scene_candidate_identity_sha256") == selected_scene_id
            ),
            None,
        ) if selected_scene_id else None
        if selected_scene_id and selected_scene_candidate is None:
            row_reasons.append("selected-scene-candidate-not-found")
            selected_scene_id = None

        ready = selected_scene_id is not None and not row_reasons
        if ready:
            status = "exact-repeated-scene-instance"
            resolved_count += 1
        elif any(
            reason.startswith("scene-world-matrix-incomplete")
            for observation in observation_rows
            for match in observation.get("matches") or []
            for reason in (match.get("blocking_reasons") or [])
        ):
            status = "blocked-incomplete-scene-world-matrices"
        elif any(
            match.get("status") == "ambiguous-multiple-scene-world-matrices"
            for observation in observation_rows
            for match in observation.get("matches") or []
        ):
            status = "ambiguous-equal-or-multiple-world-matrix-matches"
        elif not observation_rows or any(
            observation.get("capture_observation_count") == 0
            for observation in observation_rows
        ):
            status = "draw-local-transform-observation-missing"
        else:
            status = "repeated-scene-instance-unresolved"
        status_counts[status] += 1

        rows.append({
            "event_index": row.get("event_index"),
            "frame": row.get("frame"),
            "draw_evidence_sha256": _sha256(row.get("draw_evidence_sha256")),
            "candidate_set_sha256": _sha256(row.get("candidate_set_sha256")),
            "resource_identity": (
                {"resource_path": resource_identity[0], "resource_sha256": resource_identity[1]}
                if resource_identity else None
            ),
            "scene_candidate_count": len(candidates),
            "scene_candidates": candidates,
            "runtime_witness_count": len(runtime_witnesses),
            "observation_results": observation_rows,
            "selected_scene_candidate_identity_sha256": selected_scene_id,
            "selected_scene_candidate": selected_scene_candidate,
            "status": status,
            "ready": ready,
            "blocking_reasons": list(dict.fromkeys(row_reasons)),
        })

    rows.sort(key=lambda value: (
        int(value.get("event_index")) if isinstance(value.get("event_index"), int) else 2**63 - 1,
        str(value.get("candidate_set_sha256") or ""),
    ))
    repeated_count = len(repeated_rows)
    unresolved_repeated = repeated_count - resolved_count
    remaining = non_instance_ambiguity + unresolved_repeated
    input_geometry_count = len(upstream_rows)
    already_exact = sum(
        row.get("status") == "exact-scene-resource-draw"
        for row in upstream_rows
    )
    ready = remaining == 0
    if input_geometry_count == 0:
        status = "not-needed"
    elif repeated_count == 0 and non_instance_ambiguity:
        status = "upstream-non-instance-ambiguity"
    elif repeated_count == 0:
        status = "not-needed"
    elif ready:
        status = "ready"
    elif resolved_count:
        status = "partial"
    else:
        status = "not-resolved"

    return {
        "format": FORMAT,
        "version": 1,
        "status": status,
        "ready": ready,
        "summary": {
            "input_geometry_draw_count": input_geometry_count,
            "already_exact_scene_resource_draw_count": already_exact,
            "repeated_instance_input_draw_count": repeated_count,
            "resolved_repeated_instance_draw_count": resolved_count,
            "unresolved_repeated_instance_draw_count": unresolved_repeated,
            "upstream_non_instance_ambiguity_count": non_instance_ambiguity,
            "remaining_scene_draw_ambiguity_count": remaining,
            "resolution_status_counts": dict(sorted(status_counts.items())),
            "runtime_object_candidate_join_ready": object_join.get("ready") is True,
            "capture_pipeline_ready": pipeline.get("pipeline_ready") is True,
        },
        "draws": rows,
        "source_reports": {
            "resource_draw": RESOURCE_DRAW_FORMAT,
            "object_candidate_join": OBJECT_JOIN_FORMAT,
            "capture_pipeline": PIPELINE_FORMAT,
        },
        "boundary": {
            "input_scope": "Phase 624 exact-resource-draw-repeated-scene-instance rows only",
            "resource_identity_reopened": False,
            "scene_candidate_source": "ready SHIFT.SGBRuntimeObjectCandidateJoin/1 exact runtime resource row",
            "world_matrix_requirement": "every surviving scene candidate must have a complete source-backed numeric world matrix",
            "constant_observation_join": "exact resource path+SHA + binding_index + frame + draw_index",
            "matrix_comparison": "exact-ieee754-float32-bytes",
            "accepted_layouts": ["row-major", "transpose"],
            "register_semantics_assigned": False,
            "requires_all_same_draw_observations_resolved": True,
            "equal_world_matrices_select_instance": False,
            "ranking_is_proof": False,
            "buffer_payload_relevant_to_instance_selection": False,
            "new_capture_required": False,
        },
        "evidence_sha256": _canonical_hash({
            "summary": {
                "input_geometry_draw_count": input_geometry_count,
                "repeated_instance_input_draw_count": repeated_count,
                "resolved_repeated_instance_draw_count": resolved_count,
                "upstream_non_instance_ambiguity_count": non_instance_ambiguity,
                "remaining_scene_draw_ambiguity_count": remaining,
            },
            "draws": rows,
        }),
    }


def validate_files(
    resource_draw_path: str | Path,
    object_join_path: str | Path,
    pipeline_path: str | Path,
) -> dict[str, Any]:
    resource_draw = json.loads(Path(resource_draw_path).read_text(encoding="utf-8"))
    object_join = json.loads(Path(object_join_path).read_text(encoding="utf-8"))
    pipeline = json.loads(Path(pipeline_path).read_text(encoding="utf-8"))
    if not all(isinstance(value, Mapping) for value in (resource_draw, object_join, pipeline)):
        raise ValueError("inputs must be JSON objects")
    return build_repeated_scene_instance_transform_join(
        resource_draw,
        object_join,
        pipeline,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("resource_draw")
    parser.add_argument("object_candidate_join")
    parser.add_argument("capture_pipeline")
    parser.add_argument("output")
    args = parser.parse_args(argv)
    report = validate_files(
        args.resource_draw,
        args.object_candidate_join,
        args.capture_pipeline,
    )
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
