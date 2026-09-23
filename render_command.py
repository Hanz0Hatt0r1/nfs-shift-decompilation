"""Neutral renderer submission commands built from validated SHIFT contracts."""
from __future__ import annotations

from typing import Any


FORMAT = "SHIFT.RenderCommand/1"


def _gles_vertex_attribute_contract(attribute: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Describe the concrete GLES vertex-pointer call for one VertexLayout attribute."""
    property_id = str(attribute.get("property_id") or "")
    raw_storage = attribute.get("android") or attribute.get("storage") or ""
    storage = str(raw_storage).upper().replace("_", "").replace("-", "")
    mappings = {
        "FLOAT32X2": (2, "FLOAT", False, "glVertexAttribPointer"),
        "F32X2": (2, "FLOAT", False, "glVertexAttribPointer"),
        "FLOAT32X3": (3, "FLOAT", False, "glVertexAttribPointer"),
        "F32X3": (3, "FLOAT", False, "glVertexAttribPointer"),
        "FLOAT32X4": (4, "FLOAT", False, "glVertexAttribPointer"),
        "F32X4": (4, "FLOAT", False, "glVertexAttribPointer"),
        "UINT8X4": (
            4,
            "UNSIGNED_BYTE",
            property_id == "580",
            "glVertexAttribIPointer" if property_id == "580" else "glVertexAttribPointer",
        ),
        "UBYTE4": (
            4,
            "UNSIGNED_BYTE",
            property_id == "580",
            "glVertexAttribIPointer" if property_id == "580" else "glVertexAttribPointer",
        ),
    }
    info = mappings.get(storage)
    if info is None:
        return None, f"vertex-attribute-storage:unsupported:{raw_storage or 'missing'}"

    components, gl_type, integer_pointer, pointer_api = info
    try:
        location = int(attribute.get("location"))
        offset = int(attribute.get("offset"))
        stride = int(attribute.get("stride"))
    except (TypeError, ValueError):
        return None, "vertex-attribute-layout:integer-field-invalid"
    if location < 0 or offset < 0 or stride <= 0:
        return None, "vertex-attribute-layout:range-invalid"

    normalized = bool(attribute.get("normalized"))
    if integer_pointer and normalized:
        return None, "vertex-attribute-layout:integer-input-cannot-be-normalized"

    return {
        "location": location,
        "property_id": property_id,
        "components": components,
        "gl_type": gl_type,
        "normalized": normalized,
        "integer_pointer": integer_pointer,
        "pointer_api": pointer_api,
        "offset": offset,
        "stride": stride,
        "element_size": attribute.get("element_size"),
        "abi_status": attribute.get("abi_status"),
        "channel_order_candidates": attribute.get("channel_order_candidates"),
    }, None


def _find_texture_resource(resources: dict[str, Any], texture: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    ref = str(texture.get("ref") or "").replace("\\", "/").lower()
    sampler = texture.get("sampler")
    register = texture.get("d3d9_sampler_register")
    candidates = []
    for binding in resources.get("bindings", []) or []:
        if register is not None and binding.get("d3d9_sampler_register") not in (None, register):
            continue
        if binding.get("material_parameter") not in (None, texture.get("material_parameter")):
            continue
        texture_id = binding.get("texture_id")
        resource = next(
            (x for x in resources.get("textures", []) or [] if x.get("id") == texture_id),
            None,
        )
        if resource is None:
            continue
        path = str(resource.get("path") or "").replace("\\", "/").lower()
        if ref and path != ref and path.rsplit("/", 1)[-1] != ref.rsplit("/", 1)[-1]:
            continue
        sampler_id = binding.get("sampler_id")
        sampler_resource = next(
            (x for x in resources.get("samplers", []) or [] if x.get("id") == sampler_id),
            None,
        )
        if sampler and sampler_resource is not None:
            candidates.append({**binding, "texture_resource": resource, "sampler_resource": sampler_resource})
        elif sampler is None:
            candidates.append({**binding, "texture_resource": resource, "sampler_resource": sampler_resource})

    if len(candidates) == 1:
        return candidates[0], None
    if not candidates:
        return None, "renderer-texture-resource:missing"
    return None, "renderer-texture-resource:ambiguous"


def build_render_command(static_draw: dict[str, Any], resources: dict[str, Any]) -> dict[str, Any]:
    """Build an Android/GLES-neutral draw submission plan."""
    reasons = list(static_draw.get("blocking_reasons", []) or [])
    if static_draw.get("format") != "SHIFT.StaticDraw/1":
        reasons.append("static-draw:invalid")

    mesh = static_draw.get("mesh") or {}
    layout = mesh.get("vertex_layout") or {}
    attributes = []
    attribute_setup = []
    for attribute in layout.get("attributes", []) or []:
        normalized_attribute = {
            "location": attribute.get("location"),
            "property_id": attribute.get("property_id"),
            "storage": attribute.get("storage") or attribute.get("android"),
            "normalized": attribute.get("normalized"),
            "offset": attribute.get("offset"),
            "stride": attribute.get("stride") or layout.get("buffer_stride"),
            "element_size": attribute.get("element_size"),
            "abi_status": attribute.get("abi_status"),
        }
        attributes.append(normalized_attribute)
        setup, error = _gles_vertex_attribute_contract({
            **attribute,
            "stride": attribute.get("stride") or layout.get("buffer_stride"),
        })
        if error:
            reasons.append(error)
        elif setup is not None:
            attribute_setup.append(setup)

    commands = []
    for submesh in static_draw.get("submeshes", []) or []:
        material = submesh.get("material") or {}
        shader_selection = material.get("shader_selection") or {}
        linked_pair = shader_selection.get("linked_shader_pair") or material.get("linked_shader_pair")
        uniform_binding = material.get("uniform_binding") or shader_selection.get("uniform_binding") or {}
        texture_commands = []
        for texture in material.get("textures", []) or []:
            binding, error = _find_texture_resource(resources, texture)
            if error:
                if texture.get("resolution_status") == "external":
                    texture_commands.append({
                        "sampler": texture.get("sampler"),
                        "d3d9_sampler_register": texture.get("slot") or texture.get("d3d9_sampler_register"),
                        "resource": "external",
                    })
                    continue
                reasons.append(error)
                continue
            if binding and not binding.get("gpu_ready", False):
                reasons.extend(
                    binding.get("blocking_reasons", [])
                    or ["renderer-texture-resource:not-gpu-ready"]
                )
            texture_commands.append({
                "sampler": texture.get("sampler"),
                "d3d9_sampler_register": binding.get("d3d9_sampler_register") if binding else texture.get("slot"),
                "resource_binding_id": binding.get("id") if binding else None,
                "texture_id": binding.get("texture_id") if binding else None,
                "sampler_id": binding.get("sampler_id") if binding else None,
            })

        constant_commands = []
        for uniform in uniform_binding.get("bindings", []) or []:
            try:
                register_index = int(uniform.get("register_index"))
            except (TypeError, ValueError):
                reasons.append("renderer-constant-binding:register-index-invalid")
                continue
            try:
                register_count = int(uniform.get("register_count"))
            except (TypeError, ValueError):
                reasons.append("renderer-constant-binding:register-count-invalid")
                continue
            if register_index < 0 or register_count <= 0:
                reasons.append("renderer-constant-binding:register-range-invalid")
                continue
            constant_commands.append({
                "name": uniform.get("name"),
                "stage": uniform.get("stage"),
                "register_index": register_index,
                "register_count": register_count,
                "ctab_type": uniform.get("ctab_type"),
                "ubo_binding": 14,
                "byte_offset": register_index * 16,
            })

        commands.append({
            "first_index": submesh.get("first_index", 0),
            "index_count": submesh.get("index_count", 0),
            "shader": {
                "vertex": linked_pair.get("vertex_glsl") if linked_pair else None,
                "pixel": linked_pair.get("pixel_glsl") if linked_pair else None,
                "varying_locations": linked_pair.get("varying_locations", []) if linked_pair else [],
                "vertex_input_locations": linked_pair.get("vertex_input_locations", {}) if linked_pair else {},
                "constant_buffer_binding": 14,
            },
            "textures": texture_commands,
            "uniforms": uniform_binding,
            "constant_commands": constant_commands,
        })

    return {
        "format": FORMAT,
        "ready": bool(static_draw.get("ready")) and not reasons,
        "blocking_reasons": list(dict.fromkeys(reasons)),
        "mesh": {
            "ref": mesh.get("ref"),
            "vertex_count": mesh.get("vertex_count"),
            "triangle_count": mesh.get("triangle_count"),
            "vertex_layout": layout,
            "attributes": attributes,
            "attribute_setup": attribute_setup,
        },
        "world_matrix": static_draw.get("world_matrix"),
        "submeshes": commands,
        "resource_plan": {
            "format": resources.get("format"),
            "texture_count": resources.get("stats", {}).get("textures", 0),
            "sampler_count": resources.get("stats", {}).get("samplers", 0),
        },
    }
