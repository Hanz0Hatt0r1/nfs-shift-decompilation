"""Validate a SHIFT skinned draw for the Android-neutral renderer.

The contract is intentionally strict: a render-ready skinned draw must carry
explicit weight/index attributes, a complete bind skeleton, and an unambiguous
shader selection. No bone or attribute inference is performed here.
"""
from __future__ import annotations

from typing import Any


FORMAT = "SHIFT.SkinnedDraw/1"
MAX_INFLUENCES = 4


def _layout_attributes(mesh: dict[str, Any]) -> list[dict[str, Any]]:
    return list((mesh.get("vertex_layout") or {}).get("attributes", []) or [])


def _find_attribute(attrs: list[dict[str, Any]], property_id: str) -> dict[str, Any] | None:
    matches = [a for a in attrs if str(a.get("property_id")) == property_id]
    if len(matches) != 1:
        return None
    return matches[0]


def _validate_skin_attributes(mesh: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    attrs = _layout_attributes(mesh)
    reasons: list[str] = []

    weights = _find_attribute(attrs, "310")
    indices = _find_attribute(attrs, "580")

    if weights is None:
        reasons.append("skinning-attribute:BLENDWEIGHT-missing-or-ambiguous")
    if indices is None:
        reasons.append("skinning-attribute:BLENDINDICES-missing-or-ambiguous")

    if weights is not None:
        if weights.get("android") != "FLOAT32x4" or weights.get("components") != 4:
            reasons.append("skinning-attribute:BLENDWEIGHT-format")
        if weights.get("normalized") is not False:
            reasons.append("skinning-attribute:BLENDWEIGHT-normalization")
    if indices is not None:
        if indices.get("android") != "UINT8x4" or indices.get("components") != 4:
            reasons.append("skinning-attribute:BLENDINDICES-format")
        if indices.get("normalized") is not False:
            reasons.append("skinning-attribute:BLENDINDICES-normalization")

    contract = {
        "influences": MAX_INFLUENCES,
        "weights": {
            "property_id": "310",
            "usage": "BLENDWEIGHT",
            "usage_index": 0,
            "format": "FLOAT32x4",
            "normalized": False,
            "target_location": weights.get("location") if weights else None,
        },
        "indices": {
            "property_id": "580",
            "usage": "BLENDINDICES",
            "usage_index": 0,
            "format": "UINT8x4",
            "normalized": False,
            "target_location": indices.get("location") if indices else None,
        },
        "valid": not reasons,
    }
    return contract, reasons


def _validate_bind_skeleton(packet: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    mesh = packet.get("mesh") or {}
    skeleton = packet.get("bind_skeleton") or mesh.get("bind_skeleton")
    reasons: list[str] = []

    if not isinstance(skeleton, dict):
        return None, ["bind-skeleton:missing"]

    if skeleton.get("format") != "SHIFT.BindSkeleton/1":
        reasons.append("bind-skeleton:wrong-format")

    coverage = skeleton.get("coverage")
    if coverage is None:
        reasons.append("bind-skeleton:coverage-missing")
    else:
        try:
            if float(coverage) < 1.0:
                reasons.append("bind-skeleton:coverage-incomplete")
        except (TypeError, ValueError):
            reasons.append("bind-skeleton:coverage-invalid")

    bone_count = int(skeleton.get("bone_count", 0) or 0)
    if bone_count <= 0:
        reasons.append("bind-skeleton:bone-count-missing")

    links = list(skeleton.get("links", []) or [])
    if len(links) != bone_count:
        reasons.append("bind-skeleton:link-count-mismatch")

    matrices: list[list[float]] = []
    for link in links:
        matrix = link.get("local_matrix_3x4")
        if not isinstance(matrix, list) or len(matrix) != 12:
            reasons.append(f"bind-skeleton:matrix-missing:{link.get('index')}")
            continue
        matrices.append([float(x) for x in matrix])

    if len(matrices) != bone_count:
        reasons.append("bind-skeleton:palette-incomplete")

    payload = skeleton.get("animation_payload") or {}
    palette = {
        "format": "SHIFT.BindLocalPalette/1",
        "source": "SHIFT.BindSkeleton/1",
        "matrix_space": "local-bind",
        "matrix_layout": "3x4-row-major",
        "bone_count": bone_count,
        "local_matrices_3x4": matrices,
        "animation_payload": {
            "offset": payload.get("offset"),
            "size": payload.get("size"),
            "sha256": payload.get("sha256"),
            "decoded": bool(payload.get("decoded", False)),
        },
    }
    return palette, reasons


def _validate_skin_pose(
    packet: dict[str, Any],
    bone_count: int,
) -> tuple[dict[str, Any] | None, list[str]]:
    pose = packet.get("skin_pose")
    reasons: list[str] = []
    if not isinstance(pose, dict):
        return None, ["skin-pose:missing"]

    if pose.get("format") != "SHIFT.SkinPose/1":
        reasons.append("skin-pose:wrong-format")
    if pose.get("matrix_space") != "skinning":
        reasons.append("skin-pose:wrong-matrix-space")

    pose_bone_count = int(pose.get("bone_count", 0) or 0)
    if pose_bone_count != bone_count:
        reasons.append("skin-pose:bone-count-mismatch")

    matrices = list(pose.get("matrices_3x4", []) or [])
    if len(matrices) != bone_count:
        reasons.append("skin-pose:palette-incomplete")
    normalized: list[list[float]] = []
    for index, matrix in enumerate(matrices):
        if not isinstance(matrix, list) or len(matrix) != 12:
            reasons.append(f"skin-pose:matrix-invalid:{index}")
            continue
        normalized.append([float(x) for x in matrix])

    result = {
        "format": "SHIFT.SkinPose/1",
        "matrix_space": "skinning",
        "matrix_layout": "3x4-row-major",
        "bone_count": pose_bone_count,
        "matrices_3x4": normalized,
        "source": pose.get("source"),
        "frame": pose.get("frame"),
    }
    return result, list(dict.fromkeys(reasons))


def _validate_shader_selection(packet: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    selection = packet.get("shader_selection") or {}

    if selection.get("status") != "unique":
        reasons.append(f"shader-selection:{selection.get('status', 'none')}")

    for submesh in packet.get("submeshes", []) or []:
        material = submesh.get("material") or {}
        selected = material.get("shader_selection") or {}
        status = selected.get("status", "none")
        if status != "unique":
            reasons.append(f"material-shader-selection:{status}")
            continue
        pair = selected.get("shader_pair") or {}
        if pair.get("selection_status", "none") != "unique":
            reasons.append(
                f"material-shader-pair-selection:{pair.get('selection_status', 'none')}"
            )
        if pair.get("interface", {}).get("valid") is False:
            reasons.append("material-shader-interface:invalid")
        vertex_format = pair.get("vertex_format") or {}
        if vertex_format.get("valid") is False:
            reasons.append("material-vertex-format:invalid")

        for tex in material.get("textures", []) or []:
            if (
                tex.get("binding_source") != "fxo-ctab"
                or tex.get("d3d9_sampler_register") is None
            ):
                reasons.append(
                    f"material-texture-binding:unresolved:{tex.get('ref')}"
                )

    return list(dict.fromkeys(reasons))


def build_skinned_draw_contract(packet: dict[str, Any]) -> dict[str, Any]:
    """Build the renderer-facing contract for one skinned DrawPacket."""
    mesh = packet.get("mesh") or {}
    reasons: list[str] = []

    layout = mesh.get("vertex_layout") or {}
    if layout.get("format") != "SHIFT.VertexLayout/1":
        reasons.append("vertex-layout:missing")
    if int(layout.get("buffer_stride", 0) or 0) <= 0:
        reasons.append("vertex-layout:stride-missing")

    attrs_contract, attr_reasons = _validate_skin_attributes(mesh)
    reasons.extend(attr_reasons)

    summary = mesh.get("skinning")
    if summary is None:
        summary = {
            "has_weights": not any(
                "BLENDWEIGHT" in reason for reason in attr_reasons
            ),
            "has_indices": not any(
                "BLENDINDICES" in reason for reason in attr_reasons
            ),
            "skinned": not attr_reasons,
            "valid": not attr_reasons,
            "source": "vertex-layout",
        }
    if summary.get("valid") is False:
        reasons.append("mesh-skinning-summary:invalid")
    if summary.get("skinned") is not True:
        reasons.append("mesh-skinning-summary:not-skinned")

    palette, skeleton_reasons = _validate_bind_skeleton(packet)
    reasons.extend(skeleton_reasons)

    bone_count = palette["bone_count"] if palette else 0
    if palette and bone_count > 0:
        palette["index_range"] = [0, bone_count - 1]

    skin_pose, pose_reasons = _validate_skin_pose(packet, bone_count)
    reasons.extend(pose_reasons)

    reasons.extend(_validate_shader_selection(packet))

    external_samplers: list[dict[str, Any]] = []
    for submesh in packet.get("submeshes", []) or []:
        selection = ((submesh.get("material") or {}).get("shader_selection") or {})
        external_samplers.extend(selection.get("external_samplers", []) or [])

    return {
        "format": FORMAT,
        "ready": not reasons,
        "blocking_reasons": list(dict.fromkeys(reasons)),
        "mesh": {
            "ref": mesh.get("ref"),
            "vertex_count": mesh.get("vertex_count"),
            "triangle_count": mesh.get("triangle_count"),
            "vertex_layout": layout,
            "skinning": summary,
        },
        "skinning": attrs_contract,
        "bind_skeleton": {
            "format": "SHIFT.BindSkeleton/1",
            "coverage": (
                (packet.get("bind_skeleton") or mesh.get("bind_skeleton") or {}).get(
                    "coverage"
                )
            ),
            "bone_count": bone_count,
            "palette": palette,
        },
        "skin_pose": skin_pose,
        "shader_selection": packet.get("shader_selection"),
        "submeshes": packet.get("submeshes", []),
        "external_samplers": external_samplers,
    }
