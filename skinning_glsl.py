"""GLES 3.1 skinning contract and reference shader snippets.

This module deliberately stays below the D3D9 translation layer. It describes
the GPU ABI consumed by a validated SHIFT.SkinnedDraw/1 and provides a tiny,
standalone shader used by CI to prove the ABI compiles as OpenGL ES 3.1.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

FORMAT = "SHIFT.GLES31Skinning/1"
DEFAULT_BONE_BINDING = 15
DEFAULT_MAX_BONES = 128


def build_gles31_skinning_contract(
    skinned_draw: dict[str, Any],
    *,
    bone_binding: int = DEFAULT_BONE_BINDING,
    max_bones: int = DEFAULT_MAX_BONES,
) -> dict[str, Any]:
    """Convert a ready SkinnedDraw into an explicit GLES 3.1 palette ABI."""
    if skinned_draw.get("format") != "SHIFT.SkinnedDraw/1":
        raise ValueError("expected SHIFT.SkinnedDraw/1")
    if not skinned_draw.get("ready"):
        reasons = ", ".join(skinned_draw.get("blocking_reasons", []))
        raise ValueError(f"skinned draw is not ready: {reasons}")

    skin = skinned_draw.get("skinning") or {}
    weights = skin.get("weights") or {}
    indices = skin.get("indices") or {}
    layout = (skinned_draw.get("mesh") or {}).get("vertex_layout") or {}

    def layout_location(property_id: str, label: str) -> int:
        matches = [
            a for a in layout.get("attributes", []) or []
            if str(a.get("property_id")) == property_id
        ]
        if len(matches) != 1 or matches[0].get("location") is None:
            raise ValueError(f"missing unique {label} vertex binding")
        location = int(matches[0]["location"])
        return location

    position_location = layout_location("200", "POSITION0")
    weight_location = layout_location("310", "BLENDWEIGHT0")
    index_location = layout_location("580", "BLENDINDICES0")

    for record, location, label in (
        (weights, weight_location, "BLENDWEIGHT0"),
        (indices, index_location, "BLENDINDICES0"),
    ):
        declared = record.get("target_location")
        if declared is not None and int(declared) != location:
            raise ValueError(
                f"{label} location conflicts with SHIFT.VertexLayout/1"
            )
    palette = (skinned_draw.get("bind_skeleton") or {}).get("palette") or {}
    bone_count = int(palette.get("bone_count", 0) or 0)
    pose = skinned_draw.get("skin_pose") or {}
    pose_bone_count = int(pose.get("bone_count", 0) or 0)
    matrices = pose.get("matrices_3x4") or []

    if pose.get("format") != "SHIFT.SkinPose/1":
        raise ValueError("missing SHIFT.SkinPose/1")
    if pose.get("matrix_space") != "skinning":
        raise ValueError("GLES skinning requires matrix_space=skinning")
    if pose_bone_count != bone_count:
        raise ValueError("skin pose bone count does not match bind skeleton")
    if len(matrices) != bone_count or any(len(m) != 12 for m in matrices):
        raise ValueError("skin pose does not contain one complete 3x4 matrix per bone")

    if int(skin.get("influences", 0) or 0) != 4:
        raise ValueError("GLES skinning requires exactly four influences")
    if weights.get("format") != "FLOAT32x4" or weights.get("target_location") is None:
        raise ValueError("missing FLOAT32x4 BLENDWEIGHT0 binding")
    if indices.get("format") != "UINT8x4" or indices.get("target_location") is None:
        raise ValueError("missing UINT8x4 BLENDINDICES0 binding")
    if bone_count <= 0:
        raise ValueError("skinned draw has no bone palette")
    if bone_count > max_bones:
        raise ValueError(f"bone palette {bone_count} exceeds GLES shader limit {max_bones}")
    pose_matrix_blob = json.dumps(
        matrices,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    bind_matrix_rows = list(palette.get("local_matrices_3x4", []) or [])
    bind_matrix_blob = json.dumps(
        bind_matrix_rows,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return {
        "format": FORMAT,
        "api": "OpenGL ES 3.1",
        "ready": True,
        "bone_binding": bone_binding,
        "max_bones": max_bones,
        "bone_count": bone_count,
        "skin_pose": {
            "format": "SHIFT.SkinPose/1",
            "matrix_space": "skinning",
            "matrix_layout": "3x4-row-major",
            "bone_count": pose_bone_count,
            "matrices_sha256": hashlib.sha256(pose_matrix_blob).hexdigest(),
            "source": pose.get("source"),
            "frame": pose.get("frame"),
        },
        "bind_skeleton": {
            "format": "SHIFT.BindSkeleton/1",
            "bone_count": bone_count,
            "matrix_layout": palette.get("matrix_layout"),
            "matrix_space": palette.get("matrix_space"),
            "matrices_sha256": hashlib.sha256(bind_matrix_blob).hexdigest(),
        },
        "palette": {
            "storage": "std140-uniform-mat4-array",
            "matrix_source": "SHIFT.SkinPose/1",
            "matrix_layout": "row-major-3x4-expanded-to-4x4",
            "array_name": "u_bones",
        },
        "attributes": {
            "position": {
                "location": position_location,
                "glsl_type": "vec3",
            },
            "blendweight0": {
                "location": weight_location,
                "glsl_type": "vec4",
                "source_format": "FLOAT32x4",
            },
            "blendindices0": {
                "location": index_location,
                "glsl_type": "uvec4",
                "source_format": "UINT8x4",
                "integer_attribute": True,
            },
        },
        "influences": 4,
    }



def build_gles31_skinning_contract_from_render_command(
    command: dict[str, Any],
    *,
    bone_binding: int = DEFAULT_BONE_BINDING,
    max_bones: int = DEFAULT_MAX_BONES,
) -> dict[str, Any]:
    """Build the GLES 3.1 skinning ABI directly from RenderCommand/1."""
    if command.get("format") != "SHIFT.RenderCommand/1":
        raise ValueError("expected SHIFT.RenderCommand/1")
    if command.get("draw_kind") != "skinned":
        raise ValueError("RenderCommand is not a skinned draw")
    if not command.get("ready"):
        raise ValueError(
            "render command is not ready: "
            + ", ".join(command.get("blocking_reasons", []) or [])
        )

    skin = command.get("skinning") or {}
    pose = skin.get("skin_pose") or {}
    palette = skin.get("bind_skeleton") or {}
    mesh = command.get("mesh") or {}

    if skin.get("format") != "SHIFT.Skinning/1":
        raise ValueError("RenderCommand is missing SHIFT.Skinning/1")
    attributes = mesh.get("attributes") or []
    normalized_layout = {
        "format": "SHIFT.VertexLayout/1",
        "attributes": attributes,
    }
    skinned_draw = {
        "format": "SHIFT.SkinnedDraw/1",
        "ready": True,
        "blocking_reasons": [],
        "mesh": {
            "vertex_layout": normalized_layout,
            "skinning": {
                "influences": int(skin.get("influences", 0) or 0),
                "weights": skin.get("weights") or {},
                "indices": skin.get("indices") or {},
            },
        },
        "skinning": skin,
        "bind_skeleton": {
            "format": "SHIFT.BindSkeleton/1",
            "coverage": 1.0,
            "bone_count": int(palette.get("bone_count", 0) or 0),
            "palette": {
                "format": palette.get("format", "SHIFT.BonePalette/1"),
                "bone_count": int(palette.get("bone_count", 0) or 0),
                "matrices_3x4": list(palette.get("local_matrices_3x4", []) or []),
                "matrix_layout": palette.get("matrix_layout"),
                "matrix_space": palette.get("matrix_space"),
            },
        },
        "skin_pose": pose,
    }
    return build_gles31_skinning_contract(
        skinned_draw,
        bone_binding=bone_binding,
        max_bones=max_bones,
    )

def validate_gles31_skinning_contract_parity(
    command: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    """Cross-check the GLES skinning contract against its RenderCommand source."""
    checks: list[dict[str, Any]] = []
    blockers: list[str] = []

    def check(name: str, expected: Any, actual: Any, reason: str) -> None:
        status = "match" if expected == actual else "mismatch"
        checks.append({
            "name": name,
            "status": status,
            "render_command": expected,
            "gles_contract": actual,
        })
        if status != "match":
            blockers.append(reason)

    if command.get("format") != "SHIFT.RenderCommand/1":
        blockers.append("parity:render-command-invalid-format")
    if command.get("draw_kind") != "skinned":
        blockers.append("parity:render-command-not-skinned")
    skin = command.get("skinning") or {}
    if skin.get("format") != "SHIFT.Skinning/1":
        blockers.append("parity:skinning-invalid-format")
    if not command.get("ready"):
        blockers.append("parity:render-command-not-ready")
    blockers.extend(
        f"parity:source-blocker:{reason}"
        for reason in command.get("blocking_reasons", []) or []
    )

    if contract.get("format") != FORMAT:
        blockers.append("parity:gles-contract-invalid-format")
    if contract.get("api") != "OpenGL ES 3.1":
        blockers.append("parity:gles-api-invalid")
    if contract.get("ready") is not True:
        blockers.append("parity:gles-contract-not-ready")

    attributes = (command.get("mesh") or {}).get("attributes") or []

    def location_for(property_id: str) -> Any:
        rows = [
            row.get("location")
            for row in attributes
            if str(row.get("property_id")) == property_id
        ]
        return rows[0] if len(rows) == 1 else None

    contract_attrs = contract.get("attributes") or {}
    check(
        "position-location",
        location_for("200"),
        (contract_attrs.get("position") or {}).get("location"),
        "parity:position-location-mismatch",
    )
    check(
        "blendweight0-location",
        (skin.get("weights") or {}).get("target_location"),
        (contract_attrs.get("blendweight0") or {}).get("location"),
        "parity:blendweight0-location-mismatch",
    )
    check(
        "blendindices0-location",
        (skin.get("indices") or {}).get("target_location"),
        (contract_attrs.get("blendindices0") or {}).get("location"),
        "parity:blendindices0-location-mismatch",
    )
    check(
        "blendweight0-format",
        (skin.get("weights") or {}).get("format"),
        (contract_attrs.get("blendweight0") or {}).get("source_format"),
        "parity:blendweight0-format-mismatch",
    )
    check(
        "blendindices0-format",
        (skin.get("indices") or {}).get("format"),
        (contract_attrs.get("blendindices0") or {}).get("source_format"),
        "parity:blendindices0-format-mismatch",
    )
    check(
        "influences",
        int(skin.get("influences", 0) or 0),
        contract.get("influences"),
        "parity:influence-count-mismatch",
    )

    pose = skin.get("skin_pose") or {}
    contract_pose = contract.get("skin_pose") or {}
    check(
        "skin-pose-format",
        pose.get("format"),
        contract_pose.get("format"),
        "parity:skin-pose-format-mismatch",
    )
    check(
        "skin-pose-space",
        pose.get("matrix_space"),
        contract_pose.get("matrix_space"),
        "parity:skin-pose-space-mismatch",
    )
    check(
        "skin-pose-layout",
        pose.get("matrix_layout", "3x4-row-major"),
        contract_pose.get("matrix_layout"),
        "parity:skin-pose-layout-mismatch",
    )
    pose_bone_count = int(pose.get("bone_count", 0) or 0)
    pose_blob = json.dumps(
        pose.get("matrices_3x4") or [],
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    check(
        "skin-pose-bone-count",
        pose_bone_count,
        contract_pose.get("bone_count"),
        "parity:skin-pose-bone-count-mismatch",
    )
    check(
        "skin-pose-matrices",
        hashlib.sha256(pose_blob).hexdigest(),
        contract_pose.get("matrices_sha256"),
        "parity:skin-pose-matrices-mismatch",
    )

    source_palette = skin.get("bind_skeleton") or {}
    contract_palette = contract.get("bind_skeleton") or {}
    check(
        "bind-bone-count",
        int(source_palette.get("bone_count", 0) or 0),
        int(contract_palette.get("bone_count", 0) or 0),
        "parity:bind-bone-count-mismatch",
    )
    check(
        "bind-matrix-layout",
        source_palette.get("matrix_layout"),
        contract_palette.get("matrix_layout"),
        "parity:bind-matrix-layout-mismatch",
    )
    check(
        "bind-matrix-space",
        source_palette.get("matrix_space"),
        contract_palette.get("matrix_space"),
        "parity:bind-matrix-space-mismatch",
    )
    bind_blob = json.dumps(
        source_palette.get("local_matrices_3x4") or [],
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    check(
        "bind-matrices",
        hashlib.sha256(bind_blob).hexdigest(),
        contract_palette.get("matrices_sha256"),
        "parity:bind-matrices-mismatch",
    )

    return {
        "format": "SHIFT.GLES31SkinningParity/1",
        "valid": not blockers,
        "checks": checks,
        "blocking_reasons": list(dict.fromkeys(blockers)),
    }


def gles31_skinning_functions(*, bone_binding: int = DEFAULT_BONE_BINDING,
                               max_bones: int = DEFAULT_MAX_BONES) -> str:
    """Return reusable GLSL ES 3.1 linear-blend skinning functions."""
    if not 0 <= bone_binding <= 31:
        raise ValueError("uniform block binding must fit the GLES implementation range")
    if max_bones <= 0:
        raise ValueError("max_bones must be positive")
    return f"""layout(std140, binding = {bone_binding}) uniform ShiftBonePalette {{
    mat4 u_bones[{max_bones}];
}};

vec4 shift_skin_position(
    vec3 position,
    vec4 weights,
    uvec4 indices
) {{
    vec4 p = vec4(position, 1.0);
    return
        (u_bones[indices.x] * p) * weights.x +
        (u_bones[indices.y] * p) * weights.y +
        (u_bones[indices.z] * p) * weights.z +
        (u_bones[indices.w] * p) * weights.w;
}}

vec3 shift_skin_direction(
    vec3 direction,
    vec4 weights,
    uvec4 indices
) {{
    vec4 d = vec4(direction, 0.0);
    vec3 result =
        (u_bones[indices.x] * d).xyz * weights.x +
        (u_bones[indices.y] * d).xyz * weights.y +
        (u_bones[indices.z] * d).xyz * weights.z +
        (u_bones[indices.w] * d).xyz * weights.w;
    return normalize(result);
}}
"""


def build_gles31_skinning_test_shader(
    *,
    bone_binding: int = DEFAULT_BONE_BINDING,
    max_bones: int = DEFAULT_MAX_BONES,
) -> str:
    """Build a complete minimal GLES 3.1 vertex shader for compiler validation."""
    return f"""#version 310 es
precision highp float;
precision highp int;

layout(location = 0) in vec3 a_position;
layout(location = 1) in vec4 a_blendweights;
layout(location = 2) in uvec4 a_blendindices;
uniform mat4 u_mvp;

{gles31_skinning_functions(bone_binding=bone_binding, max_bones=max_bones)}

void main() {{
    vec4 skinned = shift_skin_position(
        a_position,
        a_blendweights,
        a_blendindices
    );
    gl_Position = u_mvp * skinned;
}}
"""


def palette_uniform_bytes(bone_count: int) -> int:
    """Return std140 byte size for the expanded mat4 palette."""
    if bone_count < 0:
        raise ValueError("bone_count must be non-negative")
    return bone_count * 64
