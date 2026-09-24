"""Neutral renderer submission commands built from validated SHIFT contracts."""
from __future__ import annotations

from typing import Any


FORMAT = "SHIFT.RenderCommand/1"


def _gles_vertex_attribute_contract(attribute: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Describe the concrete GLES vertex-pointer setup for one attribute."""
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
    if register is None:
        register = texture.get("slot")
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


def validate_render_command_shaders(command: dict[str, Any]) -> dict[str, Any]:
    """Run the explicit GLES shader compiler validator over each RenderCommand submesh."""
    from shader_backend import validate_linked_shader_pair

    results: list[dict[str, Any]] = []
    reasons: list[str] = []
    for index, submesh in enumerate(command.get("submeshes", []) or []):
        shader = submesh.get("shader") or {}
        vertex = shader.get("vertex")
        pixel = shader.get("pixel")
        if not vertex or not pixel:
            results.append({
                "submesh": index,
                "status": "invalid",
                "blocking_reasons": ["shader-source-missing"],
            })
            reasons.append(f"shader-validation:submesh-{index}:source-missing")
            continue

        validation = validate_linked_shader_pair({
            "format": "SHIFT.LinkedShaderPair/1",
            "vertex_glsl": vertex,
            "pixel_glsl": pixel,
        })
        results.append({"submesh": index, **validation})
        if validation.get("status") == "invalid":
            reasons.extend(
                f"shader-validation:submesh-{index}:{reason}"
                for reason in validation.get("blocking_reasons", []) or ["invalid"]
            )

    statuses = [item.get("status") for item in results]
    if any(status == "invalid" for status in statuses):
        status = "invalid"
    elif any(status == "unavailable" for status in statuses):
        status = "unavailable"
    elif statuses:
        status = "valid"
    else:
        status = "empty"

    return {
        "format": "SHIFT.RenderCommandShaderValidation/1",
        "status": status,
        "submeshes": results,
        "blocking_reasons": list(dict.fromkeys(reasons)),
    }


def build_render_command(static_draw: dict[str, Any], resources: dict[str, Any], *, validate_shaders: bool = False) -> dict[str, Any]:
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
        constant_payload = None
        if uniform_binding.get("bindings"):
            from material_constants import pack_material_constant_payload
            constant_payload = pack_material_constant_payload(uniform_binding)
            if constant_payload.get("ready") is False:
                reasons.extend(
                    constant_payload.get("blocking_reasons", [])
                    or ["uniform-payload:not-ready"]
                )
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
            sampler_resource = binding.get("sampler_resource") if binding else None
            sampler_state = (sampler_resource or {}).get("state") or {}
            texture_commands.append({
                "sampler": texture.get("sampler"),
                "d3d9_sampler_register": binding.get("d3d9_sampler_register") if binding else texture.get("slot"),
                "resource_binding_id": binding.get("id") if binding else None,
                "texture_id": binding.get("texture_id") if binding else None,
                "sampler_id": binding.get("sampler_id") if binding else None,
                "sampler_state": sampler_state,
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

        shader_validation = None
        if linked_pair is not None:
            shader_validation = linked_pair.get("shader_validation")
        external_samplers = []
        for external in material.get("external_samplers", []) or []:
            row = dict(external)
            register = row.get("d3d9_sampler_register")
            if register is None:
                register = row.get("slot")
            if register is not None:
                row["d3d9_sampler_register"] = register
            external_samplers.append(row)

        commands.append({
            "first_index": submesh.get("first_index", 0),
            "index_count": submesh.get("index_count", 0),
            "shader": {
                "vertex": linked_pair.get("vertex_glsl") if linked_pair else None,
                "pixel": linked_pair.get("pixel_glsl") if linked_pair else None,
                "vertex_program": linked_pair.get("vertex") if linked_pair else None,
                "pixel_program": linked_pair.get("pixel") if linked_pair else None,
                "varying_locations": linked_pair.get("varying_locations", []) if linked_pair else [],
                "vertex_input_locations": linked_pair.get("vertex_input_locations", {}) if linked_pair else {},
                "constant_buffer_binding": 14,
                "validation": shader_validation,
            },
            "textures": texture_commands,
            "external_samplers": external_samplers,
            "uniforms": uniform_binding,
            "constant_payload": constant_payload,
            "constant_commands": constant_commands,
        })

    command = {
        "format": FORMAT,
        "ready": False,
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
            "external_sampler_count": sum(
                len(submesh.get("external_samplers", []) or [])
                for submesh in commands
            ),
        },
    }
    if validate_shaders:
        shader_validation = validate_render_command_shaders(command)
        command["shader_validation"] = shader_validation
        if shader_validation["status"] == "invalid":
            command["blocking_reasons"].extend(
                shader_validation.get("blocking_reasons", [])
            )

    validation = validate_render_command(command)
    command["ready"] = (
        bool(static_draw.get("ready"))
        and not command["blocking_reasons"]
        and validation["valid"]
    )
    command["blocking_reasons"] = list(dict.fromkeys(
        command["blocking_reasons"] + validation["blocking_reasons"]
    ))
    command["validation"] = validation
    return command



def build_skinned_render_command(
    skinned_draw: dict[str, Any],
    resources: dict[str, Any],
    *,
    validate_shaders: bool = False,
) -> dict[str, Any]:
    """Build the common RenderCommand/1 ABI from a validated SkinnedDraw/1."""
    if skinned_draw.get("format") != "SHIFT.SkinnedDraw/1":
        raise ValueError("expected SHIFT.SkinnedDraw/1")

    static_draw = {
        "format": "SHIFT.StaticDraw/1",
        "ready": bool(skinned_draw.get("ready")),
        "blocking_reasons": list(skinned_draw.get("blocking_reasons", []) or []),
        "mesh": skinned_draw.get("mesh") or {},
        "world_matrix": skinned_draw.get("world_matrix"),
        "submeshes": skinned_draw.get("submeshes", []) or [],
    }
    command = build_render_command(
        static_draw,
        resources,
        validate_shaders=validate_shaders,
    )

    palette = (skinned_draw.get("bind_skeleton") or {}).get("palette") or {}
    pose = skinned_draw.get("skin_pose") or {}
    skin_contract = skinned_draw.get("skinning") or {}
    command["draw_kind"] = "skinned"
    command["skinning"] = {
        "format": "SHIFT.Skinning/1",
        "influences": int(skin_contract.get("influences", 0) or 0),
        "weights": dict(skin_contract.get("weights") or {}),
        "indices": dict(skin_contract.get("indices") or {}),
        "bind_skeleton": {
            "format": palette.get("format", "SHIFT.BonePalette/1"),
            "bone_count": int(palette.get("bone_count", 0) or 0),
            "matrix_layout": palette.get("matrix_layout"),
            "matrix_space": palette.get("matrix_space"),
            "local_matrices_3x4": list(palette.get("local_matrices_3x4", []) or []),
        },
        "skin_pose": {
            "format": pose.get("format"),
            "matrix_space": pose.get("matrix_space"),
            "matrix_layout": pose.get("matrix_layout", "3x4-row-major"),
            "bone_count": int(pose.get("bone_count", 0) or 0),
            "matrices_3x4": list(pose.get("matrices_3x4", []) or []),
            "source": pose.get("source"),
            "frame": pose.get("frame"),
        },
    }
    validation = validate_render_command(command)
    command["ready"] = bool(command.get("ready")) and validation["valid"]
    command["blocking_reasons"] = list(dict.fromkeys(
        list(command.get("blocking_reasons", []) or [])
        + validation["blocking_reasons"]
    ))
    command["validation"] = validation
    return command



def validate_render_command(command: dict[str, Any]) -> dict[str, Any]:
    """Validate the final RenderCommand/1 submission shape before backend consumption."""
    reasons: list[str] = []
    if command.get("format") != FORMAT:
        reasons.append("render-command:invalid-format")

    if command.get("draw_kind") == "skinned":
        skin = command.get("skinning") or {}
        if skin.get("format") != "SHIFT.Skinning/1":
            reasons.append("skinning:invalid-format")
        try:
            influences = int(skin.get("influences", 0))
        except (TypeError, ValueError):
            influences = 0
            reasons.append("skinning:influence-count-invalid")
        if influences != 4:
            reasons.append("skinning:influence-count-invalid")
        for label in ("weights", "indices"):
            if not isinstance(skin.get(label), dict):
                reasons.append(f"skinning:{label}-binding-missing")
        pose = skin.get("skin_pose") or {}
        palette = skin.get("bind_skeleton") or {}
        if pose.get("format") != "SHIFT.SkinPose/1":
            reasons.append("skinning:skin-pose-invalid")
        if pose.get("matrix_space") != "skinning":
            reasons.append("skinning:skin-pose-space-invalid")
        if palette.get("matrix_layout") not in (None, "3x4-row-major"):
            reasons.append("skinning:bind-palette-layout-invalid")
        try:
            pose_bones = int(pose.get("bone_count", 0))
            pose_matrices = list(pose.get("matrices_3x4", []) or [])
        except (TypeError, ValueError):
            pose_bones = 0
            pose_matrices = []
            reasons.append("skinning:skin-pose-payload-invalid")
        if pose_bones <= 0 or len(pose_matrices) != pose_bones:
            reasons.append("skinning:skin-pose-palette-incomplete")
        for index, matrix in enumerate(pose_matrices):
            if not isinstance(matrix, list) or len(matrix) != 12:
                reasons.append(f"skinning:skin-pose-matrix-invalid:{index}")

    shader_validation = command.get("shader_validation") or {}
    if shader_validation.get("format") not in (None, "SHIFT.RenderCommandShaderValidation/1"):
        reasons.append("shader-validation:invalid-format")
    if shader_validation.get("status") == "invalid":
        reasons.extend(shader_validation.get("blocking_reasons", []) or ["shader-validation:invalid"])

    mesh = command.get("mesh") or {}
    layout = mesh.get("vertex_layout") or {}
    if layout.get("format") != "SHIFT.VertexLayout/1":
        reasons.append("vertex-layout:invalid")

    try:
        vertex_count = int(mesh.get("vertex_count"))
        if vertex_count < 0:
            reasons.append("mesh:vertex-count-invalid")
    except (TypeError, ValueError):
        reasons.append("mesh:vertex-count-invalid")

    seen_locations: dict[int, str] = {}
    for attribute in list(command.get("mesh", {}).get("attributes", []) or []):
        try:
            location = int(attribute.get("location"))
        except (TypeError, ValueError):
            reasons.append("vertex-attribute:location-invalid")
            continue
        if location < 0:
            reasons.append("vertex-attribute:location-invalid")
            continue
        property_id = str(attribute.get("property_id"))
        owner = seen_locations.get(location)
        if owner is not None and owner != property_id:
            reasons.append(f"vertex-attribute:location-collision:{location}")
        else:
            seen_locations[location] = property_id
        try:
            offset = int(attribute.get("offset", 0) or 0)
            stride = int(attribute.get("stride", 0) or 0)
        except (TypeError, ValueError):
            reasons.append(f"vertex-attribute:range-invalid:{property_id}")
        else:
            if offset < 0:
                reasons.append(f"vertex-attribute:offset-invalid:{property_id}")
            if stride <= 0:
                reasons.append(f"vertex-attribute:stride-invalid:{property_id}")

    plan = command.get("resource_plan") or {}
    if plan.get("format") != "SHIFT.RenderResources/1":
        reasons.append("resource-plan:invalid-format")
    for key in ("texture_count", "sampler_count", "external_sampler_count"):
        try:
            if int(plan.get(key, 0) or 0) < 0:
                reasons.append(f"resource-plan:{key}-invalid")
        except (TypeError, ValueError):
            reasons.append(f"resource-plan:{key}-invalid")

    submeshes = list(command.get("submeshes", []) or [])
    if not submeshes:
        reasons.append("draw:empty")
    for submesh in submeshes:
        try:
            first = int(submesh.get("first_index", 0))
            count = int(submesh.get("index_count", 0))
        except (TypeError, ValueError):
            reasons.append("index-range:invalid")
        else:
            if first < 0 or count < 0 or count % 3:
                reasons.append("index-range:invalid")

        shader = submesh.get("shader") or {}
        if not shader.get("vertex"):
            reasons.append("shader:vertex-source-missing")
        if not shader.get("pixel"):
            reasons.append("shader:pixel-source-missing")

        for key in ("vertex_program", "pixel_program"):
            program = shader.get(key)
            if program is not None:
                if program.get("schema") != "SHIFT.ShaderProgram/1":
                    reasons.append(f"shader-ir:{key}:invalid-schema")
                if program.get("stage") not in {"vertex", "pixel"}:
                    reasons.append(f"shader-ir:{key}:invalid-stage")

        shader_validation = shader.get("validation") or {}
        if shader_validation.get("format") not in (None, "SHIFT.GLESShaderValidation/1"):
            reasons.append("shader-validation:invalid-format")
        if shader_validation.get("status") == "invalid":
            reasons.extend(shader_validation.get("blocking_reasons", []) or ["shader-validation:invalid"])

        uniform = submesh.get("uniforms") or {}
        if uniform.get("format") not in (None, "SHIFT.MaterialUniformBinding/1"):
            reasons.append("uniform-binding:invalid-format")
        constant_payload = submesh.get("constant_payload") or {}
        if constant_payload.get("format") not in (None, "SHIFT.MaterialConstantPayload/1"):
            reasons.append("uniform-payload:invalid-format")
        if constant_payload.get("ready") is False:
            reasons.extend(
                constant_payload.get("blocking_reasons", [])
                or ["uniform-payload:not-ready"]
            )
        expected_registers: set[int] = set()
        for constant in submesh.get("constant_commands", []) or []:
            try:
                start = int(constant.get("register_index"))
                count = int(constant.get("register_count"))
            except (TypeError, ValueError):
                continue
            expected_registers.update(range(start, start + max(0, count)))
        if constant_payload.get("ready") is True:
            payload_registers: set[int] = set()
            for payload_register in constant_payload.get("registers", []) or []:
                try:
                    reg = int(payload_register.get("register_index"))
                    values = payload_register.get("values")
                    byte_offset = int(payload_register.get("byte_offset"))
                    byte_size = int(payload_register.get("byte_size"))
                except (TypeError, ValueError):
                    reasons.append("uniform-payload:register-invalid")
                    continue
                if not isinstance(values, list) or len(values) != 4 or any(
                    not isinstance(value, (int, float)) for value in values
                ):
                    reasons.append(f"uniform-payload:register-width-invalid:{reg}")
                if byte_offset != reg * 16 or byte_size != 16:
                    reasons.append(f"uniform-payload:byte-range-invalid:{reg}")
                payload_registers.add(reg)
            if expected_registers and payload_registers != expected_registers:
                reasons.append("uniform-payload:register-set-mismatch")
        for constant in submesh.get("constant_commands", []) or []:
            try:
                register_index = int(constant.get("register_index"))
                register_count = int(constant.get("register_count"))
            except (TypeError, ValueError):
                reasons.append("renderer-constant-binding:register-range-invalid")
            else:
                if register_index < 0 or register_count <= 0:
                    reasons.append("renderer-constant-binding:register-range-invalid")

        sampler_registers: dict[int, int] = {}
        for texture_index, texture in enumerate(submesh.get("textures", []) or []):
            if texture.get("resource") == "external":
                continue
            if not texture.get("resource_binding_id"):
                reasons.append("texture-command:resource-binding-missing")
            if not texture.get("texture_id"):
                reasons.append("texture-command:texture-id-missing")
            if not texture.get("sampler_id"):
                reasons.append("texture-command:sampler-id-missing")

            register = texture.get("d3d9_sampler_register")
            if register is not None:
                try:
                    register_value = int(register)
                except (TypeError, ValueError):
                    reasons.append(f"texture-command:sampler-register-invalid:{texture_index}")
                else:
                    owner = sampler_registers.get(register_value)
                    if owner is not None:
                        reasons.append(
                            f"texture-command:sampler-register-collision:{register_value}"
                        )
                    else:
                        sampler_registers[register_value] = texture_index

            sampler_state = texture.get("sampler_state") or {}
            if sampler_state and sampler_state.get("format") != "SHIFT.SamplerState/1":
                reasons.append(f"texture-command:sampler-state-invalid:{texture_index}")
            if sampler_state.get("ready") is False:
                reasons.extend(
                    sampler_state.get("blocking_reasons", [])
                    or [f"texture-command:sampler-state-not-ready:{texture_index}"]
                )

        external_registers: set[int] = set()
        for external_index, external in enumerate(submesh.get("external_samplers", []) or []):
            register = external.get("d3d9_sampler_register")
            try:
                register_value = int(register)
            except (TypeError, ValueError):
                reasons.append(f"external-sampler:register-invalid:{external_index}")
                continue
            if register_value < 0:
                reasons.append(f"external-sampler:register-invalid:{external_index}")
                continue
            if register_value in external_registers:
                reasons.append(f"external-sampler:register-collision:{register_value}")
            external_registers.add(register_value)
            if register_value in sampler_registers:
                reasons.append(f"external-sampler:collides-with-material:{register_value}")
            sampler_type = str(external.get("sampler_type") or "").strip()
            if sampler_type not in {"sampler2D", "samplerCube", "sampler3D", "sampler1D"}:
                reasons.append(
                    f"external-sampler:type-invalid:{external_index}:{sampler_type or 'missing'}"
                )

    reasons = list(dict.fromkeys(reasons))
    return {
        "format": "SHIFT.RenderCommandValidation/1",
        "valid": not reasons,
        "blocking_reasons": reasons,
    }
