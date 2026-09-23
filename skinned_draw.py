"""Renderer-facing contract for skinned SHIFT draw packets."""
from __future__ import annotations

from typing import Any, Iterable

from skinning import build_skinning_contract, validate_influences, _matrix3x4


FORMAT = "SHIFT.SkinnedDraw/1"


def build_skinned_draw_contract(
    packet: dict[str, Any],
    *,
    pose_bones: Iterable[dict[str, Any] | Iterable[float]] | None = None,
    bone_indices: Iterable[Iterable[int]] | None = None,
    bone_weights: Iterable[Iterable[float]] | None = None,
) -> dict[str, Any]:
    mesh = packet.get("mesh") or {}
    skin = mesh.get("skinning") or {}
    reasons: list[str] = []

    if not skin.get("skinned"):
        reasons.append("mesh:not-skinned")
    if skin.get("valid") is False:
        reasons.append("skinning-contract:invalid")

    bones = list(pose_bones or [])
    expected = int(skin.get("bone_count", len(bones)))
    if not bones:
        reasons.append("pose:missing")
    elif len(bones) != expected:
        reasons.append("pose:bone-count-mismatch")
    else:
        for index, bone in enumerate(bones):
            matrix = bone.get("matrix_3x4") if isinstance(bone, dict) else bone
            try:
                _matrix3x4(matrix)
            except (TypeError, ValueError):
                reasons.append(f"pose:invalid-bone-matrix:{index}")

    influence_validation = None
    if bone_indices is not None and bone_weights is not None:
        influence_validation = validate_influences(
            bone_indices, bone_weights, expected
        )
        if not influence_validation["valid"]:
            reasons.append("influences:invalid")

    submeshes = [
        {
            "first_index": sm.get("first_index", 0),
            "index_count": sm.get("index_count", 0),
            "material": sm.get("material"),
        }
        for sm in packet.get("submeshes", []) or []
    ]
    if not submeshes:
        reasons.append("draw:empty")

    return {
        "format": FORMAT,
        "source": packet.get("scene"),
        "node": packet.get("node"),
        "mesh": {
            "ref": mesh.get("ref"),
            "resolved": mesh.get("resolved"),
            "vertex_count": mesh.get("vertex_count"),
            "triangle_count": mesh.get("triangle_count"),
            "skinning": skin,
        },
        "world_matrix": packet.get("world_matrix") or packet.get("matrix"),
        "pose": {
            "bone_count": len(bones),
            "expected_bone_count": expected,
            "available": bool(bones),
            "matrices": [
                list(_matrix3x4(b.get("matrix_3x4") if isinstance(b, dict) else b))
                for b in bones
            ] if bones and len(bones) == expected else [],
        },
        "influence_validation": influence_validation,
        "submeshes": submeshes,
        "ready": not reasons,
        "blocking_reasons": reasons,
    }
