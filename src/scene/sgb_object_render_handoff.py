"""Source-backed SGB OBJECT -> render-instance/transform handoff.

The retail OBJECT render vfunc at 0x00699230 consumes the resource descriptor
stored at wrapper +0x80 and chooses one of two transform paths:

* MatrixNumber >= 0: register/select a 0x40-byte MultiMatrix slot.
* MatrixNumber == -1: build a 4x4 matrix from wrapper quaternion/offset/scale.

This module records that boundary without pretending that a parent MultiMatrix
slot is already a numerically materialized world matrix.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from sgb_multimatrix import build_multimatrix_evaluation
from sgb_root_transform import build_root_transform_state

FORMAT = "SHIFT.SGBObjectRenderHandoffSet/1"
SGB_FORMAT = "SHIFT.SGBRuntime/1"
OBJECT_FORMAT = "SHIFT.SGBObjectRuntime/1"


def _kind(report: Mapping[str, Any]) -> str | None:
    value = report.get("kind") or {}
    return value.get("text") if isinstance(value, Mapping) else None


def _matrix_from_explicit(explicit: Mapping[str, Any]) -> list[float]:
    q = explicit.get("orientation_runtime_order")
    offset = explicit.get("offset_xyz")
    scale = explicit.get("scale")
    if (
        not isinstance(q, (list, tuple))
        or len(q) != 4
        or not isinstance(offset, (list, tuple))
        or len(offset) != 3
    ):
        raise ValueError("explicit OBJECT transform is incomplete")
    try:
        w, x, y, z = [float(value) for value in q]
        tx, ty, tz = [float(value) for value in offset]
        s = float(scale)
    except (TypeError, ValueError) as exc:
        raise ValueError("explicit OBJECT transform is non-numeric") from exc

    # Exact storage/order used by FUN_00445ec0(param_3=1), followed by
    # FUN_0068c560 scale and OBJECT translation writes in 0x00699230.
    matrix = [0.0] * 16
    matrix[0] = 1.0 - 2.0 * y * y - 2.0 * z * z
    matrix[5] = 1.0 - 2.0 * x * x - 2.0 * z * z
    matrix[10] = 1.0 - 2.0 * x * x - 2.0 * y * y
    matrix[1] = 2.0 * x * y + 2.0 * w * z
    matrix[4] = 2.0 * x * y - 2.0 * w * z
    matrix[2] = 2.0 * x * z - 2.0 * w * y
    matrix[8] = 2.0 * w * y + 2.0 * x * z
    matrix[6] = 2.0 * w * x + 2.0 * y * z
    matrix[9] = 2.0 * y * z - 2.0 * x * w
    matrix[15] = 1.0
    for index in (0, 1, 2, 4, 5, 6, 8, 9, 10):
        matrix[index] *= s
    matrix[12] = tx
    matrix[13] = ty
    matrix[14] = tz
    return matrix


def _matrix_record_summary(
    parent: Mapping[str, Any] | None,
    matrix_number: int,
) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(parent, Mapping):
        return None, "object-render:parent-matrix-context-missing"
    records = [
        row
        for row in (parent.get("matrix_records") or [])
        if isinstance(row, Mapping)
    ]
    if matrix_number < 0 or matrix_number >= len(records):
        return None, (
            "object-render:matrix-number-out-of-range:"
            f"{matrix_number}:count={len(records)}"
        )
    row = records[matrix_number]
    return {
        "index": matrix_number,
        "offset_xyz": row.get("offset_xyz"),
        "orientation_runtime_order": row.get(
            "orientation_runtime_order"
        ),
        "scale": row.get("scale"),
        "parent": row.get("parent"),
        "runtime_slot_stride": 0x40,
        "runtime_slot_offset": matrix_number * 0x40,
    }, None


def build_object_render_handoff(
    object_report: Mapping[str, Any],
    *,
    parent_object_report: Mapping[str, Any] | None = None,
    parent_multimatrix_root_matrix: Sequence[float] | None = None,
    parent_scenegraph_updates: Sequence[Sequence[float]] | None = None,
) -> dict[str, Any]:
    if object_report.get("format") != OBJECT_FORMAT:
        raise ValueError("object input must be SHIFT.SGBObjectRuntime/1")
    if _kind(object_report) != "OBJECT":
        raise ValueError("render handoff currently accepts OBJECT payloads only")

    blockers: list[str] = []
    resource = object_report.get("resource_filename") or {}
    resource_ref = (
        resource.get("text")
        if isinstance(resource, Mapping)
        else None
    )
    if not resource_ref:
        blockers.append("object-render:resource-reference-missing")

    try:
        matrix_number = int(object_report.get("matrix_number"))
    except (TypeError, ValueError):
        matrix_number = None
        blockers.append("object-render:matrix-number-invalid")

    transform: dict[str, Any]
    if matrix_number == -1:
        explicit = object_report.get("explicit_matrix")
        if not isinstance(explicit, Mapping):
            blockers.append("object-render:explicit-transform-missing")
            transform = {
                "mode": "explicit-object-transform",
                "world_matrix_ready": False,
            }
        else:
            try:
                matrix = _matrix_from_explicit(explicit)
            except ValueError as exc:
                blockers.append(f"object-render:{exc}")
                matrix = None
            transform = {
                "mode": "explicit-object-transform",
                "matrix_number": -1,
                "orientation_wxyz": explicit.get(
                    "orientation_runtime_order"
                ),
                "offset_xyz": explicit.get("offset_xyz"),
                "scale": explicit.get("scale"),
                "matrix_storage": (
                    "row-major 4x4 as emitted by FUN_00445ec0; "
                    "translation at indices 12..14"
                ),
                "world_matrix": matrix,
                "world_matrix_ready": matrix is not None,
                "source": {
                    "quaternion_to_matrix": "FUN_00445ec0",
                    "uniform_scale": "FUN_0068c560",
                    "render_vfunc": "0x00699230",
                    "render_instance_transform_vfunc_offset": 0x2C,
                },
            }
    elif matrix_number is not None and matrix_number >= 0:
        selected, reason = _matrix_record_summary(
            parent_object_report,
            matrix_number,
        )
        if reason:
            blockers.append(reason)

        evaluation_summary = None
        numeric_world_matrix = None
        numeric_world_matrix_ready = False
        if selected is not None and isinstance(
            parent_object_report,
            Mapping,
        ):
            resolved_root = parent_multimatrix_root_matrix
            root_state_summary = None
            if resolved_root is None:
                root_state = build_root_transform_state(
                    parent_object_report,
                    scenegraph_updates=parent_scenegraph_updates,
                )
                if root_state.get("ready") is True:
                    resolved_root = root_state.get(
                        "current_root_world_matrix"
                    )
                root_state_summary = {
                    "format": root_state.get("format"),
                    "status": root_state.get("status"),
                    "ready": root_state.get("ready"),
                    "blocking_reasons": root_state.get(
                        "blocking_reasons"
                    ),
                    "constructor_root_matrix": root_state.get(
                        "constructor_root_matrix"
                    ),
                    "scenegraph_update_history_known": root_state.get(
                        "scenegraph_update_history_known"
                    ),
                    "scenegraph_update_count": root_state.get(
                        "scenegraph_update_count"
                    ),
                    "current_root_source": root_state.get(
                        "current_root_source"
                    ),
                    "current_root_world_matrix": root_state.get(
                        "current_root_world_matrix"
                    ),
                    "source": root_state.get("source"),
                }
            else:
                root_state_summary = {
                    "format": "SHIFT.SGBRootTransformState/1",
                    "status": "provided-explicitly",
                    "ready": True,
                    "blocking_reasons": [],
                    "current_root_source": "explicit-root-world-matrix",
                    "current_root_world_matrix": list(resolved_root),
                }

            evaluation = build_multimatrix_evaluation(
                parent_object_report,
                root_world_matrix=resolved_root,
            )
            selected_slot = None
            slots = evaluation.get("slots") or []
            if matrix_number < len(slots):
                selected_slot = slots[matrix_number]
                if (
                    evaluation.get("ready") is True
                    and selected_slot.get("world_matrix_ready") is True
                ):
                    numeric_world_matrix = selected_slot.get(
                        "world_matrix"
                    )
                    numeric_world_matrix_ready = True
            evaluation_summary = {
                "format": evaluation.get("format"),
                "status": evaluation.get("status"),
                "ready": evaluation.get("ready"),
                "root_world_matrix_required": evaluation.get(
                    "root_world_matrix_required"
                ),
                "blocking_reasons": evaluation.get(
                    "blocking_reasons"
                ),
                "root_transform_state": root_state_summary,
                "selected_slot": selected_slot,
                "source": evaluation.get("source"),
            }

        transform = {
            "mode": "parent-multimatrix-slot",
            "matrix_number": matrix_number,
            "selected_parent_matrix_record": selected,
            "multimatrix_matrix_base_offset": 0x04,
            "runtime_slot_stride": 0x40,
            "runtime_slot_offset": matrix_number * 0x40,
            "world_matrix": numeric_world_matrix,
            "world_matrix_ready": numeric_world_matrix_ready,
            "selector_ready": selected is not None,
            "multimatrix_evaluation": evaluation_summary,
            "source": {
                "render_vfunc": "0x00699230",
                "multimatrix_registration": "FUN_006b1820",
                "multimatrix_source_file": (
                    ".\\Source\\RenderHierarchy\\MultiMatrix.cpp"
                ),
                "render_instance_transform_vfunc_offset": 0x2C,
            },
        }
    else:
        transform = {
            "mode": "invalid",
            "world_matrix_ready": False,
        }

    ready = not blockers
    return {
        "format": "SHIFT.SGBObjectRenderHandoff/1",
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": blockers,
        "resource": {
            "reference": resource_ref,
            "serialized_source": "OBJECT third SGB-relative string",
            "runtime_descriptor_offset": 0x80,
            "runtime_loader": "FUN_0069a6c0",
            "render_instance_factory": {
                "object_render_vfunc": "0x00699230",
                "renderer_global": "DAT_00c26058",
                "renderer_factory_vfunc_offset": 0x214,
            },
        },
        "transform": transform,
        "runtime_submission": {
            "render_instance_transform_vfunc_offset": 0x2C,
            "object_render_vfunc": "0x00699230",
            "resource_descriptor_offset": 0x80,
            "matrix_number_offset": 0x84,
            "explicit_orientation_wxyz_offset": 0x88,
            "explicit_offset_xyz_offset": 0x98,
            "explicit_scale_offset": 0xA4,
        },
        "render_binding_boundary": {
            "resource_identity_ready": bool(resource_ref),
            "transform_selector_ready": (
                transform.get("world_matrix_ready") is True
                or transform.get("selector_ready") is True
            ),
            "numeric_world_matrix_ready": (
                transform.get("world_matrix_ready") is True
            ),
            "draw_admission": False,
        },
    }


def _walk_object(
    report: Mapping[str, Any],
    *,
    parent: Mapping[str, Any] | None,
    path: list[int],
    out: list[dict[str, Any]],
    wrapper: Mapping[str, Any],
) -> None:
    kind = _kind(report)
    if kind == "OBJECT":
        handoff = build_object_render_handoff(
            report,
            parent_object_report=parent,
        )
        out.append({
            "wrapper": dict(wrapper),
            "object_path": list(path),
            "handoff": handoff,
        })
        return

    if kind not in {"LOD", "HIERARCHY"}:
        return
    for index, child in enumerate(report.get("subobject_references") or []):
        if not isinstance(child, Mapping):
            continue
        child_report = child.get("report")
        if not isinstance(child_report, Mapping):
            continue
        _walk_object(
            child_report,
            parent=report,
            path=[*path, index],
            out=out,
            wrapper=wrapper,
        )


def build_sgb_object_render_handoff_set(
    sgb_report: Mapping[str, Any],
) -> dict[str, Any]:
    if sgb_report.get("format") != SGB_FORMAT:
        raise ValueError("input must be SHIFT.SGBRuntime/1")

    rows: list[dict[str, Any]] = []
    for chunk in sgb_report.get("chunks") or []:
        if (
            not isinstance(chunk, Mapping)
            or chunk.get("tag") not in {"NODE", "SUMM"}
        ):
            continue
        tag = str(chunk.get("tag"))
        for record in chunk.get("records") or []:
            if not isinstance(record, Mapping):
                continue
            payload = record.get("object_payload") or {}
            report = (
                payload.get("report")
                if isinstance(payload, Mapping)
                else None
            )
            if not isinstance(report, Mapping):
                continue
            wrapper = {
                "chunk": tag,
                "source_record_index": record.get("index"),
                "source_record_offset": record.get("offset"),
                "name": (record.get("name") or {}).get("text"),
                "resource": (record.get("resource") or {}).get("text"),
            }
            _walk_object(
                report,
                parent=None,
                path=[],
                out=rows,
                wrapper=wrapper,
            )

    blockers: list[str] = []
    for index, row in enumerate(rows):
        handoff = row["handoff"]
        if handoff.get("ready") is not True:
            blockers.extend(
                f"object-{index}:{reason}"
                for reason in handoff.get("blocking_reasons") or []
            )
    if not rows:
        blockers.append("object-render:no-object-payloads")

    explicit = sum(
        row["handoff"]["transform"].get("mode")
        == "explicit-object-transform"
        for row in rows
    )
    parent_slot = sum(
        row["handoff"]["transform"].get("mode")
        == "parent-multimatrix-slot"
        for row in rows
    )
    numeric_ready = sum(
        row["handoff"]["transform"].get("world_matrix_ready") is True
        for row in rows
    )

    ready = bool(rows) and not blockers
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "object_count": len(rows),
        "explicit_transform_count": explicit,
        "parent_multimatrix_slot_count": parent_slot,
        "numeric_world_matrix_ready_count": numeric_ready,
        "objects": rows,
        "boundary": {
            "resource_to_runtime_descriptor": "source-backed",
            "render_instance_factory": "source-backed",
            "transform_selector": "source-backed",
            "parent_multimatrix_numeric_world_matrix": "runtime-context-required",
            "draw_admission": False,
        },
    }


def validate_file(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("SGB runtime input must be a JSON object")
    return build_sgb_object_render_handoff_set(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build source-backed SGB OBJECT render handoffs"
    )
    parser.add_argument("sgb_runtime")
    parser.add_argument("output")
    args = parser.parse_args(argv)
    report = validate_file(args.sgb_runtime)
    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "object_count": report["object_count"],
        "explicit_transform_count": report["explicit_transform_count"],
        "parent_multimatrix_slot_count": report[
            "parent_multimatrix_slot_count"
        ],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
