"""Reconstruct the source-backed SGB MultiMatrix world-transform path.

Retail MultiMatrix uses two 0x40-byte matrix arrays plus 0x10-byte metadata per
slot. FUN_0068cbb0 builds local matrices and initially copies each local matrix
to the second array. FUN_006b1620 case 1 then updates slots 1..N-1 as:

    world[slot] = local[source_slot] * world[parent_slot]

The exact operand order is confirmed by the PE call convention at 0x006b169c:
EDX receives the local matrix and the stack argument receives the parent world
matrix before FUN_00401610.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.SGBMultiMatrixWorldTransformSet/1"
SGB_FORMAT = "SHIFT.SGBRuntime/1"
OBJECT_FORMAT = "SHIFT.SGBObjectRuntime/1"


def matrix_multiply(left: Sequence[float], right: Sequence[float]) -> list[float]:
    """Return the retail row-major 4x4 product left * right."""
    if len(left) != 16 or len(right) != 16:
        raise ValueError("matrix operands must contain 16 floats")
    a = [float(value) for value in left]
    b = [float(value) for value in right]
    return [
        sum(a[row * 4 + k] * b[k * 4 + col] for k in range(4))
        for row in range(4)
        for col in range(4)
    ]


def matrix_from_wxyz_transform(
    orientation_wxyz: Sequence[float],
    offset_xyz: Sequence[float],
    scale: float,
) -> list[float]:
    """Reproduce FUN_00445ec0 + FUN_0068c560 + translation writes."""
    if len(orientation_wxyz) != 4:
        raise ValueError("orientation_wxyz must contain four floats")
    if len(offset_xyz) != 3:
        raise ValueError("offset_xyz must contain three floats")

    w, x, y, z = [float(value) for value in orientation_wxyz]
    tx, ty, tz = [float(value) for value in offset_xyz]
    s = float(scale)

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


def matrix_from_record(record: Mapping[str, Any]) -> list[float]:
    orientation = record.get("orientation_runtime_order")
    offset = record.get("offset_xyz")
    scale = record.get("scale")
    if not isinstance(orientation, (list, tuple)):
        raise ValueError("matrix record orientation is missing")
    if not isinstance(offset, (list, tuple)):
        raise ValueError("matrix record offset is missing")
    return matrix_from_wxyz_transform(orientation, offset, scale)


def evaluate_multimatrix_records(
    matrix_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    records = [row for row in matrix_records if isinstance(row, Mapping)]
    blockers: list[str] = []
    local_matrices: list[list[float]] = []

    for slot, record in enumerate(records):
        try:
            local_matrices.append(matrix_from_record(record))
        except (TypeError, ValueError) as exc:
            blockers.append(f"multimatrix:slot-{slot}:local-matrix:{exc}")
            local_matrices.append([0.0] * 16)

    # FUN_0068cbb0 copies every newly built local matrix into the second array.
    world_matrices = [list(matrix) for matrix in local_matrices]
    metadata: list[dict[str, Any]] = []

    for slot, record in enumerate(records):
        try:
            parent = int(record.get("parent"))
        except (TypeError, ValueError):
            parent = None
            blockers.append(f"multimatrix:slot-{slot}:parent-invalid")

        metadata.append({
            "slot": slot,
            "operation_type": 1,
            "parent_serialized": parent,
            "parent_byte": (
                parent & 0xFF if parent is not None else None
            ),
            "source_slot": slot,
            "world_slot_stride": 0x40,
            "metadata_stride": 0x10,
            "world_pointer_metadata_offset": 0x00,
            "operation_type_metadata_offset": 0x08,
            "parent_metadata_offset": 0x0B,
            "source_slot_metadata_offset": 0x0C,
        })

    # FUN_006b1620 deliberately starts at slot 1; slot 0 remains the initial
    # local->world copy regardless of its serialized parent byte.
    for slot in range(1, len(records)):
        meta = metadata[slot]
        parent_byte = meta["parent_byte"]
        source_slot = meta["source_slot"]
        if parent_byte is None or not 0 <= parent_byte < len(records):
            blockers.append(
                f"multimatrix:slot-{slot}:parent-out-of-range:{parent_byte}"
            )
            continue
        if not 0 <= source_slot < len(records):
            blockers.append(
                f"multimatrix:slot-{slot}:source-slot-out-of-range:{source_slot}"
            )
            continue
        world_matrices[slot] = matrix_multiply(
            local_matrices[source_slot],
            world_matrices[parent_byte],
        )

    slots = [
        {
            **metadata[index],
            "local_matrix": local_matrices[index],
            "world_matrix": world_matrices[index],
            "world_update": (
                "initial-local-copy"
                if index == 0
                else "case1:local[source_slot]*world[parent_byte]"
            ),
        }
        for index in range(len(records))
    ]
    return {
        "format": "SHIFT.SGBMultiMatrixRuntime/1",
        "version": 1,
        "status": "ready" if not blockers else "blocked",
        "ready": not blockers,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "slot_count": len(records),
        "local_array_stride": 0x40,
        "world_array_stride": 0x40,
        "metadata_stride": 0x10,
        "slots": slots,
        "source": {
            "allocator": "FUN_006b144b",
            "local_builder": "FUN_0068cbb0",
            "updater": "FUN_006b1620",
            "case1_matrix_product": "FUN_00401610/FUN_00401619",
            "case1_operand_order": "local * parent_world",
            "matrix_copy": "FUN_00401d10",
        },
    }


def _kind(report: Mapping[str, Any]) -> str | None:
    value = report.get("kind") or {}
    return value.get("text") if isinstance(value, Mapping) else None


def _wrapper_summary(
    record: Mapping[str, Any],
    tag: str,
) -> dict[str, Any]:
    return {
        "chunk": tag,
        "source_record_index": record.get("index"),
        "source_record_offset": record.get("offset"),
        "name": (record.get("name") or {}).get("text"),
        "resource": (record.get("resource") or {}).get("text"),
    }


def _context_id(wrapper: Mapping[str, Any], path: Sequence[int]) -> str:
    chunk = wrapper.get("chunk") or "?"
    index = wrapper.get("source_record_index")
    suffix = ".".join(str(value) for value in path) if path else "root"
    return f"{chunk}:{index}:{suffix}"


def _walk_object_graph(
    report: Mapping[str, Any],
    *,
    wrapper: Mapping[str, Any],
    path: list[int],
    incoming_context: Mapping[str, Any] | None,
    contexts: list[dict[str, Any]],
    objects: list[dict[str, Any]],
    containers: list[dict[str, Any]],
    blockers: list[str],
) -> None:
    kind = _kind(report)
    if kind in {"LOD", "HIERARCHY"}:
        context = incoming_context
        ownership = "inherited"
        selector = None

        if incoming_context is None:
            records = [
                row
                for row in (report.get("matrix_records") or [])
                if isinstance(row, Mapping)
            ]
            if records:
                evaluated = evaluate_multimatrix_records(records)
                context = {
                    "id": _context_id(wrapper, path),
                    "runtime": evaluated,
                }
                contexts.append({
                    "context_id": context["id"],
                    "owner": {
                        "wrapper": dict(wrapper),
                        "object_path": list(path),
                        "object_kind": kind,
                    },
                    "runtime": evaluated,
                })
                ownership = "owned"
                if evaluated.get("ready") is not True:
                    blockers.extend(
                        f"{context['id']}:{reason}"
                        for reason in evaluated.get("blocking_reasons") or []
                    )
            elif report.get("subobjects"):
                blockers.append(
                    f"multimatrix:{_context_id(wrapper, path)}:"
                    "container-has-no-context"
                )
                context = None
                ownership = "missing"
        else:
            try:
                matrix_number = int(report.get("matrix_number"))
            except (TypeError, ValueError):
                matrix_number = None
            slots = (
                incoming_context.get("runtime", {}).get("slots") or []
            )
            if (
                matrix_number is None
                or matrix_number < 0
                or matrix_number >= len(slots)
            ):
                blockers.append(
                    f"multimatrix:{_context_id(wrapper, path)}:"
                    f"inherited-selector-out-of-range:{matrix_number}:"
                    f"count={len(slots)}"
                )
            else:
                selector = {
                    "matrix_number": matrix_number,
                    "context_id": incoming_context.get("id"),
                    "world_matrix": slots[matrix_number]["world_matrix"],
                }

        containers.append({
            "wrapper": dict(wrapper),
            "object_path": list(path),
            "object_kind": kind,
            "matrix_number": report.get("matrix_number"),
            "matrix_record_count": len(report.get("matrix_records") or []),
            "context_ownership": ownership,
            "context_id": context.get("id") if context else None,
            "inherited_selector": selector,
            "serialized_matrix_table_used_for_context": ownership == "owned",
        })

        for index, child in enumerate(report.get("subobject_references") or []):
            if not isinstance(child, Mapping):
                continue
            child_report = child.get("report")
            if not isinstance(child_report, Mapping):
                continue
            _walk_object_graph(
                child_report,
                wrapper=wrapper,
                path=[*path, index],
                incoming_context=context,
                contexts=contexts,
                objects=objects,
                containers=containers,
                blockers=blockers,
            )
        return

    if kind != "OBJECT":
        return

    try:
        matrix_number = int(report.get("matrix_number"))
    except (TypeError, ValueError):
        matrix_number = None

    transform: dict[str, Any]
    ready = True
    reasons: list[str] = []

    if matrix_number == -1:
        explicit = report.get("explicit_matrix")
        if not isinstance(explicit, Mapping):
            ready = False
            reasons.append("object-world:explicit-transform-missing")
            transform = {
                "mode": "explicit-object-transform",
                "world_matrix": None,
            }
        else:
            try:
                world = matrix_from_wxyz_transform(
                    explicit.get("orientation_runtime_order") or [],
                    explicit.get("offset_xyz") or [],
                    explicit.get("scale"),
                )
            except (TypeError, ValueError) as exc:
                ready = False
                reasons.append(f"object-world:explicit-transform:{exc}")
                world = None
            transform = {
                "mode": "explicit-object-transform",
                "world_matrix": world,
                "context_id": None,
                "matrix_number": -1,
                "source": "OBJECT vfunc 0x00699230",
            }
    elif matrix_number is not None and matrix_number >= 0:
        slots = (
            incoming_context.get("runtime", {}).get("slots") or []
            if isinstance(incoming_context, Mapping)
            else []
        )
        if (
            not isinstance(incoming_context, Mapping)
            or matrix_number >= len(slots)
        ):
            ready = False
            reasons.append(
                "object-world:multimatrix-slot-unavailable:"
                f"{matrix_number}:count={len(slots)}"
            )
            world = None
            context_id = (
                incoming_context.get("id")
                if isinstance(incoming_context, Mapping)
                else None
            )
        else:
            slot = slots[matrix_number]
            world = slot.get("world_matrix")
            context_id = incoming_context.get("id")
            if incoming_context.get("runtime", {}).get("ready") is not True:
                ready = False
                reasons.append("object-world:multimatrix-context-blocked")
        transform = {
            "mode": "multimatrix-world-slot",
            "world_matrix": world,
            "context_id": context_id,
            "matrix_number": matrix_number,
            "runtime_slot_stride": 0x40,
            "runtime_slot_offset": matrix_number * 0x40,
            "source": (
                "OBJECT 0x00699230 -> FUN_006b1820 / "
                "MultiMatrix world array +0x04"
            ),
        }
    else:
        ready = False
        reasons.append("object-world:matrix-number-invalid")
        transform = {
            "mode": "invalid",
            "world_matrix": None,
            "context_id": None,
            "matrix_number": matrix_number,
        }

    if not ready:
        blockers.extend(
            f"{_context_id(wrapper, path)}:{reason}"
            for reason in reasons
        )

    objects.append({
        "wrapper": dict(wrapper),
        "object_path": list(path),
        "resource": (report.get("resource_filename") or {}).get("text"),
        "matrix_number": matrix_number,
        "ready": ready,
        "blocking_reasons": reasons,
        "transform": transform,
    })


def build_sgb_multimatrix_world_transforms(
    sgb_report: Mapping[str, Any],
) -> dict[str, Any]:
    if sgb_report.get("format") != SGB_FORMAT:
        raise ValueError("input must be SHIFT.SGBRuntime/1")

    contexts: list[dict[str, Any]] = []
    objects: list[dict[str, Any]] = []
    containers: list[dict[str, Any]] = []
    blockers: list[str] = []

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
            root = (
                payload.get("report")
                if isinstance(payload, Mapping)
                else None
            )
            if not isinstance(root, Mapping):
                continue
            _walk_object_graph(
                root,
                wrapper=_wrapper_summary(record, tag),
                path=[],
                incoming_context=None,
                contexts=contexts,
                objects=objects,
                containers=containers,
                blockers=blockers,
            )

    if not objects:
        blockers.append("object-world:no-object-payloads")

    ready_objects = sum(row.get("ready") is True for row in objects)
    explicit_objects = sum(
        row.get("transform", {}).get("mode") == "explicit-object-transform"
        for row in objects
    )
    multimatrix_objects = sum(
        row.get("transform", {}).get("mode") == "multimatrix-world-slot"
        for row in objects
    )
    owned_containers = sum(
        row.get("context_ownership") == "owned"
        for row in containers
    )
    inherited_containers = sum(
        row.get("context_ownership") == "inherited"
        for row in containers
    )

    blockers = list(dict.fromkeys(blockers))
    ready = bool(objects) and ready_objects == len(objects) and not blockers
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": blockers,
        "context_count": len(contexts),
        "container_count": len(containers),
        "object_count": len(objects),
        "ready_object_count": ready_objects,
        "explicit_object_count": explicit_objects,
        "multimatrix_object_count": multimatrix_objects,
        "owned_context_container_count": owned_containers,
        "inherited_context_container_count": inherited_containers,
        "contexts": contexts,
        "containers": containers,
        "objects": objects,
        "render_binding_boundary": {
            "numeric_object_world_matrices_ready": ready,
            "matrix_convention": (
                "row-vector/row-major, translation indices 12..14"
            ),
            "multimatrix_case1_world_rule": "local * parent_world",
            "draw_admission": False,
            "next_join": (
                "SHIFT.SGBScenePlacement/1 + "
                "SHIFT.SGBObjectRenderHandoffSet/1"
            ),
        },
        "evidence": {
            "allocator": "FUN_006b144b",
            "local_builder": "FUN_0068cbb0",
            "hierarchy_updater": "FUN_006b1620",
            "matrix_multiply": "FUN_00401610/FUN_00401619",
            "hierarchy_render_constructor": "FUN_006ab4a0",
            "lod_render_constructor": "FUN_006b4050",
            "object_render_vfunc": "0x00699230",
        },
    }


def validate_file(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("SGB runtime input must be a JSON object")
    return build_sgb_multimatrix_world_transforms(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate SGB MultiMatrix world transforms"
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
        "context_count": report["context_count"],
        "object_count": report["object_count"],
        "ready_object_count": report["ready_object_count"],
        "explicit_object_count": report["explicit_object_count"],
        "multimatrix_object_count": report["multimatrix_object_count"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
