"""Promote Phase 596 wrapper-root consensus into SGB OBJECT handoffs.

This adapter consumes only ready wrapper-scoped roots authorized by
SHIFT.SGBMultiMatrixRootConsensus/1, re-evaluates OBJECT MatrixNumber paths
through the existing MultiMatrix evaluator, and emits the ordinary
SHIFT.SGBObjectRenderHandoffSet/1 contract expected by scene admission.

It does not recover or synthesize historical SceneGraph update events.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Mapping

from sgb_object_render_handoff import (
    FORMAT as HANDOFF_FORMAT,
    SGB_FORMAT,
    build_sgb_object_render_handoff_set,
)

CONSENSUS_FORMAT = "SHIFT.SGBMultiMatrixRootConsensus/1"


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _matrix16(value: Any) -> list[float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 16:
        return None
    try:
        result = [float(item) for item in value]
    except (TypeError, ValueError):
        return None
    if not all(math.isfinite(item) for item in result):
        return None
    return result


def _sgb_wrapper_keys(
    sgb_runtime: Mapping[str, Any],
) -> set[tuple[str, int]]:
    result: set[tuple[str, int]] = set()
    for chunk in sgb_runtime.get("chunks") or []:
        if (
            not isinstance(chunk, Mapping)
            or chunk.get("tag") not in {"NODE", "SUMM"}
        ):
            continue
        tag = str(chunk.get("tag"))
        for record in chunk.get("records") or []:
            if not isinstance(record, Mapping):
                continue
            index = _safe_int(record.get("index"))
            if index is not None:
                result.add((tag, index))
    return result


def _ready_roots(
    sgb_runtime: Mapping[str, Any],
    root_consensus: Mapping[str, Any],
) -> tuple[
    dict[tuple[str, int], list[float]],
    dict[tuple[str, int], dict[str, Any]],
]:
    if root_consensus.get("format") != CONSENSUS_FORMAT:
        raise ValueError(
            "consensus input must be SHIFT.SGBMultiMatrixRootConsensus/1"
        )
    if root_consensus.get("ready") is not True:
        raise ValueError("root consensus must be ready")

    boundary = root_consensus.get("boundary") or {}
    if not isinstance(boundary, Mapping):
        raise ValueError("root consensus boundary is missing")
    if boundary.get("authorizes_current_wrapper_root_only") is not True:
        raise ValueError(
            "root consensus does not authorize current wrapper roots"
        )
    if boundary.get("scenegraph_update_history_recovered") is not False:
        raise ValueError(
            "root consensus must not claim SceneGraph update history"
        )
    if boundary.get("authorizes_render_admission") is not False:
        raise ValueError(
            "root consensus must not directly authorize render admission"
        )

    known_wrappers = _sgb_wrapper_keys(sgb_runtime)
    roots: dict[tuple[str, int], list[float]] = {}
    provenance: dict[tuple[str, int], dict[str, Any]] = {}

    for row in root_consensus.get("consensus") or []:
        if not isinstance(row, Mapping) or row.get("ready") is not True:
            continue
        if row.get("authorizes_current_wrapper_root") is not True:
            continue

        wrapper = row.get("wrapper") or {}
        if not isinstance(wrapper, Mapping):
            raise ValueError("ready consensus row has no wrapper")
        chunk = str(wrapper.get("chunk") or "")
        source_index = _safe_int(wrapper.get("source_record_index"))
        if chunk not in {"NODE", "SUMM"} or source_index is None:
            raise ValueError("ready consensus row has invalid wrapper identity")

        key = (chunk, source_index)
        if key not in known_wrappers:
            raise ValueError(
                "ready consensus wrapper is absent from SGB runtime: "
                f"{chunk}:{source_index}"
            )
        if key in roots:
            raise ValueError(
                "multiple ready consensus roots for wrapper: "
                f"{chunk}:{source_index}"
            )

        root = _matrix16(row.get("root_world_matrix"))
        if root is None:
            raise ValueError(
                "ready consensus row has invalid root matrix: "
                f"{chunk}:{source_index}"
            )
        roots[key] = root
        provenance[key] = {
            "format": CONSENSUS_FORMAT,
            "wrapper": {
                "chunk": chunk,
                "source_record_index": source_index,
            },
            "root_float32_hex": row.get("root_float32_hex"),
            "support_resource_count": row.get(
                "support_resource_count"
            ),
            "distinct_cumulative_local_count": row.get(
                "distinct_cumulative_local_count"
            ),
            "witness_count": row.get("witness_count"),
            "authorizes_current_wrapper_root": True,
            "scenegraph_update_history_recovered": False,
            "authorizes_render_admission": False,
        }

    if not roots:
        raise ValueError("root consensus contains no ready wrapper roots")
    return roots, provenance


def build_root_promoted_object_handoffs(
    sgb_runtime: Mapping[str, Any],
    root_consensus: Mapping[str, Any],
) -> dict[str, Any]:
    if sgb_runtime.get("format") != SGB_FORMAT:
        raise ValueError("SGB input must be SHIFT.SGBRuntime/1")

    roots, provenance = _ready_roots(
        sgb_runtime,
        root_consensus,
    )

    baseline = build_sgb_object_render_handoff_set(sgb_runtime)
    promoted = build_sgb_object_render_handoff_set(
        sgb_runtime,
        wrapper_root_matrices=roots,
        wrapper_root_provenance=provenance,
    )

    baseline_rows = baseline.get("objects") or []
    promoted_rows = promoted.get("objects") or []
    if len(baseline_rows) != len(promoted_rows):
        raise ValueError("root promotion changed OBJECT row count")

    promoted_indices: list[int] = []
    still_blocked_indices: list[int] = []
    root_applied_indices: list[int] = []
    for index, (before, after) in enumerate(
        zip(baseline_rows, promoted_rows)
    ):
        if not isinstance(before, Mapping) or not isinstance(after, Mapping):
            continue
        before_handoff = before.get("handoff") or {}
        after_handoff = after.get("handoff") or {}
        before_transform = (
            before_handoff.get("transform")
            if isinstance(before_handoff, Mapping)
            else {}
        ) or {}
        after_transform = (
            after_handoff.get("transform")
            if isinstance(after_handoff, Mapping)
            else {}
        ) or {}

        if after.get("runtime_wrapper_root") is not None:
            root_applied_indices.append(index)

        matrix_slot = (
            after_transform.get("mode")
            == "parent-multimatrix-slot"
        )
        before_ready = before_transform.get(
            "world_matrix_ready"
        ) is True
        after_ready = after_transform.get(
            "world_matrix_ready"
        ) is True
        if matrix_slot and not before_ready and after_ready:
            promoted_indices.append(index)
        elif matrix_slot and not after_ready:
            still_blocked_indices.append(index)

    promotion = {
        "format": "SHIFT.SGBMultiMatrixRootPromotion/1",
        "version": 1,
        "status": "ready",
        "ready": True,
        "blocking_reasons": [],
        "consensus_format": CONSENSUS_FORMAT,
        "wrapper_root_count": len(roots),
        "root_applied_object_count": len(root_applied_indices),
        "promoted_matrix_object_count": len(promoted_indices),
        "remaining_unresolved_matrix_object_count": len(
            still_blocked_indices
        ),
        "root_applied_object_indices": root_applied_indices,
        "promoted_object_indices": promoted_indices,
        "remaining_unresolved_object_indices": still_blocked_indices,
        "boundary": {
            "wrapper_scoped_roots_only": True,
            "existing_multimatrix_evaluator_reused": True,
            "scenegraph_update_history_recovered": False,
            "direct_render_admission_authorized": False,
            "downstream_contract": HANDOFF_FORMAT,
        },
    }

    promoted["runtime_root_promotion"] = promotion
    promoted["boundary"] = {
        **dict(promoted.get("boundary") or {}),
        "runtime_wrapper_root_promotion": promotion["format"],
        "runtime_wrapper_root_consensus": CONSENSUS_FORMAT,
        "root_promotion_recovers_scenegraph_history": False,
    }
    return promoted


def validate_files(
    sgb_runtime_path: str | Path,
    root_consensus_path: str | Path,
) -> dict[str, Any]:
    sgb = json.loads(
        Path(sgb_runtime_path).read_text(encoding="utf-8")
    )
    consensus = json.loads(
        Path(root_consensus_path).read_text(encoding="utf-8")
    )
    if not isinstance(sgb, Mapping):
        raise ValueError("SGB runtime JSON must be an object")
    if not isinstance(consensus, Mapping):
        raise ValueError("root consensus JSON must be an object")
    return build_root_promoted_object_handoffs(
        sgb,
        consensus,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sgb_runtime")
    parser.add_argument("root_consensus")
    parser.add_argument("output")
    args = parser.parse_args(argv)

    report = validate_files(
        args.sgb_runtime,
        args.root_consensus,
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
    promotion = report["runtime_root_promotion"]
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "wrapper_root_count": promotion["wrapper_root_count"],
        "promoted_matrix_object_count": promotion[
            "promoted_matrix_object_count"
        ],
        "remaining_unresolved_matrix_object_count": promotion[
            "remaining_unresolved_matrix_object_count"
        ],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
