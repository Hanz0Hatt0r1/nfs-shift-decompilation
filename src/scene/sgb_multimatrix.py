"""Source-backed evaluator for SHIFT RenderHierarchy MultiMatrix tables.

Retail construction stores one local 4x4 matrix and one runtime/world 4x4 matrix
per serialized MATRIX record. All descriptors start in mode 1. Before an update,
the runtime owner overwrites world slot 0 with an externally supplied root
matrix, then FUN_006b1620 evaluates slots 1..N-1 in source order as:

    world[i] = local[i] * world[parent_low_byte]

This module deliberately requires that root input instead of assuming identity.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.SGBMultiMatrixEvaluation/1"
ROOT_SOLVE_FORMAT = "SHIFT.SGBMultiMatrixRootSolve/1"
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


def _identity_matrix() -> list[float]:
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]


def _affine_inverse(
    value: Sequence[float],
    *,
    label: str,
    tolerance: float = 1.0e-8,
) -> list[float]:
    matrix = _as_float_vector(value, 16, label)
    if not all(math.isfinite(item) for item in matrix):
        raise ValueError(f"{label} must contain finite values")
    if (
        abs(matrix[3]) > tolerance
        or abs(matrix[7]) > tolerance
        or abs(matrix[11]) > tolerance
        or abs(matrix[15] - 1.0) > tolerance
    ):
        raise ValueError(f"{label} must be affine D3D row-vector form")

    a, b, c = matrix[0], matrix[1], matrix[2]
    d, e, f = matrix[4], matrix[5], matrix[6]
    g, h, i = matrix[8], matrix[9], matrix[10]
    determinant = (
        a * (e * i - f * h)
        - b * (d * i - f * g)
        + c * (d * h - e * g)
    )
    if not math.isfinite(determinant) or abs(determinant) <= tolerance:
        raise ValueError(f"{label} affine linear transform is singular")

    inv_det = 1.0 / determinant
    linear_inverse = [
        (e * i - f * h) * inv_det,
        (c * h - b * i) * inv_det,
        (b * f - c * e) * inv_det,
        (f * g - d * i) * inv_det,
        (a * i - c * g) * inv_det,
        (c * d - a * f) * inv_det,
        (d * h - e * g) * inv_det,
        (b * g - a * h) * inv_det,
        (a * e - b * d) * inv_det,
    ]
    tx, ty, tz = matrix[12], matrix[13], matrix[14]
    inverse_translation = [
        -(
            tx * linear_inverse[col]
            + ty * linear_inverse[3 + col]
            + tz * linear_inverse[6 + col]
        )
        for col in range(3)
    ]
    return [
        linear_inverse[0], linear_inverse[1], linear_inverse[2], 0.0,
        linear_inverse[3], linear_inverse[4], linear_inverse[5], 0.0,
        linear_inverse[6], linear_inverse[7], linear_inverse[8], 0.0,
        inverse_translation[0],
        inverse_translation[1],
        inverse_translation[2],
        1.0,
    ]


def solve_root_world_from_selected_slot(
    matrix_records: Sequence[Mapping[str, Any]],
    selected_index: int,
    observed_world_matrix: Sequence[float],
    *,
    tolerance: float = 1.0e-5,
) -> dict[str, Any]:
    """Solve current root world matrix from one observed runtime slot world.

    For a root-connected static mode-1 chain:

        world[selected] = local[selected] * ... * root

    therefore:

        root = inverse(cumulative_local) * observed_world

    The result is accepted only after reevaluating the existing MultiMatrix
    contract and reproducing the observed selected-slot world within tolerance.
    This solves the current root state; it does not reconstruct SceneGraph
    update history.
    """
    records = [
        dict(record)
        for record in matrix_records
        if isinstance(record, Mapping)
    ]
    blockers: list[str] = []
    if len(records) != len(matrix_records):
        blockers.append("multimatrix-root-solve:matrix-record-invalid")
    if not records:
        blockers.append("multimatrix-root-solve:no-matrix-records")

    try:
        selected = int(selected_index)
    except (TypeError, ValueError):
        selected = -1
    if selected < 0 or selected >= len(records):
        blockers.append(
            "multimatrix-root-solve:selected-slot-out-of-range:"
            f"{selected}:count={len(records)}"
        )

    try:
        observed = _as_float_vector(
            observed_world_matrix,
            16,
            "observed_world_matrix",
        )
    except ValueError as exc:
        observed = None
        blockers.append(f"multimatrix-root-solve:{exc}")
    if observed is not None and not all(math.isfinite(item) for item in observed):
        blockers.append(
            "multimatrix-root-solve:observed_world_matrix must contain finite values"
        )

    cumulative = _identity_matrix()
    chain: list[int] = []
    visited: set[int] = set()
    cursor = selected

    if not blockers and selected > 0:
        while cursor != 0:
            if cursor in visited:
                blockers.append(
                    f"multimatrix-root-solve:parent-cycle:{cursor}"
                )
                break
            visited.add(cursor)
            chain.append(cursor)
            record = records[cursor]
            try:
                local = matrix_from_record(record)
            except ValueError as exc:
                blockers.append(
                    f"multimatrix-root-solve:slot-{cursor}:{exc}"
                )
                break
            cumulative = matrix_multiply(cumulative, local)
            try:
                parent = int(record.get("parent")) & 0xFF
            except (TypeError, ValueError):
                blockers.append(
                    f"multimatrix-root-solve:slot-{cursor}:parent-invalid"
                )
                break
            if parent >= len(records):
                blockers.append(
                    f"multimatrix-root-solve:slot-{cursor}:"
                    f"parent-out-of-range:{parent}:count={len(records)}"
                )
                break
            if parent >= cursor and parent != 0:
                blockers.append(
                    f"multimatrix-root-solve:slot-{cursor}:"
                    f"parent-not-earlier:{parent}"
                )
                break
            cursor = parent

    solved_root = None
    inverse_cumulative = None
    evaluation = None
    reproduced = None
    max_abs_error = None

    if not blockers and observed is not None:
        try:
            inverse_cumulative = _affine_inverse(
                cumulative,
                label="cumulative_local",
            )
        except ValueError as exc:
            blockers.append(f"multimatrix-root-solve:{exc}")
        else:
            solved_root = matrix_multiply(
                inverse_cumulative,
                observed,
            )
            evaluation = evaluate_matrix_records(
                records,
                root_world_matrix=solved_root,
            )
            if evaluation.get("ready") is not True:
                blockers.extend(
                    "multimatrix-root-solve:reevaluation:"
                    + str(reason)
                    for reason in evaluation.get("blocking_reasons") or []
                )
            else:
                slots = evaluation.get("slots") or []
                if selected >= len(slots):
                    blockers.append(
                        "multimatrix-root-solve:selected-slot-missing-after-reevaluation"
                    )
                else:
                    reproduced = slots[selected].get("world_matrix")
                    if not isinstance(reproduced, list) or len(reproduced) != 16:
                        blockers.append(
                            "multimatrix-root-solve:reproduced-world-missing"
                        )
                    else:
                        max_abs_error = max(
                            abs(float(reproduced[index]) - observed[index])
                            for index in range(16)
                        )
                        if max_abs_error > tolerance:
                            blockers.append(
                                "multimatrix-root-solve:"
                                f"reevaluation-mismatch:{max_abs_error}"
                            )

    blockers = list(dict.fromkeys(blockers))
    ready = solved_root is not None and not blockers
    return {
        "format": ROOT_SOLVE_FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": blockers,
        "selected_slot": selected,
        "selected_slot_chain_to_root": chain,
        "observed_world_matrix": observed,
        "cumulative_local_matrix": cumulative,
        "inverse_cumulative_local_matrix": inverse_cumulative,
        "solved_root_world_matrix": solved_root,
        "reproduced_selected_world_matrix": reproduced,
        "max_abs_reproduction_error": max_abs_error,
        "tolerance": tolerance,
        "evaluation": evaluation,
        "boundary": {
            "solves_current_root_state": ready,
            "scenegraph_update_history_recovered": False,
            "requires_root_connected_earlier-parent_chain": True,
            "requires_invertible_cumulative_local": True,
            "acceptance": "reevaluate-selected-slot-with-existing-contract",
        },
        "source": {
            "composition": "world[i] = local[i] * world[parent_low_byte]",
            "evaluator": "FUN_006b1620",
            "matrix_multiply": "FUN_00401610/FUN_00401619",
        },
    }


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


def build_multimatrix_root_solve(
    owner_report: Mapping[str, Any],
    selected_index: int,
    observed_world_matrix: Sequence[float],
    *,
    tolerance: float = 1.0e-5,
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
    result = solve_root_world_from_selected_slot(
        owner_report.get("matrix_records") or [],
        selected_index,
        observed_world_matrix,
        tolerance=tolerance,
    )
    result["owner_kind"] = kind
    result["owner_matrix_number"] = owner_report.get(
        "matrix_number"
    )
    return result


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
