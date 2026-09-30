"""Measure Phase 595-597 MatrixNumber coverage on runtime capture evidence.

This module orchestrates the existing evidence gates without introducing a new
transform inference path:

SGB placement + baseline OBJECT handoffs + runtime capture + IR manifest
  -> Phase 595 runtime-object candidate join
  -> Phase 596 owner-scoped MultiMatrix root consensus
  -> Phase 597 root application through the existing handoff evaluator
  -> ordinary SHIFT.SGBRenderBindingAdmission/1

The report measures current-state coverage only. Historical SceneGraph update
ordering remains explicitly unresolved.
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

FORMAT = "SHIFT.SGBMultiMatrixRuntimeCoverage/1"


def _object_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    wrapper = row.get("wrapper")
    wrapper = wrapper if isinstance(wrapper, Mapping) else {}
    handoff = row.get("handoff")
    handoff = handoff if isinstance(handoff, Mapping) else {}
    resource = handoff.get("resource")
    resource = resource if isinstance(resource, Mapping) else {}
    return (
        wrapper.get("chunk"),
        wrapper.get("source_record_index"),
        tuple(row.get("object_path") or []),
        str(resource.get("reference") or ""),
    )


def _matrix_rows(
    handoffs: Mapping[str, Any],
) -> dict[tuple[Any, ...], dict[str, Any]]:
    result: dict[tuple[Any, ...], dict[str, Any]] = {}
    for index, row in enumerate(handoffs.get("objects") or []):
        if not isinstance(row, Mapping):
            continue
        handoff = row.get("handoff")
        handoff = handoff if isinstance(handoff, Mapping) else {}
        transform = handoff.get("transform")
        transform = transform if isinstance(transform, Mapping) else {}
        if transform.get("mode") != "parent-multimatrix-slot":
            continue
        evaluation = transform.get("multimatrix_evaluation")
        evaluation = (
            evaluation if isinstance(evaluation, Mapping) else {}
        )
        root_state = evaluation.get("root_transform_state")
        root_state = root_state if isinstance(root_state, Mapping) else {}
        key = _object_key(row)
        result[key] = {
            "object_index": index,
            "wrapper": {
                "chunk": key[0],
                "source_record_index": key[1],
            },
            "object_path": list(key[2]),
            "owner_path": list(key[2][:-1]),
            "resource_reference": key[3] or None,
            "matrix_number": transform.get("matrix_number"),
            "world_matrix_ready": (
                transform.get("world_matrix_ready") is True
            ),
            "world_matrix": transform.get("world_matrix"),
            "current_root_source": root_state.get(
                "current_root_source"
            ),
            "runtime_root_consensus": root_state.get(
                "runtime_root_consensus"
            ),
        }
    return result


def _binding_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    placement = row.get("placement")
    placement = placement if isinstance(placement, Mapping) else {}
    obj = row.get("object")
    obj = obj if isinstance(obj, Mapping) else {}
    return (
        placement.get("wrapper_chunk"),
        placement.get("source_record_index"),
        tuple(obj.get("object_path") or []),
        str(obj.get("resource_reference") or ""),
    )


def _ready_binding_map(
    admission: Mapping[str, Any],
) -> dict[tuple[Any, ...], bool]:
    result: dict[tuple[Any, ...], bool] = {}
    for row in admission.get("bindings") or []:
        if not isinstance(row, Mapping):
            continue
        result[_binding_key(row)] = row.get("ready") is True
    return result


def _ready_consensus_keys(
    consensus: Mapping[str, Any],
) -> set[tuple[str, Any, tuple[int, ...]]]:
    result: set[tuple[str, Any, tuple[int, ...]]] = set()
    for row in consensus.get("consensus") or []:
        if (
            not isinstance(row, Mapping)
            or row.get("ready") is not True
            or row.get(
                "authorizes_current_multimatrix_owner_root"
            ) is not True
        ):
            continue
        wrapper = row.get("wrapper")
        wrapper = wrapper if isinstance(wrapper, Mapping) else {}
        owner_path = row.get("owner_path")
        if not isinstance(owner_path, list):
            continue
        result.add((
            str(wrapper.get("chunk") or ""),
            wrapper.get("source_record_index"),
            tuple(int(value) for value in owner_path),
        ))
    return result


def build_multimatrix_runtime_coverage(
    scene_placement: Mapping[str, Any],
    sgb_runtime: Mapping[str, Any],
    capture_pipeline: Mapping[str, Any],
    ir_manifest: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    baseline_handoffs = build_sgb_object_render_handoff_set(
        sgb_runtime
    )
    candidate_join = build_runtime_object_candidate_join(
        scene_placement,
        baseline_handoffs,
        capture_pipeline,
        ir_manifest,
    )
    consensus = build_multimatrix_root_consensus(
        sgb_runtime,
        candidate_join,
        capture_pipeline,
    )

    if consensus.get("ready") is True:
        promoted_handoffs = build_sgb_object_render_handoff_set(
            sgb_runtime,
            root_consensus=consensus,
        )
    else:
        promoted_handoffs = baseline_handoffs

    baseline_admission = build_sgb_render_binding_admission(
        scene_placement,
        baseline_handoffs,
    )
    promoted_admission = build_sgb_render_binding_admission(
        scene_placement,
        promoted_handoffs,
    )

    baseline_matrix = _matrix_rows(baseline_handoffs)
    promoted_matrix = _matrix_rows(promoted_handoffs)
    ready_consensus_keys = _ready_consensus_keys(consensus)

    resolved_rows: list[dict[str, Any]] = []
    unresolved_rows: list[dict[str, Any]] = []
    already_ready_rows: list[dict[str, Any]] = []

    for key, after in promoted_matrix.items():
        before = baseline_matrix.get(key) or {}
        before_ready = before.get("world_matrix_ready") is True
        after_ready = after.get("world_matrix_ready") is True
        owner_key = (
            str(after["wrapper"]["chunk"] or ""),
            after["wrapper"]["source_record_index"],
            tuple(after.get("owner_path") or []),
        )
        row = {
            **after,
            "baseline_world_matrix_ready": before_ready,
            "consensus_owner_ready": owner_key
            in ready_consensus_keys,
        }
        if before_ready:
            already_ready_rows.append(row)
        elif after_ready:
            resolved_rows.append(row)
        else:
            unresolved_rows.append(row)

    baseline_bindings = _ready_binding_map(baseline_admission)
    promoted_bindings = _ready_binding_map(promoted_admission)
    newly_admitted = [
        {
            "wrapper": {
                "chunk": key[0],
                "source_record_index": key[1],
            },
            "object_path": list(key[2]),
            "resource_reference": key[3] or None,
        }
        for key, ready_after in promoted_bindings.items()
        if ready_after
        and baseline_bindings.get(key) is not True
    ]

    audit_blockers: list[str] = []
    if capture_pipeline.get("pipeline_ready") is not True:
        audit_blockers.append(
            "multimatrix-coverage:capture-pipeline-not-ready"
        )
    if candidate_join.get("ready") is not True:
        audit_blockers.extend(
            str(reason)
            for reason in candidate_join.get("blocking_reasons") or [
                "multimatrix-coverage:candidate-join-not-ready"
            ]
        )
    audit_blockers = list(dict.fromkeys(audit_blockers))
    ready = not audit_blockers

    consensus_rows = [
        row
        for row in consensus.get("consensus") or []
        if isinstance(row, Mapping)
    ]
    ready_consensus_count = sum(
        row.get("ready") is True
        and row.get(
            "authorizes_current_multimatrix_owner_root"
        ) is True
        for row in consensus_rows
    )
    ambiguous_consensus_count = sum(
        row.get("ready") is not True
        for row in consensus_rows
    )

    return {
        "format": FORMAT,
        "version": 1,
        "status": "measured" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": audit_blockers,
        "coverage": {
            "runtime_resource_count": candidate_join.get(
                "runtime_resource_count",
                0,
            ),
            "matched_runtime_resource_count": candidate_join.get(
                "matched_runtime_resource_count",
                0,
            ),
            "unique_candidate_resource_count": candidate_join.get(
                "unique_candidate_resource_count",
                0,
            ),
            "matrix_object_count": len(promoted_matrix),
            "baseline_numeric_matrix_object_count": sum(
                row.get("world_matrix_ready") is True
                for row in baseline_matrix.values()
            ),
            "ready_consensus_owner_count": ready_consensus_count,
            "ambiguous_consensus_owner_count": (
                ambiguous_consensus_count
            ),
            "consensus_hypothesis_count": consensus.get(
                "hypothesis_count",
                0,
            ),
            "consensus_eligible_root_count": consensus.get(
                "eligible_root_count",
                0,
            ),
            "consensus_resolved_matrix_object_count": len(
                resolved_rows
            ),
            "remaining_unresolved_matrix_object_count": len(
                unresolved_rows
            ),
            "promoted_numeric_matrix_object_count": sum(
                row.get("world_matrix_ready") is True
                for row in promoted_matrix.values()
            ),
            "baseline_admitted_binding_count": baseline_admission.get(
                "admitted_binding_count",
                0,
            ),
            "promoted_admitted_binding_count": promoted_admission.get(
                "admitted_binding_count",
                0,
            ),
            "newly_admitted_binding_count": len(newly_admitted),
        },
        "resolved_matrix_objects": resolved_rows,
        "remaining_unresolved_matrix_objects": unresolved_rows,
        "already_numeric_matrix_objects": already_ready_rows,
        "newly_admitted_bindings": newly_admitted,
        "stages": {
            "candidate_join": {
                "format": candidate_join.get("format"),
                "status": candidate_join.get("status"),
                "ready": candidate_join.get("ready"),
                "identity_complete": candidate_join.get(
                    "identity_complete"
                ),
                "blocking_reasons": candidate_join.get(
                    "blocking_reasons"
                ),
            },
            "root_consensus": {
                "format": consensus.get("format"),
                "status": consensus.get("status"),
                "ready": consensus.get("ready"),
                "ready_consensus_count": consensus.get(
                    "ready_consensus_count",
                    0,
                ),
                "ambiguous_consensus_count": consensus.get(
                    "ambiguous_consensus_count",
                    0,
                ),
                "blocking_reasons": consensus.get(
                    "blocking_reasons"
                ),
            },
            "baseline_handoffs": {
                "format": baseline_handoffs.get("format"),
                "ready": baseline_handoffs.get("ready"),
                "numeric_world_matrix_ready_count": (
                    baseline_handoffs.get(
                        "numeric_world_matrix_ready_count",
                        0,
                    )
                ),
            },
            "promoted_handoffs": {
                "format": promoted_handoffs.get("format"),
                "ready": promoted_handoffs.get("ready"),
                "runtime_root_consensus_applied_object_count": (
                    promoted_handoffs.get(
                        "runtime_root_consensus_applied_object_count",
                        0,
                    )
                ),
                "numeric_world_matrix_ready_count": (
                    promoted_handoffs.get(
                        "numeric_world_matrix_ready_count",
                        0,
                    )
                ),
            },
            "baseline_scene_admission": {
                "format": baseline_admission.get("format"),
                "ready": baseline_admission.get("ready"),
                "admitted_binding_count": baseline_admission.get(
                    "admitted_binding_count",
                    0,
                ),
                "blocked_binding_count": baseline_admission.get(
                    "blocked_binding_count",
                    0,
                ),
            },
            "promoted_scene_admission": {
                "format": promoted_admission.get("format"),
                "ready": promoted_admission.get("ready"),
                "admitted_binding_count": promoted_admission.get(
                    "admitted_binding_count",
                    0,
                ),
                "blocked_binding_count": promoted_admission.get(
                    "blocked_binding_count",
                    0,
                ),
            },
        },
        "boundary": {
            "new_transform_inference": False,
            "phase595_candidate_join_reused": True,
            "phase596_owner_consensus_reused": True,
            "phase597_handoff_application_reused": True,
            "ordinary_scene_admission_reused": True,
            "scenegraph_update_history_recovered": False,
            "world_register_semantics_assigned": False,
            "production_capture_required_for_real_counts": True,
        },
    }


def validate_files(
    scene_placement_path: str | Path,
    sgb_runtime_path: str | Path,
    capture_pipeline_path: str | Path,
    ir_root: str | Path,
) -> dict[str, Any]:
    placement = json.loads(
        Path(scene_placement_path).read_text(encoding="utf-8")
    )
    sgb = json.loads(
        Path(sgb_runtime_path).read_text(encoding="utf-8")
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
        raise ValueError("scene placement JSON must be an object")
    if not isinstance(sgb, Mapping):
        raise ValueError("SGB runtime JSON must be an object")
    if not isinstance(capture, Mapping):
        raise ValueError("capture pipeline JSON must be an object")
    if not isinstance(manifest, list):
        raise ValueError("IR manifest JSON must be an array")
    return build_multimatrix_runtime_coverage(
        placement,
        sgb,
        capture,
        manifest,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene_placement")
    parser.add_argument("sgb_runtime")
    parser.add_argument("capture_pipeline")
    parser.add_argument("ir_root")
    parser.add_argument("output")
    args = parser.parse_args(argv)

    report = validate_files(
        args.scene_placement,
        args.sgb_runtime,
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
        "coverage": report["coverage"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
