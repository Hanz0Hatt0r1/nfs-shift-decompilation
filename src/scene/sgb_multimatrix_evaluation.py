"""Numerically reproduce the source-backed SGB MultiMatrix update path.

The retail hierarchy constructors create one MultiMatrix only when a
LOD/HIERARCHY object is entered without a parent context. Nested hierarchy
objects inherit that context and select one of its slots with MatrixNumber.

FUN_0068cbb0 builds the local 4x4 matrices. Runtime slot mode 1 is evaluated by
FUN_006b1620 as:

    world[i] = local[i] * world[parent[i]]

Slot zero is special: hierarchy update vfuncs copy an external base matrix into
world[0] before FUN_006b1620 runs. Therefore this module never invents an
identity base for MatrixNumber-backed objects.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from sgb_object_render_handoff import _matrix_from_explicit

FORMAT = "SHIFT.SGBMultiMatrixEvaluation/1"
SGB_FORMAT = "SHIFT.SGBRuntime/1"
BASE_FORMAT = "SHIFT.SGBMultiMatrixBaseSet/1"


def _kind(report: Mapping[str, Any]) -> str | None:
    value = report.get("kind") or {}
    return value.get("text") if isinstance(value, Mapping) else None


def _matrix16(value: Any) -> list[float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 16:
        return None
    try:
        return [float(item) for item in value]
    except (TypeError, ValueError):
        return None


def _mat_mul(left: list[float], right: list[float]) -> list[float]:
    """Match FUN_00401610: row-major result = left * right."""
    return [
        sum(
            left[row * 4 + k] * right[k * 4 + column]
            for k in range(4)
        )
        for row in range(4)
        for column in range(4)
    ]


def _matrix_from_record(record: Mapping[str, Any]) -> list[float]:
    return _matrix_from_explicit({
        "orientation_runtime_order": record.get(
            "orientation_runtime_order"
        ),
        "offset_xyz": record.get("offset_xyz"),
        "scale": record.get("scale"),
    })


def evaluate_multimatrix_records(
    matrix_records: list[Mapping[str, Any]],
    *,
    base_matrix: list[float] | None = None,
    base_source_backed: bool = False,
    base_source: str | None = None,
) -> dict[str, Any]:
    """Evaluate one root MultiMatrix exactly as the mode-1 retail path does."""
    blockers: list[str] = []
    local_matrices: list[list[float] | None] = []
    parents: list[int | None] = []

    for index, record in enumerate(matrix_records):
        try:
            local = _matrix_from_record(record)
        except ValueError as exc:
            blockers.append(f"multimatrix:slot-{index}:{exc}")
            local = None
        local_matrices.append(local)
        try:
            parents.append(int(record.get("parent")))
        except (TypeError, ValueError):
            blockers.append(f"multimatrix:slot-{index}:parent-invalid")
            parents.append(None)

    if not matrix_records:
        blockers.append("multimatrix:no-matrix-records")

    construction_world = [
        list(matrix) if matrix is not None else None
        for matrix in local_matrices
    ]

    base = _matrix16(base_matrix)
    if base_matrix is not None and base is None:
        blockers.append("multimatrix:base-matrix-invalid")

    runtime_world: list[list[float] | None] | None = None
    base_required = bool(matrix_records) and base is None

    if matrix_records and base is not None:
        runtime_world = [
            list(matrix) if matrix is not None else None
            for matrix in local_matrices
        ]
        runtime_world[0] = list(base)

        # FUN_006b1620 intentionally skips slot zero and walks the remaining
        # metadata records in slot order.  FUN_0068cbb0 leaves mode=1 and
        # writes the source parent low byte at metadata +0x0b.
        for index in range(1, len(matrix_records)):
            parent = parents[index]
            local = local_matrices[index]
            if parent is None:
                continue
            if parent < 0 or parent >= len(matrix_records):
                blockers.append(
                    f"multimatrix:slot-{index}:parent-out-of-range:"
                    f"{parent}:count={len(matrix_records)}"
                )
                runtime_world[index] = None
                continue
            parent_world = runtime_world[parent]
            if local is None or parent_world is None:
                blockers.append(
                    f"multimatrix:slot-{index}:dependency-not-ready"
                )
                runtime_world[index] = None
                continue
            runtime_world[index] = _mat_mul(local, parent_world)

    numeric_ready = (
        runtime_world is not None
        and all(matrix is not None for matrix in runtime_world)
        and not blockers
    )
    source_backed_ready = numeric_ready and bool(base_source_backed)

    slots = []
    for index, record in enumerate(matrix_records):
        slots.append({
            "index": index,
            "parent": parents[index],
            "runtime_mode": 1,
            "local_matrix": local_matrices[index],
            "construction_world_matrix": construction_world[index],
            "runtime_world_matrix": (
                runtime_world[index]
                if runtime_world is not None
                else None
            ),
            "source": {
                "local_builder": "FUN_0068cbb0",
                "mode_evaluator": "FUN_006b1620 case 1",
                "multiply": "FUN_00401610(local, parent_world)",
            },
        })

    return {
        "format": "SHIFT.SGBMultiMatrixContext/1",
        "status": (
            "ready"
            if numeric_ready
            else ("base-required" if base_required and not blockers else "blocked")
        ),
        "ready": numeric_ready,
        "source_backed_world_ready": source_backed_ready,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "base": {
            "required_for_runtime_update": bool(matrix_records),
            "provided": base is not None,
            "matrix": base,
            "source_backed": bool(base_source_backed),
            "source": base_source,
            "runtime_write": (
                "hierarchy vfunc +0x2c copies external matrix to world slot 0"
            ),
        },
        "slot_count": len(matrix_records),
        "slots": slots,
        "construction_boundary": {
            "local_and_world_initially_equal": True,
            "source": "FUN_0068cbb0 -> FUN_00401d10",
        },
        "runtime_update_boundary": {
            "slot_zero_replaced_by_external_base": True,
            "dependent_formula": "world[i] = local[i] * world[parent[i]]",
            "multiply_call_convention": (
                "FUN_00401610: ECX=dest, EDX=local, stack=parent_world"
            ),
        },
    }


def _base_key(chunk: str, record_index: int) -> str:
    return f"{chunk}:{record_index}"


def _parse_base_set(value: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    if value is None:
        return {}
    if value.get("format") != BASE_FORMAT:
        raise ValueError("base input must be SHIFT.SGBMultiMatrixBaseSet/1")
    result: dict[str, dict[str, Any]] = {}
    for ordinal, row in enumerate(value.get("bases") or []):
        if not isinstance(row, Mapping):
            raise ValueError(f"base row {ordinal} must be an object")
        chunk = str(row.get("chunk") or "")
        try:
            record_index = int(row.get("source_record_index"))
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"base row {ordinal} has invalid source_record_index"
            ) from exc
        key = _base_key(chunk, record_index)
        if key in result:
            raise ValueError(f"duplicate MultiMatrix base key: {key}")
        matrix = _matrix16(row.get("matrix"))
        if matrix is None:
            raise ValueError(f"base row {ordinal} matrix must contain 16 numbers")
        result[key] = {
            "matrix": matrix,
            "source_backed": row.get("source_backed") is True,
            "source": row.get("source"),
        }
    return result


def _object_resource(report: Mapping[str, Any]) -> str | None:
    value = report.get("resource_filename") or {}
    return value.get("text") if isinstance(value, Mapping) else None


def _walk_root(
    report: Mapping[str, Any],
    *,
    chunk: str,
    record_index: int,
    wrapper_name: str | None,
    path: list[int],
    context: Mapping[str, Any] | None,
    context_owner_path: list[int] | None,
    base: Mapping[str, Any] | None,
    objects: list[dict[str, Any]],
    hierarchies: list[dict[str, Any]],
    blockers: list[str],
) -> None:
    kind = _kind(report)

    if kind in {"LOD", "HIERARCHY"}:
        active_context = context
        active_owner_path = context_owner_path
        inherited = context is not None

        if not inherited:
            records = [
                row
                for row in (report.get("matrix_records") or [])
                if isinstance(row, Mapping)
            ]
            active_context = evaluate_multimatrix_records(
                records,
                base_matrix=(base or {}).get("matrix"),
                base_source_backed=(base or {}).get("source_backed") is True,
                base_source=(base or {}).get("source"),
            )
            active_owner_path = list(path)

        try:
            matrix_number = int(report.get("matrix_number"))
        except (TypeError, ValueError):
            matrix_number = None
            blockers.append(
                f"multimatrix:{chunk}:{record_index}:"
                f"path-{'.'.join(map(str, path)) or 'root'}:"
                "matrix-number-invalid"
            )

        selector_ready = False
        selected_world = None
        selected_source_backed = False
        if inherited and matrix_number is not None and matrix_number >= 0:
            slots = list((active_context or {}).get("slots") or [])
            if matrix_number < len(slots):
                selected_world = slots[matrix_number].get(
                    "runtime_world_matrix"
                )
                selector_ready = True
                selected_source_backed = bool(
                    (active_context or {}).get("source_backed_world_ready")
                )
            else:
                blockers.append(
                    f"multimatrix:{chunk}:{record_index}:"
                    f"path-{'.'.join(map(str, path)) or 'root'}:"
                    f"matrix-number-out-of-range:{matrix_number}:"
                    f"count={len(slots)}"
                )
        elif not inherited:
            slots = list((active_context or {}).get("slots") or [])
            if slots:
                selected_world = slots[0].get("runtime_world_matrix")
                selector_ready = True
                selected_source_backed = bool(
                    (active_context or {}).get("source_backed_world_ready")
                )

        hierarchies.append({
            "wrapper": {
                "chunk": chunk,
                "source_record_index": record_index,
                "name": wrapper_name,
            },
            "object_path": list(path),
            "kind": kind,
            "matrix_number": matrix_number,
            "context_inherited": inherited,
            "context_owner_path": (
                list(active_owner_path)
                if active_owner_path is not None
                else None
            ),
            "serialized_matrix_table_ignored_for_runtime_context": inherited,
            "selector_ready": selector_ready,
            "selected_world_matrix": selected_world,
            "source_backed_world_ready": (
                selector_ready and selected_world is not None
                and selected_source_backed
            ),
            "multimatrix": (
                dict(active_context)
                if not inherited and isinstance(active_context, Mapping)
                else None
            ),
            "source": {
                "constructor": "FUN_006ab4a0 / LOD-equivalent constructor",
                "new_context_when_parent_null": True,
                "inherit_context_when_parent_nonnull": True,
                "registration": "FUN_006b1820",
            },
        })

        for index, child in enumerate(report.get("subobject_references") or []):
            if not isinstance(child, Mapping):
                continue
            child_report = child.get("report")
            if not isinstance(child_report, Mapping):
                continue
            _walk_root(
                child_report,
                chunk=chunk,
                record_index=record_index,
                wrapper_name=wrapper_name,
                path=[*path, index],
                context=active_context,
                context_owner_path=active_owner_path,
                base=base,
                objects=objects,
                hierarchies=hierarchies,
                blockers=blockers,
            )
        return

    if kind != "OBJECT":
        return

    resource = _object_resource(report)
    try:
        matrix_number = int(report.get("matrix_number"))
    except (TypeError, ValueError):
        matrix_number = None

    world_matrix = None
    numeric_ready = False
    source_backed = False
    transform_mode = "invalid"
    object_blockers: list[str] = []

    if matrix_number == -1:
        explicit = report.get("explicit_matrix")
        if not isinstance(explicit, Mapping):
            object_blockers.append("explicit-transform-missing")
        else:
            try:
                world_matrix = _matrix_from_explicit(explicit)
                numeric_ready = True
                source_backed = True
                transform_mode = "explicit-object-transform"
            except ValueError as exc:
                object_blockers.append(str(exc))
    elif matrix_number is not None and matrix_number >= 0:
        transform_mode = "multimatrix-slot"
        if context is None:
            object_blockers.append("multimatrix-context-missing")
        else:
            slots = list(context.get("slots") or [])
            if matrix_number >= len(slots):
                object_blockers.append(
                    f"matrix-number-out-of-range:{matrix_number}:count={len(slots)}"
                )
            else:
                world_matrix = slots[matrix_number].get("runtime_world_matrix")
                numeric_ready = world_matrix is not None
                source_backed = (
                    numeric_ready
                    and context.get("source_backed_world_ready") is True
                )
                if not numeric_ready:
                    object_blockers.append("multimatrix-base-required")
    else:
        object_blockers.append("matrix-number-invalid")

    if not resource:
        object_blockers.append("resource-reference-missing")

    objects.append({
        "wrapper": {
            "chunk": chunk,
            "source_record_index": record_index,
            "name": wrapper_name,
        },
        "object_path": list(path),
        "resource_ref": resource,
        "matrix_number": matrix_number,
        "transform_mode": transform_mode,
        "world_matrix": world_matrix,
        "numeric_world_matrix_ready": numeric_ready,
        "source_backed_world_matrix_ready": source_backed,
        "context_owner_path": (
            list(context_owner_path)
            if context_owner_path is not None
            else None
        ),
        "blocking_reasons": object_blockers,
        "render_binding_admission": (
            bool(resource) and source_backed and not object_blockers
        ),
        "source": {
            "render_vfunc": "0x00699230",
            "resource_descriptor_offset": 0x80,
            "matrix_number_offset": 0x84,
            "multimatrix_registration": "FUN_006b1820",
        },
    })


def build_sgb_multimatrix_evaluation(
    sgb_report: Mapping[str, Any],
    *,
    base_set: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if sgb_report.get("format") != SGB_FORMAT:
        raise ValueError("input must be SHIFT.SGBRuntime/1")

    bases = _parse_base_set(base_set)
    objects: list[dict[str, Any]] = []
    hierarchies: list[dict[str, Any]] = []
    blockers: list[str] = []
    root_count = 0
    root_context_count = 0
    base_supplied_count = 0

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
            try:
                record_index = int(record.get("index"))
            except (TypeError, ValueError):
                blockers.append(f"multimatrix:{tag}:record-index-invalid")
                continue

            root_count += 1
            key = _base_key(tag, record_index)
            base = bases.get(key)
            if base is not None:
                base_supplied_count += 1
            if _kind(report) in {"LOD", "HIERARCHY"}:
                root_context_count += 1

            _walk_root(
                report,
                chunk=tag,
                record_index=record_index,
                wrapper_name=(record.get("name") or {}).get("text"),
                path=[],
                context=None,
                context_owner_path=None,
                base=base,
                objects=objects,
                hierarchies=hierarchies,
                blockers=blockers,
            )

    if not objects:
        blockers.append("multimatrix:no-renderable-objects")

    numeric_ready_count = sum(
        row.get("numeric_world_matrix_ready") is True
        for row in objects
    )
    source_backed_count = sum(
        row.get("source_backed_world_matrix_ready") is True
        for row in objects
    )
    admitted_count = sum(
        row.get("render_binding_admission") is True
        for row in objects
    )
    base_required_objects = sum(
        "multimatrix-base-required" in (row.get("blocking_reasons") or [])
        for row in objects
    )

    structural_ready = not blockers
    numeric_complete = (
        bool(objects)
        and numeric_ready_count == len(objects)
        and not blockers
    )
    source_backed_complete = (
        bool(objects)
        and source_backed_count == len(objects)
        and not blockers
    )

    return {
        "format": FORMAT,
        "version": 1,
        "status": (
            "ready"
            if source_backed_complete
            else ("partial" if objects else "blocked")
        ),
        "ready": source_backed_complete,
        "structural_ready": structural_ready,
        "numeric_complete": numeric_complete,
        "source_backed_complete": source_backed_complete,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "summary": {
            "root_wrapper_count": root_count,
            "root_multimatrix_context_count": root_context_count,
            "base_matrix_supplied_count": base_supplied_count,
            "object_count": len(objects),
            "numeric_world_matrix_ready_count": numeric_ready_count,
            "source_backed_world_matrix_ready_count": source_backed_count,
            "render_binding_admitted_object_count": admitted_count,
            "base_required_object_count": base_required_objects,
        },
        "hierarchies": hierarchies,
        "objects": objects,
        "boundary": {
            "top_level_wrapper_parent_context": "null via FUN_006aed50",
            "root_multimatrix_external_base": (
                "required for source-backed runtime-update world matrices"
            ),
            "identity_base_assumed": False,
            "explicit_object_matrix_independent_of_multimatrix": True,
            "final_render_binding_join": "next-stage",
        },
        "evidence": {
            "local_matrix_builder": "FUN_0068cbb0",
            "runtime_evaluator": "FUN_006b1620",
            "matrix_multiply": "FUN_00401610",
            "hierarchy_update": "FUN_006ab710 / FUN_0068d9a0 / FUN_006b4280",
            "object_render": "0x00699230",
        },
    }


def validate_files(
    sgb_runtime_path: str | Path,
    base_set_path: str | Path | None = None,
) -> dict[str, Any]:
    sgb_report = json.loads(
        Path(sgb_runtime_path).read_text(encoding="utf-8")
    )
    base_set = None
    if base_set_path is not None:
        base_set = json.loads(
            Path(base_set_path).read_text(encoding="utf-8")
        )
    return build_sgb_multimatrix_evaluation(
        sgb_report,
        base_set=base_set,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate source-backed SGB MultiMatrix hierarchy transforms"
    )
    parser.add_argument("sgb_runtime")
    parser.add_argument("output")
    parser.add_argument(
        "--base-matrices",
        help="optional SHIFT.SGBMultiMatrixBaseSet/1 JSON",
    )
    args = parser.parse_args(argv)

    report = validate_files(
        args.sgb_runtime,
        args.base_matrices,
    )
    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "numeric_complete": report["numeric_complete"],
        "summary": report["summary"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
