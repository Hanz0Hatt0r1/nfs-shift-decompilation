"""Source-backed evaluator for SHIFT RenderHierarchy MultiMatrix tables.

Retail construction stores one local 4x4 matrix and one runtime/world 4x4 matrix
per serialized MATRIX record. All descriptors start in mode 1. Before an update,
the runtime owner overwrites world slot 0 with an externally supplied root
matrix, then FUN_006b1620 evaluates slots 1..N-1 in source order as:

    world[i] = local[i] * world[parent_low_byte]

This module deliberately requires that root input instead of assuming identity.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.SGBMultiMatrixEvaluation/1"
OBJECT_FORMAT = "SHIFT.SGBObjectRuntime/1"
OWNER_KINDS = {"LOD", "HIERARCHY"}


def _kind(report: Mapping[str, Any]) -> str | None:
    value = report.get("kind") or {}
    return value.get("text") if isinstance(value, Mapping) else None


def _as_float_vector(value: Any, length: int, label: str) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != length:
        raise ValueError(f"{label} must contain {length} values")
    try:
        return [float(item) for item in value]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc


def matrix_from_record(record: Mapping[str, Any]) -> list[float]:
    """Reproduce FUN_0068cbb0 local-matrix construction for one MATRIX record."""
    w, x, y, z = _as_float_vector(
        record.get("orientation_runtime_order"), 4, "orientation_runtime_order"
    )
    tx, ty, tz = _as_float_vector(record.get("offset_xyz"), 3, "offset_xyz")
    try:
        scale = float(record.get("scale"))
    except (TypeError, ValueError) as exc:
        raise ValueError("scale must be numeric") from exc

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
        matrix[index] *= scale
    matrix[12] = tx
    matrix[13] = ty
    matrix[14] = tz
    return matrix


def matrix_multiply(a: Sequence[float], b: Sequence[float]) -> list[float]:
    """Return a*b using the same row-major/D3D convention as FUN_00401619."""
    if len(a) != 16 or len(b) != 16:
        raise ValueError("matrix multiply requires two 4x4 matrices")
    return [
        sum(float(a[row * 4 + k]) * float(b[k * 4 + col]) for k in range(4))
        for row in range(4)
        for col in range(4)
    ]


def _root_matrix(value: Any) -> list[float] | None:
    if value is None:
        return None
    return _as_float_vector(value, 16, "root_world_matrix")


def evaluate_matrix_records(
    matrix_records: Sequence[Mapping[str, Any]],
    *,
    root_world_matrix: Sequence[float] | None = None,
) -> dict[str, Any]:
    """Evaluate one static MultiMatrix table with an explicit runtime root matrix.

    The implementation mirrors the construction/update path actually used by the
    retail owner wrappers. It initializes world slots from their local matrices,
    overwrites world slot 0 when a root is supplied, and evaluates descriptor
    mode 1 for slots 1..N-1 in source order. Parent indices are the low byte of
    the serialized signed parent dword because FUN_0068cbb0 stores only SUB41.
    """
    records = [
        dict(record)
        for record in matrix_records
        if isinstance(record, Mapping)
    ]
    blockers: list[str] = []
    if len(records) != len(matrix_records):
        blockers.append("multimatrix:matrix-record-invalid")
    if not records:
        blockers.append("multimatrix:no-matrix-records")

    locals_: list[list[float] | None] = []
    parent_indices: list[int | None] = []
    for index, record in enumerate(records):
        try:
            local = matrix_from_record(record)
        except ValueError as exc:
            local = None
            blockers.append(f"multimatrix:slot-{index}:{exc}")
        locals_.append(local)
        try:
            parent_raw = int(record.get("parent"))
        except (TypeError, ValueError):
            parent_indices.append(None)
            if index != 0:
                blockers.append(f"multimatrix:slot-{index}:parent-invalid")
        else:
            parent_indices.append(parent_raw & 0xFF)

    try:
        root = _root_matrix(root_world_matrix)
    except ValueError as exc:
        root = None
        blockers.append(f"multimatrix:{exc}")
    if root is None:
        blockers.append("multimatrix:root-world-matrix-required")

    world: list[list[float] | None] = [
        list(local) if local is not None else None for local in locals_
    ]
    if world and root is not None:
        world[0] = list(root)
        for index in range(1, len(world)):
            parent = parent_indices[index]
            if parent is None:
                world[index] = None
                continue
            if parent >= len(world):
                blockers.append(
                    f"multimatrix:slot-{index}:parent-out-of-range:"
                    f"{parent}:count={len(world)}"
                )
                world[index] = None
                continue
            local = locals_[index]
            parent_world = world[parent]
            if local is None or parent_world is None:
                blockers.append(
                    f"multimatrix:slot-{index}:dependency-unavailable"
                )
                world[index] = None
                continue
            world[index] = matrix_multiply(local, parent_world)

    blockers = list(dict.fromkeys(blockers))
    slots = []
    for index, record in enumerate(records):
        slots.append({
            "index": index,
            "serialized_parent": record.get("parent"),
            "runtime_parent_index": parent_indices[index],
            "descriptor_mode": 1,
            "descriptor_self_index": index & 0xFF,
            "local_matrix": locals_[index],
            "world_matrix": world[index] if root is not None else None,
            "world_matrix_ready": (
                root is not None and world[index] is not None
            ),
        })

    ready = bool(records) and root is not None and not blockers
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": blockers,
        "matrix_count": len(records),
        "root_world_matrix": root,
        "root_world_matrix_required": True,
        "slots": slots,
        "runtime_layout": {
            "allocation_bytes_per_slot": 0x90,
            "local_matrix_stride": 0x40,
            "world_matrix_stride": 0x40,
            "descriptor_stride": 0x10,
            "descriptor_world_pointer_offset": 0x00,
            "descriptor_mode_offset": 0x08,
            "descriptor_parent_index_offset": 0x0B,
            "descriptor_self_index_offset": 0x0C,
        },
        "source": {
            "constructor": "FUN_006b144b",
            "local_matrix_initializer": "FUN_0068cbb0",
            "root_world_overwrite": [
                "FUN_006ab710",
                "FUN_006b4280",
            ],
            "evaluator": "FUN_006b1620",
            "matrix_multiply": "FUN_00401610/FUN_00401619",
            "matrix_copy": "FUN_00401d10",
            "source_file": ".\\Source\\RenderHierarchy\\MultiMatrix.cpp",
            "static_descriptor_mode": 1,
            "composition": (
                "world[i] = local[i] * world[parent_low_byte]"
            ),
            "evaluation_order": "slot index 1..N-1",
        },
    }


def build_multimatrix_evaluation(
    owner_report: Mapping[str, Any],
    *,
    root_world_matrix: Sequence[float] | None = None,
) -> dict[str, Any]:
    if owner_report.get("format") != OBJECT_FORMAT:
        raise ValueError(
            "owner input must be SHIFT.SGBObjectRuntime/1"
        )
    kind = _kind(owner_report)
    if kind not in OWNER_KINDS:
        raise ValueError(
            "MultiMatrix owner must be LOD or HIERARCHY"
        )
    result = evaluate_matrix_records(
        owner_report.get("matrix_records") or [],
        root_world_matrix=root_world_matrix,
    )
    result["owner_kind"] = kind
    result["owner_matrix_number"] = owner_report.get(
        "matrix_number"
    )
    return result
