"""Validate a SHIFT DrawPacket for the first static GPU renderer path.

This layer intentionally does not issue GL calls. It converts the recovered
DrawPacket evidence into a small, explicit renderer contract and reports
blocking gaps instead of guessing.
"""
from __future__ import annotations

from typing import Any

from texture_pipeline import build_texture_contract


FORMAT = "SHIFT.StaticDraw/1"


def _material_contract(material: dict[str, Any] | None) -> dict[str, Any]:
    material = material or {}
    selection = material.get("shader_selection") or {}
    status = selection.get("status", "none")
    reasons: list[str] = []

    if status != "unique":
        reasons.append(f"shader-selection:{status}")

    pair = selection.get("shader_pair") or {}
    if not pair:
        reasons.append("shader-pair:missing")
    else:
        pair_status = pair.get("selection_status", "none")
        if pair_status != "unique":
            reasons.append(f"shader-pair-selection:{pair_status}")
        if pair.get("interface", {}).get("valid") is False:
            reasons.append("shader-interface:invalid")
        if pair.get("vertex_format", {}).get("valid") is False:
            reasons.append("vertex-format:invalid")

    linked_pair = selection.get("linked_shader_pair")
    if not linked_pair:
        reasons.append("shader-glsl:missing")
    elif linked_pair.get("format") != "SHIFT.LinkedShaderPair/1":
        reasons.append("shader-glsl:invalid")
    if selection.get("linked_shader_error"):
        reasons.append("shader-glsl:error")

    explicit_textures = []
    unresolved_textures = []
    for tex in material.get("textures", []) or []:
        item = {
            "material_parameter": tex.get("material_parameter"),
            "ref": tex.get("ref"),
            "slot": tex.get("slot"),
            "sampler": tex.get("sampler"),
            "sampler_type": tex.get("sampler_type"),
            "binding_source": tex.get("binding_source"),
            "resolved": tex.get("resolved", []),
            "dds": tex.get("dds"),
        }
        if tex.get("binding_source") == "fxo-ctab" and tex.get("d3d9_sampler_register") is not None:
            if tex.get("dds"):
                item["texture_resource"] = build_texture_contract(tex["dds"], tex)
            explicit_textures.append(item)
        else:
            unresolved_textures.append(item)

    uniforms = selection.get("uniform_binding") or {}
    external_samplers = selection.get("external_samplers") or []

    texture_blockers = [
        f"texture:{reason}"
        for tex in explicit_textures
        for reason in (tex.get("texture_resource", {}) or {}).get("blocking_reasons", [])
    ]

    return {
        "format": FORMAT,
        "material": material.get("name"),
        "shader_selection": selection,
        "textures": explicit_textures,
        "unresolved_textures": unresolved_textures,
        "external_samplers": external_samplers,
        "uniform_binding": uniforms,
        "ready": not reasons and not unresolved_textures and not texture_blockers,
        "blocking_reasons": (
            reasons
            + (["material-texture-binding:unresolved"] if unresolved_textures else [])
            + texture_blockers
        ),
    }


def build_static_draw_contract(packet: dict[str, Any]) -> dict[str, Any]:
    """Build the renderer-facing contract for one DrawPacket."""
    mesh = packet.get("mesh") or {}
    layout = mesh.get("vertex_layout") or {}
    reasons: list[str] = []

    if layout.get("format") != "SHIFT.VertexLayout/1":
        reasons.append("vertex-layout:missing")
    if layout.get("buffer_stride", 0) <= 0:
        reasons.append("vertex-layout:stride-missing")
    attributes = layout.get("attributes", []) or []
    if any(a.get("status") == "unknown" or a.get("abi_status") == "unknown" for a in attributes):
        reasons.append("vertex-layout:unknown-attribute")

    # Ambiguous ABI is blocking only when the selected shader consumes it.
    # This prevents a silent RGBA/BGRA or D3D9 declaration choice.
    used_properties: set[str] = set()
    for submesh in packet.get("submeshes", []) or []:
        material = submesh.get("material") or {}
        pair = (material.get("shader_selection") or {}).get("shader_pair") or {}
        selected_bindings = pair.get("vertex_bindings") or pair.get("vertex_format", {}).get("vertex_bindings") or []
        used_properties.update(
            str(x.get("property_id"))
            for x in selected_bindings
            if x.get("matched") and x.get("property_id") is not None
        )
    ambiguous_used = [
        str(a.get("property_id"))
        for a in attributes
        if a.get("abi_status") == "ambiguous"
        and str(a.get("property_id")) in used_properties
    ]
    if ambiguous_used:
        reasons.append("vertex-layout:ambiguous-attribute:" + ",".join(sorted(set(ambiguous_used))))

    submeshes = []
    material_ready = True
    material_reasons: list[str] = []
    for submesh in packet.get("submeshes", []) or []:
        contract = _material_contract(submesh.get("material"))
        material_ready = material_ready and contract["ready"]
        material_reasons.extend(contract.get("blocking_reasons", []))
        submeshes.append({
            "first_index": submesh.get("first_index", 0),
            "index_count": submesh.get("index_count", 0),
            "material": contract,
        })

    if not submeshes:
        reasons.append("draw:empty")
    if packet.get("mesh", {}).get("vertex_count") is None:
        reasons.append("mesh:vertex-count-missing")
    if not material_ready:
        reasons.extend(dict.fromkeys(material_reasons))
        reasons.append("material:binding-not-ready")

    return {
        "format": FORMAT,
        "source": packet.get("scene"),
        "node": packet.get("node"),
        "mesh": {
            "ref": mesh.get("ref"),
            "resolved": mesh.get("resolved"),
            "vertex_count": mesh.get("vertex_count"),
            "triangle_count": mesh.get("triangle_count"),
            "vertex_layout": layout,
        },
        "world_matrix": packet.get("world_matrix") or packet.get("matrix"),
        "submeshes": submeshes,
        "ready": not reasons,
        "blocking_reasons": reasons,
    }
