"""Orchestrate pre-admission SGB MatrixNumber transform recovery.

Phase 598 composes the already-proven Phase 595 candidate join, Phase 596
owner-scoped root consensus, Phase 597 root application and the existing
SGBRenderBindingAdmission boundary. It does not add a new transform heuristic.

The report compares baseline and recovered handoffs/admission so one authentic
capture can show exactly which MatrixNumber OBJECT rows became numerically
ready, which remained blocked, and whether ordinary scene admission improved.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from sgb_multimatrix_root_consensus import (
    build_multimatrix_root_consensus,
)
from sgb_object_render_handoff import (
    build_sgb_object_render_handoff_set,
)
from sgb_render_binding_admission import (
    build_sgb_render_binding_admission,
)
from sgb_runtime_object_candidate_join import (
    build_runtime_object_candidate_join,
)

FORMAT = "SHIFT.SGBRuntimeTransformRecoveryPipeline/1"
SGB_FORMAT = "SHIFT.SGBRuntime/1"
PLACEMENT_FORMAT = "SHIFT.SGBScenePlacement/1"
CAPTURE_FORMAT = "SHIFT.IMBRuntimeCapturePipeline/1"


def _row_key(row: Mapping[str, Any]) -> tuple[str, Any, tuple[int, ...]]:
    wrapper = row.get("wrapper")
    wrapper = wrapper if isinstance(wrapper, Mapping) else {}
    path = row.get("object_path")
    path = path if isinstance(path, list) else []
    return (
        str(wrapper.get("chunk") or ""),
        wrapper.get("source_record_index"),
        tuple(int(value) for value in path),
    )


def _handoff_index(
    report: Mapping[str, Any],
) -> dict[tuple[str, Any, tuple[int, ...]], Mapping[str, Any]]:
    rows: dict[
        tuple[str, Any, tuple[int, ...]],
        Mapping[str, Any],
    ] = {}
    for row in report.get("objects") or []:
        if not isinstance(row, Mapping):
            continue
        try:
            key = _row_key(row)
        except (TypeError, ValueError):
            continue
        rows[key] = row
    return rows


def _transform(row: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not isinstance(row, Mapping):
        return {}
    handoff = row.get("handoff")
    handoff = handoff if isinstance(handoff, Mapping) else {}
    value = handoff.get("transform")
    return value if isinstance(value, Mapping) else {}


def _resource_reference(row: Mapping[str, Any] | None) -> Any:
    if not isinstance(row, Mapping):
        return None
    handoff = row.get("handoff")
    handoff = handoff if isinstance(handoff, Mapping) else {}
    resource = handoff.get("resource")
    resource = resource if isinstance(resource, Mapping) else {}
    return resource.get("reference")


def _consensus_provenance(
    transform: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    evaluation = transform.get("multimatrix_evaluation")
    if not isinstance(evaluation, Mapping):
        return None
    root_state = evaluation.get("root_transform_state")
    if not isinstance(root_state, Mapping):
        return None
    if (
        root_state.get("current_root_source")
        != "phase596-runtime-root-consensus"
    ):
        return None
    value = root_state.get("runtime_root_consensus")
    return value if isinstance(value, Mapping) else None


def _compare_handoffs(
    baseline: Mapping[str, Any],
    recovered: Mapping[str, Any],
) -> dict[str, Any]:
    before = _handoff_index(baseline)
    after = _handoff_index(recovered)
    keys = sorted(
        set(before) | set(after),
        key=lambda value: (
            value[0],
            str(value[1]),
            value[2],
        ),
    )

    rows: list[dict[str, Any]] = []
    recovered_rows: list[dict[str, Any]] = []
    still_blocked: list[dict[str, Any]] = []
    parent_slot_count = 0
    parent_slot_ready_before = 0
    parent_slot_ready_after = 0

    for key in keys:
        before_row = before.get(key)
        after_row = after.get(key)
        before_transform = _transform(before_row)
        after_transform = _transform(after_row)
        mode = (
            after_transform.get("mode")
            or before_transform.get("mode")
        )
        before_ready = (
            before_transform.get("world_matrix_ready") is True
        )
        after_ready = (
            after_transform.get("world_matrix_ready") is True
        )
        if mode == "parent-multimatrix-slot":
            parent_slot_count += 1
            if before_ready:
                parent_slot_ready_before += 1
            if after_ready:
                parent_slot_ready_after += 1

        provenance = _consensus_provenance(after_transform)
        row = {
            "wrapper": {
                "chunk": key[0],
                "source_record_index": key[1],
            },
            "object_path": list(key[2]),
            "resource_reference": (
                _resource_reference(after_row)
                or _resource_reference(before_row)
            ),
            "transform_mode": mode,
            "matrix_number": (
                after_transform.get("matrix_number")
                if after_transform
                else before_transform.get("matrix_number")
            ),
            "numeric_world_ready_before": before_ready,
            "numeric_world_ready_after": after_ready,
            "recovered_by_runtime_root_consensus": (
                not before_ready
                and after_ready
                and provenance is not None
            ),
            "world_matrix_after": (
                after_transform.get("world_matrix")
                if after_ready
                else None
            ),
            "runtime_root_consensus": (
                dict(provenance)
                if provenance is not None
                else None
            ),
        }
        rows.append(row)
        if row["recovered_by_runtime_root_consensus"]:
            recovered_rows.append(row)
        if (
            mode == "parent-multimatrix-slot"
            and not after_ready
        ):
            still_blocked.append(row)

    return {
        "object_count": len(rows),
        "parent_multimatrix_slot_count": parent_slot_count,
        "parent_multimatrix_numeric_ready_before": (
            parent_slot_ready_before
        ),
        "parent_multimatrix_numeric_ready_after": (
            parent_slot_ready_after
        ),
        "recovered_matrixnumber_object_count": len(recovered_rows),
        "remaining_blocked_matrixnumber_object_count": len(still_blocked),
        "transform_recovery_complete": (
            parent_slot_count > 0
            and parent_slot_ready_after == parent_slot_count
        ),
        "objects": rows,
        "recovered_objects": recovered_rows,
        "remaining_blocked_objects": still_blocked,
    }


def _manifest_rows(
    ir_manifest: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if isinstance(ir_manifest, (str, bytes, bytearray)):
        raise ValueError("IR manifest must be a JSON array")
    return [
        dict(row)
        for row in ir_manifest
        if isinstance(row, Mapping)
    ]


def build_sgb_runtime_transform_recovery_pipeline(
    sgb_runtime: Mapping[str, Any],
    scene_placement: Mapping[str, Any],
    capture_pipeline: Mapping[str, Any],
    ir_manifest: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if sgb_runtime.get("format") != SGB_FORMAT:
        raise ValueError("SGB input must be SHIFT.SGBRuntime/1")
    if scene_placement.get("format") != PLACEMENT_FORMAT:
        raise ValueError(
            "placement input must be SHIFT.SGBScenePlacement/1"
        )
    if capture_pipeline.get("format") != CAPTURE_FORMAT:
        raise ValueError(
            "capture input must be SHIFT.IMBRuntimeCapturePipeline/1"
        )

    manifest = _manifest_rows(ir_manifest)
    baseline_handoffs = build_sgb_object_render_handoff_set(
        sgb_runtime
    )
    baseline_admission = build_sgb_render_binding_admission(
        scene_placement,
        baseline_handoffs,
    )

    candidate_join = build_runtime_object_candidate_join(
        scene_placement,
        baseline_handoffs,
        capture_pipeline,
        manifest,
    )

    consensus = build_multimatrix_root_consensus(
        sgb_runtime,
        candidate_join,
        capture_pipeline,
    )

    consensus_applied = consensus.get("ready") is True
    recovered_handoffs = build_sgb_object_render_handoff_set(
        sgb_runtime,
        root_consensus=consensus if consensus_applied else None,
    )
    recovered_admission = build_sgb_render_binding_admission(
        scene_placement,
        recovered_handoffs,
    )

    comparison = _compare_handoffs(
        baseline_handoffs,
        recovered_handoffs,
    )

    blockers: list[str] = []
    if baseline_handoffs.get("ready") is not True:
        blockers.extend(
            "baseline-handoff:" + str(reason)
            for reason in (
                baseline_handoffs.get("blocking_reasons") or []
            )
        )
    if candidate_join.get("ready") is not True:
        blockers.extend(
            "candidate-join:" + str(reason)
            for reason in (
                candidate_join.get("blocking_reasons") or []
            )
        )
    if capture_pipeline.get("pipeline_ready") is not True:
        blockers.extend(
            "capture-pipeline:" + str(reason)
            for reason in (
                capture_pipeline.get("blocking_reasons") or []
            )
        )
    if (
        consensus_applied
        and recovered_handoffs.get("ready") is not True
    ):
        blockers.extend(
            "recovered-handoff:" + str(reason)
            for reason in (
                recovered_handoffs.get("blocking_reasons") or []
            )
        )

    blockers = list(dict.fromkeys(blockers))
    pipeline_ready = not blockers
    recovered_count = comparison[
        "recovered_matrixnumber_object_count"
    ]
    admitted_before = int(
        baseline_admission.get("admitted_binding_count") or 0
    )
    admitted_after = int(
        recovered_admission.get("admitted_binding_count") or 0
    )

    if not pipeline_ready:
        status = "blocked"
    elif recovered_count > 0:
        status = "recovered"
    elif consensus.get("ready") is True:
        status = "no-delta"
    else:
        status = "no-consensus"

    return {
        "format": FORMAT,
        "version": 1,
        "status": status,
        "pipeline_ready": pipeline_ready,
        "blocking_reasons": blockers,
        "consensus_applied": consensus_applied,
        "transform_recovery_complete": comparison[
            "transform_recovery_complete"
        ],
        "scene_admission_ready": (
            recovered_admission.get("ready") is True
        ),
        "summary": {
            "object_count": comparison["object_count"],
            "parent_multimatrix_slot_count": comparison[
                "parent_multimatrix_slot_count"
            ],
            "parent_multimatrix_numeric_ready_before": comparison[
                "parent_multimatrix_numeric_ready_before"
            ],
            "parent_multimatrix_numeric_ready_after": comparison[
                "parent_multimatrix_numeric_ready_after"
            ],
            "recovered_matrixnumber_object_count": recovered_count,
            "remaining_blocked_matrixnumber_object_count": comparison[
                "remaining_blocked_matrixnumber_object_count"
            ],
            "root_consensus_ready_count": int(
                consensus.get("ready_consensus_count") or 0
            ),
            "root_consensus_ambiguous_count": int(
                consensus.get("ambiguous_consensus_count") or 0
            ),
            "admitted_binding_count_before": admitted_before,
            "admitted_binding_count_after": admitted_after,
            "admitted_binding_delta": (
                admitted_after - admitted_before
            ),
        },
        "baseline": {
            "object_handoffs": baseline_handoffs,
            "render_binding_admission": baseline_admission,
        },
        "runtime_candidate_join": candidate_join,
        "root_consensus": consensus,
        "recovered": {
            "object_handoffs": recovered_handoffs,
            "render_binding_admission": recovered_admission,
        },
        "comparison": comparison,
        "boundary": {
            "phase595_candidate_join_reused": True,
            "phase596_owner_root_consensus_reused": True,
            "phase597_handoff_application_reused": True,
            "existing_scene_admission_reused": True,
            "new_transform_math": False,
            "register_semantics_assigned": False,
            "scenegraph_update_history_recovered": False,
            "render_admission_only_via_existing_gate": True,
            "authentic_capture_required_for_production_recovery": True,
        },
    }


def validate_files(
    sgb_runtime_path: str | Path,
    scene_placement_path: str | Path,
    capture_pipeline_path: str | Path,
    ir_root: str | Path,
) -> dict[str, Any]:
    sgb_runtime = json.loads(
        Path(sgb_runtime_path).read_text(encoding="utf-8")
    )
    scene_placement = json.loads(
        Path(scene_placement_path).read_text(encoding="utf-8")
    )
    capture_pipeline = json.loads(
        Path(capture_pipeline_path).read_text(encoding="utf-8")
    )
    manifest = json.loads(
        (Path(ir_root) / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    if not isinstance(sgb_runtime, Mapping):
        raise ValueError("SGB runtime JSON must be an object")
    if not isinstance(scene_placement, Mapping):
        raise ValueError("scene placement JSON must be an object")
    if not isinstance(capture_pipeline, Mapping):
        raise ValueError("capture pipeline JSON must be an object")
    if not isinstance(manifest, list):
        raise ValueError("IR manifest must be a JSON array")
    return build_sgb_runtime_transform_recovery_pipeline(
        sgb_runtime,
        scene_placement,
        capture_pipeline,
        manifest,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sgb_runtime")
    parser.add_argument("scene_placement")
    parser.add_argument("capture_pipeline")
    parser.add_argument("ir_root")
    parser.add_argument("output")
    args = parser.parse_args(argv)

    report = validate_files(
        args.sgb_runtime,
        args.scene_placement,
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
        "pipeline_ready": report["pipeline_ready"],
        "consensus_applied": report["consensus_applied"],
        "transform_recovery_complete": report[
            "transform_recovery_complete"
        ],
        "scene_admission_ready": report[
            "scene_admission_ready"
        ],
        "summary": report["summary"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["pipeline_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
