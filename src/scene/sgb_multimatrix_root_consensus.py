"""Build a pre-admission MultiMatrix root consensus from runtime VS constants.

Phase 596 combines the Phase 595 runtime-resource -> SGB candidate narrowing
with the Phase 594 inverse MultiMatrix root solve. No world-register semantic is
assigned. Every contiguous four-register VS constant window is treated as an
observation candidate in row-major and transpose layouts.

A wrapper root is promoted only when the same exact float32 root is independently
recovered from at least two exact runtime resources and at least two distinct
cumulative local transforms. The existing MultiMatrix evaluator remains the
acceptance oracle inside each Phase 594 solve.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import struct
from pathlib import Path
from typing import Any, Mapping

from sgb_multimatrix import build_multimatrix_root_solve

FORMAT = "SHIFT.SGBMultiMatrixRootConsensus/1"
SGB_FORMAT = "SHIFT.SGBRuntime/1"
CANDIDATE_FORMAT = "SHIFT.SGBRuntimeObjectCandidateJoin/1"
CAPTURE_FORMAT = "SHIFT.IMBRuntimeCapturePipeline/1"


def _norm_ref(value: Any) -> str:
    return re.sub(
        r"/+",
        "/",
        str(value or "").replace("\\", "/"),
    ).lower().lstrip("./")


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
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _matrix16(value: Any) -> list[float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 16:
        return None
    try:
        out = [float(item) for item in value]
    except (TypeError, ValueError):
        return None
    return out if all(math.isfinite(item) for item in out) else None


def _f32_hex(values: list[float]) -> str:
    return struct.pack("<16f", *values).hex()


def _transpose(values: list[float]) -> list[float]:
    return [
        values[row + column * 4]
        for row in range(4)
        for column in range(4)
    ]


def _vertex_constant_windows(
    constant_state: Mapping[str, Any],
) -> list[dict[str, Any]]:
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
                isinstance(value, (int, float))
                for value in raw_values
            )
        ):
            continue
        values = [float(value) for value in raw_values]
        if not all(math.isfinite(value) for value in values):
            continue
        registers[register] = values

    rows: list[dict[str, Any]] = []
    for start in sorted(registers):
        if not all(
            start + offset in registers for offset in range(4)
        ):
            continue
        values = [
            value
            for offset in range(4)
            for value in registers[start + offset]
        ]
        rows.append({
            "start_register": start,
            "registers": [start + offset for offset in range(4)],
            "values": values,
        })
    return rows


def _kind(report: Mapping[str, Any]) -> str | None:
    value = report.get("kind")
    return (
        str(value.get("text"))
        if isinstance(value, Mapping) and value.get("text")
        else None
    )


def _wrapper_root_report(
    sgb_runtime: Mapping[str, Any],
    wrapper: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    chunk_tag = str(wrapper.get("chunk") or "")
    source_index = _safe_int(wrapper.get("source_record_index"))
    if chunk_tag not in {"NODE", "SUMM"} or source_index is None:
        return None

    for chunk in sgb_runtime.get("chunks") or []:
        if (
            not isinstance(chunk, Mapping)
            or chunk.get("tag") != chunk_tag
        ):
            continue
        for record in chunk.get("records") or []:
            if (
                not isinstance(record, Mapping)
                or _safe_int(record.get("index")) != source_index
            ):
                continue
            payload = record.get("object_payload")
            if not isinstance(payload, Mapping):
                return None
            report = payload.get("report")
            return report if isinstance(report, Mapping) else None
    return None


def _owner_for_object_path(
    root: Mapping[str, Any],
    object_path: Any,
) -> Mapping[str, Any] | None:
    if not isinstance(object_path, list) or not object_path:
        return None
    current: Mapping[str, Any] = root
    for depth, raw_index in enumerate(object_path):
        index = _safe_int(raw_index)
        refs = current.get("subobject_references")
        if (
            index is None
            or not isinstance(refs, list)
            or index < 0
            or index >= len(refs)
        ):
            return None
        row = refs[index]
        if not isinstance(row, Mapping):
            return None
        child = row.get("report")
        if not isinstance(child, Mapping):
            return None
        if depth == len(object_path) - 1:
            return current
        current = child
    return None


def _resource_identity(row: Mapping[str, Any]) -> tuple[str, str, str] | None:
    archive = str(row.get("archive") or "")
    path = _norm_ref(row.get("resource_path"))
    sha = _sha256(row.get("resource_sha256"))
    if not archive or not path or sha is None:
        return None
    return archive, path, sha


def _capture_resources(
    capture: Mapping[str, Any],
) -> dict[tuple[str, str, str], Mapping[str, Any]]:
    rows: dict[tuple[str, str, str], Mapping[str, Any]] = {}
    for row in capture.get("resource_results") or []:
        if not isinstance(row, Mapping):
            continue
        key = _resource_identity(row)
        if key is not None:
            rows[key] = row
    return rows


def _observation_rows(
    resource: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    return [
        row
        for row in (
            resource.get("attributed_texture_observations") or []
        )
        if isinstance(row, Mapping)
        and row.get("status") == "observed"
        and isinstance(row.get("constant_state"), Mapping)
    ]


def build_multimatrix_root_consensus(
    sgb_runtime: Mapping[str, Any],
    candidate_join: Mapping[str, Any],
    capture_pipeline: Mapping[str, Any],
) -> dict[str, Any]:
    if sgb_runtime.get("format") != SGB_FORMAT:
        raise ValueError("SGB input must be SHIFT.SGBRuntime/1")
    if candidate_join.get("format") != CANDIDATE_FORMAT:
        raise ValueError(
            "candidate input must be SHIFT.SGBRuntimeObjectCandidateJoin/1"
        )
    if capture_pipeline.get("format") != CAPTURE_FORMAT:
        raise ValueError(
            "capture input must be SHIFT.IMBRuntimeCapturePipeline/1"
        )

    blockers: list[str] = []
    if candidate_join.get("ready") is not True:
        blockers.append("root-consensus:candidate-join-not-ready")
    if capture_pipeline.get("pipeline_ready") is not True:
        blockers.append("root-consensus:capture-pipeline-not-ready")

    capture_by_identity = _capture_resources(capture_pipeline)
    hypotheses: list[dict[str, Any]] = []
    skipped_candidates: list[dict[str, Any]] = []

    for runtime_row in candidate_join.get("resources") or []:
        if not isinstance(runtime_row, Mapping):
            continue
        key = _resource_identity(runtime_row)
        if key is None:
            continue
        capture_resource = capture_by_identity.get(key)
        if capture_resource is None:
            blockers.append(
                "root-consensus:capture-resource-missing:"
                + "|".join(key)
            )
            continue

        observations = _observation_rows(capture_resource)
        if not observations:
            continue

        for candidate in runtime_row.get("scene_candidates") or []:
            if not isinstance(candidate, Mapping):
                continue
            matrix_number = _safe_int(candidate.get("matrix_number"))
            if (
                candidate.get("transform_mode")
                != "parent-multimatrix-slot"
                or matrix_number is None
                or matrix_number < 0
            ):
                continue

            wrapper = candidate.get("wrapper")
            wrapper = wrapper if isinstance(wrapper, Mapping) else {}
            root_report = _wrapper_root_report(
                sgb_runtime,
                wrapper,
            )
            owner = (
                _owner_for_object_path(
                    root_report,
                    candidate.get("object_path"),
                )
                if isinstance(root_report, Mapping)
                else None
            )
            if owner is None or _kind(owner) not in {"LOD", "HIERARCHY"}:
                skipped_candidates.append({
                    "runtime_resource_identity": {
                        "archive": key[0],
                        "resource_path": key[1],
                        "resource_sha256": key[2],
                    },
                    "scene_candidate_index": candidate.get(
                        "scene_candidate_index"
                    ),
                    "reason": "multimatrix-owner-not-resolved",
                })
                continue

            for observation in observations:
                constant_state = observation.get("constant_state")
                if not isinstance(constant_state, Mapping):
                    continue
                for window in _vertex_constant_windows(
                    constant_state
                ):
                    layouts = [
                        ("row-major", list(window["values"])),
                        (
                            "transpose",
                            _transpose(list(window["values"])),
                        ),
                    ]
                    for layout, observed_world in layouts:
                        solve = build_multimatrix_root_solve(
                            owner,
                            matrix_number,
                            observed_world,
                        )
                        if solve.get("ready") is not True:
                            continue
                        root = _matrix16(
                            solve.get("solved_root_world_matrix")
                        )
                        cumulative = _matrix16(
                            solve.get("cumulative_local_matrix")
                        )
                        if root is None or cumulative is None:
                            continue
                        hypotheses.append({
                            "wrapper": {
                                "chunk": wrapper.get("chunk"),
                                "source_record_index": wrapper.get(
                                    "source_record_index"
                                ),
                            },
                            "scene_candidate_index": candidate.get(
                                "scene_candidate_index"
                            ),
                            "placement_index": candidate.get(
                                "placement_index"
                            ),
                            "object_path": candidate.get("object_path"),
                            "matrix_number": matrix_number,
                            "runtime_resource_identity": {
                                "archive": key[0],
                                "resource_path": key[1],
                                "resource_sha256": key[2],
                            },
                            "frame": observation.get("frame"),
                            "draw_index": observation.get("draw_index"),
                            "start_register": window["start_register"],
                            "registers": list(window["registers"]),
                            "layout": layout,
                            "solved_root_world_matrix": root,
                            "root_float32_hex": _f32_hex(root),
                            "cumulative_local_float32_hex": (
                                _f32_hex(cumulative)
                            ),
                            "max_abs_reproduction_error": solve.get(
                                "max_abs_reproduction_error"
                            ),
                            "root_solve": {
                                "format": solve.get("format"),
                                "selected_slot_chain_to_root": solve.get(
                                    "selected_slot_chain_to_root"
                                ),
                                "boundary": solve.get("boundary"),
                            },
                        })

    groups: dict[tuple[str, Any, str], list[dict[str, Any]]] = {}
    for row in hypotheses:
        wrapper = row["wrapper"]
        key = (
            str(wrapper.get("chunk")),
            wrapper.get("source_record_index"),
            str(row["root_float32_hex"]),
        )
        groups.setdefault(key, []).append(row)

    eligible: list[dict[str, Any]] = []
    for key, rows in groups.items():
        resources = {
            (
                row["runtime_resource_identity"]["archive"],
                row["runtime_resource_identity"]["resource_path"],
                row["runtime_resource_identity"]["resource_sha256"],
            )
            for row in rows
        }
        local_shapes = {
            row["cumulative_local_float32_hex"]
            for row in rows
        }
        if len(resources) < 2 or len(local_shapes) < 2:
            continue
        eligible.append({
            "wrapper": {
                "chunk": key[0],
                "source_record_index": key[1],
            },
            "root_float32_hex": key[2],
            "root_world_matrix": rows[0][
                "solved_root_world_matrix"
            ],
            "support_resource_count": len(resources),
            "distinct_cumulative_local_count": len(local_shapes),
            "witness_count": len(rows),
            "support_resource_identities": [
                {
                    "archive": value[0],
                    "resource_path": value[1],
                    "resource_sha256": value[2],
                }
                for value in sorted(resources)
            ],
            "witnesses": rows,
        })

    eligible_by_wrapper: dict[tuple[str, Any], list[dict[str, Any]]] = {}
    for row in eligible:
        wrapper = row["wrapper"]
        eligible_by_wrapper.setdefault(
            (
                str(wrapper.get("chunk")),
                wrapper.get("source_record_index"),
            ),
            [],
        ).append(row)

    consensus_rows: list[dict[str, Any]] = []
    for wrapper_key, rows in sorted(
        eligible_by_wrapper.items(),
        key=lambda item: (item[0][0], str(item[0][1])),
    ):
        if len(rows) == 1:
            selected = rows[0]
            consensus_rows.append({
                **selected,
                "status": "ready",
                "ready": True,
                "blocking_reasons": [],
                "authorizes_current_wrapper_root": True,
            })
        else:
            consensus_rows.append({
                "wrapper": {
                    "chunk": wrapper_key[0],
                    "source_record_index": wrapper_key[1],
                },
                "status": "ambiguous",
                "ready": False,
                "blocking_reasons": [
                    "multiple-root-consensus-values:"
                    + str(len(rows))
                ],
                "authorizes_current_wrapper_root": False,
                "candidate_roots": rows,
            })

    ready_consensus = [
        row for row in consensus_rows if row.get("ready") is True
    ]
    ambiguous_consensus = [
        row for row in consensus_rows if row.get("ready") is not True
    ]

    blockers = list(dict.fromkeys(blockers))
    input_ready = not blockers
    ready = input_ready and bool(ready_consensus)

    return {
        "format": FORMAT,
        "version": 1,
        "status": (
            "ready"
            if ready
            else "ambiguous"
            if input_ready and ambiguous_consensus
            else "not-found"
            if input_ready
            else "blocked"
        ),
        "ready": ready,
        "blocking_reasons": blockers,
        "hypothesis_count": len(hypotheses),
        "eligible_root_count": len(eligible),
        "ready_consensus_count": len(ready_consensus),
        "ambiguous_consensus_count": len(ambiguous_consensus),
        "consensus": consensus_rows,
        "skipped_candidates": skipped_candidates,
        "boundary": {
            "runtime_constant_windows": (
                "all contiguous four-register strong-attributed VS windows"
            ),
            "accepted_layouts": ["row-major", "transpose"],
            "register_semantics_assigned": False,
            "root_identity": "exact IEEE-754 float32 root bytes",
            "minimum_independent_resources": 2,
            "minimum_distinct_cumulative_locals": 2,
            "phase594_round_trip_required": True,
            "authorizes_current_wrapper_root_only": True,
            "scenegraph_update_history_recovered": False,
            "authorizes_object_runtime_attribution": False,
            "authorizes_render_admission": False,
        },
    }


def validate_files(
    sgb_runtime_path: str | Path,
    candidate_join_path: str | Path,
    capture_pipeline_path: str | Path,
) -> dict[str, Any]:
    sgb = json.loads(
        Path(sgb_runtime_path).read_text(encoding="utf-8")
    )
    candidates = json.loads(
        Path(candidate_join_path).read_text(encoding="utf-8")
    )
    capture = json.loads(
        Path(capture_pipeline_path).read_text(encoding="utf-8")
    )
    if not isinstance(sgb, Mapping):
        raise ValueError("SGB runtime JSON must be an object")
    if not isinstance(candidates, Mapping):
        raise ValueError("candidate join JSON must be an object")
    if not isinstance(capture, Mapping):
        raise ValueError("capture pipeline JSON must be an object")
    return build_multimatrix_root_consensus(
        sgb,
        candidates,
        capture,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sgb_runtime")
    parser.add_argument("candidate_join")
    parser.add_argument("capture_pipeline")
    parser.add_argument("output")
    args = parser.parse_args(argv)

    report = validate_files(
        args.sgb_runtime,
        args.candidate_join,
        args.capture_pipeline,
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
        "hypothesis_count": report["hypothesis_count"],
        "eligible_root_count": report["eligible_root_count"],
        "ready_consensus_count": report[
            "ready_consensus_count"
        ],
        "ambiguous_consensus_count": report[
            "ambiguous_consensus_count"
        ],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
