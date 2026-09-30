"""Join exact runtime IMB resource evidence to pre-admission SGB object candidates.

The join is deliberately weaker than scene admission. Runtime archive/path/SHA
is revalidated against the IR manifest, then SGB placement/wrapper/object rows
are narrowed by the same logical resource path. SGB contracts do not currently
carry their source archive identity, so this module never upgrades a logical
path match into exact OBJECT/runtime attribution by itself.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.SGBRuntimeObjectCandidateJoin/1"
PLACEMENT_FORMAT = "SHIFT.SGBScenePlacement/1"
HANDOFF_FORMAT = "SHIFT.SGBObjectRenderHandoffSet/1"
CAPTURE_FORMAT = "SHIFT.IMBRuntimeCapturePipeline/1"


def _norm_ref(value: Any) -> str:
    return re.sub(
        r"/+",
        "/",
        str(value or "").replace("\\", "/"),
    ).lower().lstrip("./")


def _placement_wrapper_key(
    placement: Mapping[str, Any],
) -> tuple[str, Any] | None:
    mode = placement.get("mode")
    if mode == "flat-summ":
        chunk = "SUMM"
    elif mode == "part-node":
        chunk = "NODE"
    else:
        return None
    object_row = placement.get("object")
    if not isinstance(object_row, Mapping):
        return None
    return chunk, object_row.get("source_record_index")


def _handoff_wrapper_key(
    row: Mapping[str, Any],
) -> tuple[str, Any] | None:
    wrapper = row.get("wrapper")
    if not isinstance(wrapper, Mapping):
        return None
    chunk = wrapper.get("chunk")
    index = wrapper.get("source_record_index")
    if chunk not in {"NODE", "SUMM"} or index is None:
        return None
    return str(chunk), index


def _sha256(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    if len(text) != 64:
        return None
    try:
        int(text, 16)
    except ValueError:
        return None
    return text


def _scene_candidates(
    scene_placement: Mapping[str, Any],
    object_handoffs: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    blockers: list[str] = []
    placements = [
        row
        for row in (scene_placement.get("placements") or [])
        if isinstance(row, Mapping)
    ]
    handoffs = [
        row
        for row in (object_handoffs.get("objects") or [])
        if isinstance(row, Mapping)
    ]
    if not placements:
        blockers.append("runtime-object-join:no-scene-placements")
    if not handoffs:
        blockers.append("runtime-object-join:no-object-handoffs")

    by_key: dict[tuple[str, Any], list[Mapping[str, Any]]] = {}
    for index, row in enumerate(handoffs):
        key = _handoff_wrapper_key(row)
        if key is None:
            blockers.append(
                f"runtime-object-join:handoff-{index}:wrapper-identity-missing"
            )
            continue
        by_key.setdefault(key, []).append(row)

    candidates: list[dict[str, Any]] = []
    for placement_ordinal, placement in enumerate(placements):
        key = _placement_wrapper_key(placement)
        if key is None:
            blockers.append(
                f"runtime-object-join:placement-{placement_ordinal}:"
                "wrapper-identity-missing"
            )
            continue
        matches = by_key.get(key, [])
        for handoff_ordinal, row in enumerate(matches):
            handoff = row.get("handoff")
            if not isinstance(handoff, Mapping):
                continue
            resource = handoff.get("resource")
            transform = handoff.get("transform")
            resource = resource if isinstance(resource, Mapping) else {}
            transform = transform if isinstance(transform, Mapping) else {}
            resource_ref = resource.get("reference")
            if not resource_ref:
                continue
            candidates.append({
                "scene_candidate_index": len(candidates),
                "placement_index": placement.get(
                    "placement_index",
                    placement_ordinal,
                ),
                "placement_mode": placement.get("mode"),
                "placement_identity": placement.get("identity"),
                "placement_spatial": placement.get("spatial"),
                "wrapper": {
                    "chunk": key[0],
                    "source_record_index": key[1],
                },
                "object_path": row.get("object_path"),
                "wrapper_object_ordinal": handoff_ordinal,
                "resource_reference": str(resource_ref),
                "normalized_resource_reference": _norm_ref(resource_ref),
                "handoff_ready": handoff.get("ready") is True,
                "transform_mode": transform.get("mode"),
                "matrix_number": transform.get("matrix_number"),
                "numeric_world_matrix_ready": (
                    transform.get("world_matrix_ready") is True
                ),
                "world_matrix": transform.get("world_matrix"),
            })

    if not candidates and not blockers:
        blockers.append("runtime-object-join:no-scene-candidates")
    return candidates, list(dict.fromkeys(blockers))


def _manifest_rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(
        value, (str, bytes, bytearray)
    ):
        raise ValueError("IR manifest must be a JSON array")
    return [
        dict(row)
        for row in value
        if isinstance(row, Mapping) and "error" not in row
    ]


def build_runtime_object_candidate_join(
    scene_placement: Mapping[str, Any],
    object_handoffs: Mapping[str, Any],
    capture_pipeline: Mapping[str, Any],
    ir_manifest: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if scene_placement.get("format") != PLACEMENT_FORMAT:
        raise ValueError(
            "placement input must be SHIFT.SGBScenePlacement/1"
        )
    if object_handoffs.get("format") != HANDOFF_FORMAT:
        raise ValueError(
            "handoff input must be SHIFT.SGBObjectRenderHandoffSet/1"
        )
    if capture_pipeline.get("format") != CAPTURE_FORMAT:
        raise ValueError(
            "capture input must be SHIFT.IMBRuntimeCapturePipeline/1"
        )

    blockers: list[str] = []
    if scene_placement.get("ready") is not True:
        blockers.append("runtime-object-join:scene-placement-not-ready")
    if capture_pipeline.get("pipeline_ready") is not True:
        blockers.append("runtime-object-join:capture-pipeline-not-ready")

    candidates, candidate_blockers = _scene_candidates(
        scene_placement,
        object_handoffs,
    )
    blockers.extend(candidate_blockers)
    manifest = _manifest_rows(ir_manifest)

    by_manifest_identity: dict[
        tuple[str, str, str],
        list[dict[str, Any]],
    ] = {}
    for row in manifest:
        archive = str(row.get("archive") or "")
        path = _norm_ref(row.get("path"))
        sha = _sha256(row.get("sha256"))
        if not archive or not path or sha is None:
            continue
        by_manifest_identity.setdefault(
            (archive, path, sha),
            [],
        ).append(row)

    resources: list[dict[str, Any]] = []
    exact_resource_count = 0
    matched_resource_count = 0
    unique_candidate_resource_count = 0

    for ordinal, resource in enumerate(
        capture_pipeline.get("resource_results") or []
    ):
        if not isinstance(resource, Mapping):
            continue
        archive = str(resource.get("archive") or "")
        path = str(resource.get("resource_path") or "")
        normalized_path = _norm_ref(path)
        sha = _sha256(resource.get("resource_sha256"))
        gate = (
            (resource.get("runtime_evidence") or {})
            .get("same_instance_gate")
        )
        gate_ready = (
            isinstance(gate, Mapping)
            and gate.get("ready") is True
        )

        row_blockers: list[str] = []
        if not archive:
            row_blockers.append("runtime-archive-missing")
        if not normalized_path:
            row_blockers.append("runtime-resource-path-missing")
        if sha is None:
            row_blockers.append("runtime-resource-sha256-invalid")
        if not gate_ready:
            row_blockers.append("runtime-same-instance-gate-not-ready")

        manifest_hits: list[dict[str, Any]] = []
        if archive and normalized_path and sha is not None:
            manifest_hits = by_manifest_identity.get(
                (archive, normalized_path, sha),
                [],
            )
            if not manifest_hits:
                row_blockers.append(
                    "runtime-resource-ir-identity-not-found"
                )

        scene_hits = [
            dict(candidate)
            for candidate in candidates
            if candidate["normalized_resource_reference"]
            == normalized_path
        ]
        if not scene_hits:
            row_blockers.append(
                "logical-scene-resource-candidate-not-found"
            )

        exact_resource_ready = (
            gate_ready
            and bool(manifest_hits)
            and sha is not None
        )
        if exact_resource_ready:
            exact_resource_count += 1
        if exact_resource_ready and scene_hits:
            matched_resource_count += 1
        if exact_resource_ready and len(scene_hits) == 1:
            unique_candidate_resource_count += 1

        resources.append({
            "runtime_resource_index": resource.get(
                "resource_index",
                ordinal,
            ),
            "archive": archive or None,
            "resource_path": path or None,
            "normalized_resource_path": normalized_path or None,
            "resource_sha256": sha,
            "candidate_binding_indices": list(
                resource.get("candidate_binding_indices") or []
            ),
            "runtime_same_instance_gate_ready": gate_ready,
            "ir_manifest_identity_ready": bool(manifest_hits),
            "ir_manifest_match_count": len(manifest_hits),
            "exact_runtime_resource_ready": exact_resource_ready,
            "scene_candidate_count": len(scene_hits),
            "unique_logical_scene_candidate": (
                exact_resource_ready and len(scene_hits) == 1
            ),
            "scene_candidates": scene_hits,
            "status": (
                "unique-candidate"
                if exact_resource_ready and len(scene_hits) == 1
                else "ambiguous"
                if exact_resource_ready and len(scene_hits) > 1
                else "blocked"
            ),
            "blocking_reasons": list(
                dict.fromkeys(row_blockers)
            ),
        })

    if not resources:
        blockers.append("runtime-object-join:no-runtime-resources")

    blockers = list(dict.fromkeys(blockers))
    pipeline_ready = not blockers
    resource_count = len(resources)
    all_resources_matched = (
        pipeline_ready
        and resource_count > 0
        and matched_resource_count == resource_count
    )
    identity_complete = (
        all_resources_matched
        and unique_candidate_resource_count == resource_count
    )

    if not pipeline_ready:
        status = "blocked"
    elif identity_complete:
        status = "unique-candidates"
    elif matched_resource_count:
        status = "partial"
    else:
        status = "not-found"

    return {
        "format": FORMAT,
        "version": 1,
        "status": status,
        "ready": pipeline_ready,
        "identity_complete": identity_complete,
        "blocking_reasons": blockers,
        "scene_candidate_count": len(candidates),
        "runtime_resource_count": resource_count,
        "exact_runtime_resource_count": exact_resource_count,
        "matched_runtime_resource_count": matched_resource_count,
        "unique_candidate_resource_count": (
            unique_candidate_resource_count
        ),
        "scene_candidates": candidates,
        "resources": resources,
        "boundary": {
            "runtime_resource_identity": (
                "exact D3D9 same-instance archive/path/SHA revalidated "
                "against IR manifest"
            ),
            "scene_candidate_identity": (
                "SGB placement wrapper + object_path + logical resource path"
            ),
            "sgb_source_archive_identity_available": False,
            "unique_logical_candidate_is_render_admission": False,
            "authorizes_multimatrix_root_solve": False,
            "authorizes_world_matrix": False,
            "authorizes_render_admission": False,
            "uses_render_binding_admission_index": False,
            "next_stage": (
                "attach an independent transform/spatial witness before "
                "promoting one candidate OBJECT"
            ),
        },
    }


def validate_files(
    scene_placement_path: str | Path,
    object_handoffs_path: str | Path,
    capture_pipeline_path: str | Path,
    ir_root: str | Path,
) -> dict[str, Any]:
    placement = json.loads(
        Path(scene_placement_path).read_text(encoding="utf-8")
    )
    handoffs = json.loads(
        Path(object_handoffs_path).read_text(encoding="utf-8")
    )
    capture = json.loads(
        Path(capture_pipeline_path).read_text(encoding="utf-8")
    )
    manifest = json.loads(
        (Path(ir_root) / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    if not isinstance(placement, Mapping):
        raise ValueError("placement JSON must be an object")
    if not isinstance(handoffs, Mapping):
        raise ValueError("handoff JSON must be an object")
    if not isinstance(capture, Mapping):
        raise ValueError("capture JSON must be an object")
    return build_runtime_object_candidate_join(
        placement,
        handoffs,
        capture,
        manifest,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene_placement")
    parser.add_argument("object_handoffs")
    parser.add_argument("capture_pipeline")
    parser.add_argument("ir_root")
    parser.add_argument("output")
    args = parser.parse_args(argv)

    report = validate_files(
        args.scene_placement,
        args.object_handoffs,
        args.capture_pipeline,
        args.ir_root,
    )
    Path(args.output).write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "identity_complete": report["identity_complete"],
        "runtime_resource_count": report[
            "runtime_resource_count"
        ],
        "matched_runtime_resource_count": report[
            "matched_runtime_resource_count"
        ],
        "unique_candidate_resource_count": report[
            "unique_candidate_resource_count"
        ],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
