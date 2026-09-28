"""Platform-neutral reference skinning for SHIFT MEB meshes.

The MEB format supplies four float weights (property 310) and four byte bone
indices (property 580). This module does not infer animation-keyframe formats;
it consumes a resolved skeleton pose and provides a deterministic CPU reference
implementation that the future Android renderer can cross-check.
"""
from __future__ import annotations

from typing import Any, Iterable


FORMAT = "SHIFT.Skinning/1"


def _matrix3x4(matrix: Iterable[float]) -> tuple[float, ...]:
    vals = tuple(float(x) for x in matrix)
    if len(vals) == 12:
        return vals
    if len(vals) == 16:
        return (
            vals[0], vals[1], vals[2], vals[3],
            vals[4], vals[5], vals[6], vals[7],
            vals[8], vals[9], vals[10], vals[11],
        )
    raise ValueError("bone matrix must contain 12 or 16 floats")


def _transform_point(m: tuple[float, ...], p: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = p
    return (
        m[0] * x + m[1] * y + m[2] * z + m[3],
        m[4] * x + m[5] * y + m[6] * z + m[7],
        m[8] * x + m[9] * y + m[10] * z + m[11],
    )


def _transform_direction(m: tuple[float, ...], v: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = v
    return (
        m[0] * x + m[1] * y + m[2] * z,
        m[4] * x + m[5] * y + m[6] * z,
        m[8] * x + m[9] * y + m[10] * z,
    )


def _normalize3(v: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = v
    n = (x * x + y * y + z * z) ** 0.5
    if n <= 1.0e-12:
        return (0.0, 0.0, 0.0)
    return (x / n, y / n, z / n)


def build_skinning_contract(
    vertex_properties: Iterable[str | dict],
    skeleton: dict[str, Any] | None,
    *,
    strict_indices: bool = True,
) -> dict[str, Any]:
    props = {
        str(x.get("id")) if isinstance(x, dict) else str(x)
        for x in vertex_properties
    }
    has_weights = "310" in props
    has_indices = "580" in props
    contract = {
        "format": FORMAT,
        "has_weights": has_weights,
        "has_indices": has_indices,
        "skinned": has_weights and has_indices,
        "valid": has_weights == has_indices,
        "strict_indices": strict_indices,
    }
    if not contract["valid"]:
        contract["error"] = "weights_without_indices" if has_weights else "indices_without_weights"
        return contract
    if not contract["skinned"]:
        return contract

    bones = list((skeleton or {}).get("bones", []) or [])
    bone_count = int((skeleton or {}).get("num_bones", len(bones)))
    contract["bone_count"] = bone_count
    contract["bone_records"] = len(bones)
    contract["weights_storage"] = "FLOAT32x4"
    contract["indices_storage"] = "UINT8x4"
    contract["influence_count"] = 4
    if skeleton is None:
        contract["valid"] = False
        contract["error"] = "skeleton_missing"
        return contract
    if len(bones) != bone_count:
        contract["valid"] = False
        contract["error"] = "skeleton_bone_count_mismatch"
        return contract
    if strict_indices:
        contract["index_range"] = [0, max(0, bone_count - 1)]
    return contract


def validate_influences(
    bone_indices: Iterable[Iterable[int]],
    bone_weights: Iterable[Iterable[float]],
    bone_count: int,
    *,
    strict_indices: bool = True,
    tolerance: float = 1.0e-5,
) -> dict[str, Any]:
    indices = [tuple(int(x) for x in row) for row in bone_indices]
    weights = [tuple(float(x) for x in row) for row in bone_weights]
    issues: list[dict[str, Any]] = []
    if len(indices) != len(weights):
        return {
            "valid": False,
            "vertex_count": min(len(indices), len(weights)),
            "issues": [{"kind": "count-mismatch", "indices": len(indices), "weights": len(weights)}],
        }
    for vi, (ids, ws) in enumerate(zip(indices, weights)):
        if len(ids) != 4 or len(ws) != 4:
            issues.append({"vertex": vi, "kind": "influence-width", "indices": len(ids), "weights": len(ws)})
            continue
        total = sum(ws)
        if abs(total - 1.0) > tolerance and total > tolerance:
            issues.append({"vertex": vi, "kind": "weights-not-normalized", "sum": total})
        for slot, idx in enumerate(ids):
            if idx < 0 or idx >= bone_count:
                issues.append({"vertex": vi, "kind": "bone-index-out-of-range", "slot": slot, "index": idx})
    if strict_indices:
        valid = not any(i["kind"] == "bone-index-out-of-range" for i in issues)
    else:
        valid = True
    return {
        "valid": valid,
        "vertex_count": len(indices),
        "issues": issues,
        "strict_indices": strict_indices,
    }


def skin_points(
    positions: Iterable[Iterable[float]],
    bone_indices: Iterable[Iterable[int]],
    bone_weights: Iterable[Iterable[float]],
    bones: Iterable[dict[str, Any] | Iterable[float]],
    *,
    normalize_weights: bool = False,
    strict_indices: bool = True,
) -> list[tuple[float, float, float]]:
    pos = [tuple(float(x) for x in p) for p in positions]
    ids = [tuple(int(x) for x in row) for row in bone_indices]
    weights = [tuple(float(x) for x in row) for row in bone_weights]
    bone_mats: list[tuple[float, ...]] = []
    for bone in bones:
        source = bone.get("matrix_3x4") if isinstance(bone, dict) else bone
        if source is None:
            raise ValueError("bone record has no matrix_3x4")
        bone_mats.append(_matrix3x4(source))

    if len(pos) != len(ids) or len(pos) != len(weights):
        raise ValueError("positions, bone_indices and bone_weights must have equal length")
    result: list[tuple[float, float, float]] = []
    for vi, (p, row_ids, row_weights) in enumerate(zip(pos, ids, weights)):
        total = sum(row_weights)
        norm = 1.0 / total if normalize_weights and abs(total) > 1.0e-12 else 1.0
        out = [0.0, 0.0, 0.0]
        for slot, (bone_id, weight) in enumerate(zip(row_ids, row_weights)):
            if abs(weight) <= 1.0e-12:
                continue
            if bone_id < 0 or bone_id >= len(bone_mats):
                if strict_indices:
                    raise ValueError(f"vertex {vi} influence {slot} references bone {bone_id}, count={len(bone_mats)}")
                continue
            tp = _transform_point(bone_mats[bone_id], p)
            factor = weight * norm
            out[0] += tp[0] * factor
            out[1] += tp[1] * factor
            out[2] += tp[2] * factor
        result.append(tuple(out))
    return result


def skin_directions(
    vectors: Iterable[Iterable[float]],
    bone_indices: Iterable[Iterable[int]],
    bone_weights: Iterable[Iterable[float]],
    bones: Iterable[dict[str, Any] | Iterable[float]],
    *,
    normalize_weights: bool = False,
    strict_indices: bool = True,
) -> list[tuple[float, float, float]]:
    vec = [tuple(float(x) for x in v) for v in vectors]
    ids = [tuple(int(x) for x in row) for row in bone_indices]
    weights = [tuple(float(x) for x in row) for row in bone_weights]
    bone_mats = [
        _matrix3x4(b.get("matrix_3x4") if isinstance(b, dict) else b)
        for b in bones
    ]
    if len(vec) != len(ids) or len(vec) != len(weights):
        raise ValueError("vectors, bone_indices and bone_weights must have equal length")
    result = []
    for vi, (v, row_ids, row_weights) in enumerate(zip(vec, ids, weights)):
        total = sum(row_weights)
        norm = 1.0 / total if normalize_weights and abs(total) > 1.0e-12 else 1.0
        out = [0.0, 0.0, 0.0]
        for slot, (bone_id, weight) in enumerate(zip(row_ids, row_weights)):
            if abs(weight) <= 1.0e-12:
                continue
            if bone_id < 0 or bone_id >= len(bone_mats):
                if strict_indices:
                    raise ValueError(f"vertex {vi} influence {slot} references bone {bone_id}, count={len(bone_mats)}")
                continue
            tv = _transform_direction(bone_mats[bone_id], v)
            factor = weight * norm
            out[0] += tv[0] * factor
            out[1] += tv[1] * factor
            out[2] += tv[2] * factor
        result.append(_normalize3(tuple(out)))
    return result
