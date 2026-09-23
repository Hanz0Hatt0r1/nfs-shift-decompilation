"""GLES 3.1 skinning contract and reference shader snippets.

This module deliberately stays below the D3D9 translation layer. It describes
the GPU ABI consumed by a validated SHIFT.SkinnedDraw/1 and provides a tiny,
standalone shader used by CI to prove the ABI compiles as OpenGL ES 3.1.
"""
from __future__ import annotations

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
    matrices = palette.get("matrices_3x4") or []
    if len(matrices) != bone_count or any(len(m) != 12 for m in matrices):
        raise ValueError("bone palette does not contain one complete 3x4 matrix per bone")

    return {
        "format": FORMAT,
        "api": "OpenGL ES 3.1",
        "bone_binding": bone_binding,
        "max_bones": max_bones,
        "bone_count": bone_count,
        "palette": {
            "storage": "std140-uniform-mat4-array",
            "matrix_source": "SHIFT.BonePalette/1",
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
