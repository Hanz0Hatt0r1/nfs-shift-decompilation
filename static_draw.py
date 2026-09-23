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
    selection = material.get("shader_selection") or material
    status = selection.get("status") or selection.get("selection_status", "none")
    reasons: list[str] = []

    if status != "unique":
        reasons.append(f"shader-selection:{status}")

    pair = selection.get("shader_pair") or material.get("shader_pair") or {}
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

    linked_pair = selection.get("linked_shader_pair") or material.get("linked_shader_pair")
    if not linked_pair:
        reasons.append("shader-glsl:missing")
    elif linked_pair.get("format") != "SHIFT.LinkedShaderPair/1":
        reasons.append("shader-glsl:invalid")
    if selection.get("linked_shader_error") or material.get("linked_shader_error"):
        reasons.append("shader-glsl:error")

    explicit_textures = []
    unresolved_textures = []
    for tex in (material.get("textures", []) or material.get("bindings", []) or []):
        binding_source = tex.get("binding_source") or tex.get("binding")
        item = {
            "material_parameter": tex.get("material_parameter"),
            "ref": tex.get("ref") or tex.get("texture"),
            "slot": tex.get("slot"),
            "sampler": tex.get("sampler"),
            "sampler_type": tex.get("sampler_type"),
            "binding_source": binding_source,
            "resolved": tex.get("resolved", []) or ([{"path": tex.get("texture_resolved")} ] if tex.get("texture_resolved") else []),
            "dds": tex.get("dds"),
        }
        if binding_source == "fxo-ctab" or tex.get("binding") == "material-texture":
            if tex.get("dds"):
                item["texture_resource"] = build_texture_contract(tex["dds"], tex)
                explicit_textures.append(item)
            elif tex.get("texture_resolved") or item["resolved"]:
                item["resolution_status"] = "resolved-path"
                explicit_textures.append(item)
            else:
                item["resolution_status"] = "unresolved"
                unresolved_textures.append(item)
        elif binding_source in {"unresolved", "unresolved-texture"}:
            item["resolution_status"] = "unresolved"
            unresolved_textures.append(item)
        else:
            # Renderer-global/specialized resources are kept as external
            # requirements and must not be mistaken for missing material textures.
            item["resolution_status"] = "external"
            explicit_textures.append(item)

    material_unresolved = [
        x for x in material.get("unresolved_textures", []) or []
        if x is not None
    ]

    uniforms, uniform_reasons = _uniform_contract(material, selection)
    external_samplers = selection.get("external_samplers") or material.get("external_samplers") or []

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
        "unresolved_textures": unresolved_textures + material_unresolved,
        "external_samplers": external_samplers,
        "uniform_binding": uniforms,
        "ready": not reasons and not unresolved_textures and not texture_blockers and not uniform_reasons,
        "blocking_reasons": (
            reasons
            + (["material-texture-binding:unresolved"] if unresolved_textures else [])
            + texture_blockers
            + uniform_reasons
        ),
    }


def _uniform_contract(material: dict[str, Any], selection: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    uniform_binding = selection.get("uniform_binding") or material.get("uniform_binding")
    if uniform_binding is None:
        # Materials without reflected numeric shader params may legitimately have
        # no uniform bindings. The linker still emits a typed empty contract.
        return {"format": "SHIFT.MaterialUniformBinding/1", "bindings": [], "optimized_out_or_unreflected": []}, []

    reasons: list[str] = []
    if uniform_binding.get("format") is None and not (
        uniform_binding.get("bindings") or uniform_binding.get("optimized_out_or_unreflected")
    ):
        # Preserve compatibility with legacy empty fixtures while keeping all
        # non-empty bindings schema-strict.
        uniform_binding = {
            "format": "SHIFT.MaterialUniformBinding/1",
            "bindings": [],
            "optimized_out_or_unreflected": [],
        }
    elif uniform_binding.get("format") != "SHIFT.MaterialUniformBinding/1":
        return uniform_binding, ["material-uniform-binding:invalid"]

    for binding in uniform_binding.get("bindings", []) or []:
        if binding.get("binding") != "material-constant":
            reasons.append(
                f"material-uniform-binding:register-set:{binding.get('register_set')}"
            )
        try:
            register_index = int(binding.get("register_index"))
        except (TypeError, ValueError):
            reasons.append("material-uniform-binding:register-index-invalid")
        else:
            if register_index < 0:
                reasons.append("material-uniform-binding:register-index-invalid")
        try:
            register_count = int(binding.get("register_count"))
        except (TypeError, ValueError):
            reasons.append("material-uniform-binding:register-count-invalid")
        else:
            if register_count <= 0:
                reasons.append("material-uniform-binding:register-count-invalid")
        if binding.get("shape_warning"):
            reasons.append(f"material-uniform-binding:{binding['shape_warning']}")

    return uniform_binding, list(dict.fromkeys(reasons))


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
        pair = (material.get("shader_selection") or material).get("shader_pair") or material.get("shader_pair") or {}
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
    total_indices = int(mesh.get("triangle_count", 0) or 0) * 3
    for submesh in packet.get("submeshes", []) or []:
        contract = _material_contract(submesh.get("material"))
        material_ready = material_ready and contract["ready"]
        material_reasons.extend(contract.get("blocking_reasons", []))

        first_index = int(submesh.get("first_index", 0) or 0)
        index_count = int(submesh.get("index_count", 0) or 0)
        if first_index < 0 or index_count < 0:
            reasons.append("draw:index-range-negative")
        if index_count % 3:
            reasons.append("draw:index-count-not-triangle-aligned")
        if total_indices and first_index + index_count > total_indices:
            reasons.append("draw:index-range-out-of-bounds")

        submeshes.append({
            "first_index": first_index,
            "index_count": index_count,
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
