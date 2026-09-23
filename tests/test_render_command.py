from static_draw import build_static_draw_contract
from render_command import build_render_command, validate_render_command


def _packet():
    return {
        "scene": "cars/body.vhf",
        "node": "BODY",
        "mesh": {
            "ref": "cars/body.meb",
            "vertex_count": 3,
            "triangle_count": 1,
            "vertex_layout": {
                "format": "SHIFT.VertexLayout/1",
                "buffer_stride": 12,
                "attributes": [{
                    "property_id": "200",
                    "location": 0,
                    "offset": 0,
                    "element_size": 12,
                    "stride": 12,
                    "storage": "f32x3",
                    "abi_status": "inferred",
                }],
            },
        },
        "world_matrix": None,
        "submeshes": [{
            "first_index": 0,
            "index_count": 3,
            "material": {
                "name": "BODY",
                "status": "unique",
                "shader_pair": {
                    "selection_status": "unique",
                    "interface": {"valid": True},
                    "vertex_format": {"valid": True},
                },
                "linked_shader_pair": {
                    "format": "SHIFT.LinkedShaderPair/1",
                    "vertex_glsl": "#version 310 es\n",
                    "pixel_glsl": "#version 310 es\n",
                    "varying_locations": [],
                    "vertex_input_locations": {"0": 0},
                },
                "uniform_binding": {
                    "format": "SHIFT.MaterialUniformBinding/1",
                    "bindings": [],
                    "optimized_out_or_unreflected": [],
                },
                "textures": [{
                    "material_parameter": "Diffuse",
                    "ref": "textures/body.dds",
                    "slot": 1,
                    "d3d9_sampler_register": 1,
                    "sampler": "diffuseMap",
                    "binding_source": "fxo-ctab",
                    "resolved": [{"path": "textures/body.dds"}],
                }],
            },
        }],
    }


def _resources(gpu_ready=True):
    return {
        "format": "SHIFT.RenderResources/1",
        "textures": [{
            "id": "tex_body",
            "path": "textures/body.dds",
            "gpu_ready": gpu_ready,
            "blocking_reasons": [] if gpu_ready else ["runtime-extension-missing:X"],
        }],
        "samplers": [{
            "id": "smp_body",
            "state": {},
        }],
        "bindings": [{
            "id": "tb_body",
            "texture_id": "tex_body",
            "sampler_id": "smp_body",
            "material_parameter": "Diffuse",
            "d3d9_sampler_register": 1,
            "gpu_ready": gpu_ready,
            "blocking_reasons": [] if gpu_ready else ["runtime-extension-missing:X"],
        }],
        "unresolved": [],
        "stats": {
            "textures": 1,
            "samplers": 1,
            "bindings": 1,
        },
    }


def test_render_command_resolves_texture_resource_binding():
    packet = _packet()
    static_draw = build_static_draw_contract(packet)
    assert static_draw["ready"] is True
    result = build_render_command(static_draw, _resources())
    assert result["format"] == "SHIFT.RenderCommand/1"
    assert result["ready"] is True
    tex = result["submeshes"][0]["textures"][0]
    assert tex["resource_binding_id"] == "tb_body"
    assert tex["texture_id"] == "tex_body"
    assert tex["sampler_id"] == "smp_body"


def test_render_command_blocks_missing_texture_resource():
    packet = _packet()
    static_draw = build_static_draw_contract(packet)
    resources = _resources()
    resources["bindings"] = []
    result = build_render_command(static_draw, resources)
    assert result["ready"] is False
    assert "renderer-texture-resource:missing" in result["blocking_reasons"]


def test_render_command_propagates_gpu_texture_blocker():
    packet = _packet()
    static_draw = build_static_draw_contract(packet)
    result = build_render_command(static_draw, _resources(gpu_ready=False))
    assert result["ready"] is False
    assert "runtime-extension-missing:X" in result["blocking_reasons"]


def test_render_command_exposes_gles_constant_buffer_offsets():
    packet = _packet()
    packet["submeshes"][0]["material"]["uniform_binding"] = {
        "format": "SHIFT.MaterialUniformBinding/1",
        "bindings": [{
            "name": "primerBasis",
            "binding": "material-constant",
            "register_set": 2,
            "register_index": 5,
            "register_count": 1,
            "ctab_type": "float4",
        }],
        "optimized_out_or_unreflected": [],
    }
    draw = build_static_draw_contract(packet)
    resources = _resources()
    result = build_render_command(draw, resources)
    constants = result["submeshes"][0]["constant_commands"]
    assert constants == [{
        "name": "primerBasis",
        "stage": None,
        "register_index": 5,
        "register_count": 1,
        "ctab_type": "float4",
        "ubo_binding": 14,
        "byte_offset": 80,
    }]


def test_render_command_rejects_invalid_constant_register_range():
    packet = _packet()
    packet["submeshes"][0]["material"]["uniform_binding"] = {
        "format": "SHIFT.MaterialUniformBinding/1",
        "bindings": [{
            "name": "primerBasis",
            "binding": "material-constant",
            "register_set": 2,
            "register_index": -1,
            "register_count": 1,
            "ctab_type": "float4",
        }],
        "optimized_out_or_unreflected": [],
    }
    draw = build_static_draw_contract(packet)
    result = build_render_command(draw, _resources())
    assert result["ready"] is False
    assert "renderer-constant-binding:register-range-invalid" in result["blocking_reasons"]


def test_render_command_validation_gate_is_reported():
    static_draw = build_static_draw_contract(_packet())
    result = build_render_command(static_draw, _resources())
    assert result["ready"] is True
    assert result["validation"]["format"] == "SHIFT.RenderCommandValidation/1"
    assert result["validation"]["valid"] is True


def test_render_command_validation_rejects_missing_shader_source():
    static_draw = build_static_draw_contract(_packet())
    result = build_render_command(static_draw, _resources())
    result["submeshes"][0]["shader"]["vertex"] = None
    validation = validate_render_command(result)
    assert validation["valid"] is False
    assert "shader:vertex-source-missing" in validation["blocking_reasons"]


def test_render_command_validation_rejects_location_collision():
    static_draw = build_static_draw_contract(_packet())
    result = build_render_command(static_draw, _resources())
    result["mesh"]["attributes"].append({
        "location": 0,
        "property_id": "220",
        "offset": 12,
        "stride": 12,
        "storage": "f32x3",
    })
    validation = validate_render_command(result)
    assert validation["valid"] is False
    assert "vertex-attribute:location-collision:0" in validation["blocking_reasons"]


def test_render_command_validation_rejects_bad_index_count():
    static_draw = build_static_draw_contract(_packet())
    result = build_render_command(static_draw, _resources())
    result["submeshes"][0]["index_count"] = 4
    validation = validate_render_command(result)
    assert validation["valid"] is False
    assert "index-range:invalid" in validation["blocking_reasons"]


def test_render_command_emits_explicit_gles_vertex_setup():
    packet = _packet()
    packet["mesh"]["vertex_layout"]["attributes"] = [
        {
            "property_id": "200",
            "location": 3,
            "storage": "FLOAT32x3",
            "normalized": False,
            "offset": 0,
            "stride": 32,
            "element_size": 12,
            "abi_status": "inferred",
        },
        {
            "property_id": "580",
            "location": 7,
            "storage": "UINT8x4",
            "normalized": False,
            "offset": 28,
            "stride": 32,
            "element_size": 4,
            "abi_status": "proven",
        },
        {
            "property_id": "460",
            "location": 9,
            "storage": "UINT8x4",
            "normalized": True,
            "offset": 12,
            "stride": 32,
            "element_size": 4,
            "abi_status": "ambiguous",
            "channel_order_candidates": ["RGBA", "BGRA"],
        },
    ]
    draw = build_static_draw_contract(packet)
    result = build_render_command(draw, _resources())
    assert result["ready"] is True
    setup = {x["property_id"]: x for x in result["mesh"]["attribute_setup"]}
    assert setup["200"]["components"] == 3
    assert setup["200"]["gl_type"] == "FLOAT"
    assert setup["200"]["pointer_api"] == "glVertexAttribPointer"
    assert setup["580"]["gl_type"] == "UNSIGNED_BYTE"
    assert setup["580"]["pointer_api"] == "glVertexAttribIPointer"
    assert setup["580"]["integer_pointer"] is True
    assert setup["460"]["normalized"] is True
    assert setup["460"]["pointer_api"] == "glVertexAttribPointer"
    assert setup["460"]["channel_order_candidates"] == ["RGBA", "BGRA"]


def test_render_command_blocks_unsupported_vertex_storage():
    packet = _packet()
    packet["mesh"]["vertex_layout"]["attributes"][0]["storage"] = "RAW4"
    packet["mesh"]["vertex_layout"]["attributes"][0]["android"] = None
    draw = build_static_draw_contract(packet)
    result = build_render_command(draw, _resources())
    assert result["ready"] is False
    assert "vertex-attribute-storage:unsupported:RAW4" in result["blocking_reasons"]


def test_render_command_blocks_normalized_integer_bone_indices():
    packet = _packet()
    packet["mesh"]["vertex_layout"]["attributes"] = [{
        "property_id": "580",
        "location": 2,
        "storage": "UINT8x4",
        "normalized": True,
        "offset": 0,
        "stride": 4,
        "element_size": 4,
        "abi_status": "proven",
    }]
    draw = build_static_draw_contract(packet)
    result = build_render_command(draw, _resources())
    assert result["ready"] is False
    assert "vertex-attribute-layout:integer-input-cannot-be-normalized" in result["blocking_reasons"]


def test_render_command_can_attach_shader_validation(monkeypatch):
    from render_command import validate_render_command_shaders

    monkeypatch.setattr(
        "shader_backend.validate_linked_shader_pair",
        lambda pair: {
            "format": "SHIFT.GLESShaderValidation/1",
            "status": "valid",
            "validator": "/usr/bin/glslangValidator",
            "stages": {
                "vertex": {"valid": True},
                "pixel": {"valid": True},
            },
            "link": {"valid": True},
            "blocking_reasons": [],
        },
    )
    draw = build_static_draw_contract(_packet())
    result = build_render_command(draw, _resources(), validate_shaders=True)
    assert result["ready"] is True
    assert result["shader_validation"]["format"] == "SHIFT.RenderCommandShaderValidation/1"
    assert result["shader_validation"]["status"] == "valid"
    assert result["shader_validation"]["submeshes"][0]["status"] == "valid"


def test_render_command_shader_validation_blocks_invalid_pair(monkeypatch):
    monkeypatch.setattr(
        "shader_backend.validate_linked_shader_pair",
        lambda pair: {
            "format": "SHIFT.GLESShaderValidation/1",
            "status": "invalid",
            "validator": "/usr/bin/glslangValidator",
            "stages": {
                "vertex": {"valid": True},
                "pixel": {"valid": False},
            },
            "link": {"valid": None},
            "blocking_reasons": ["linked-shader:pixel-compile-failed"],
        },
    )
    draw = build_static_draw_contract(_packet())
    result = build_render_command(draw, _resources(), validate_shaders=True)
    assert result["ready"] is False
    assert result["shader_validation"]["status"] == "invalid"
    assert "shader-validation:submesh-0:linked-shader:pixel-compile-failed" in result["blocking_reasons"]


def test_render_command_shader_validation_unavailable_is_nonblocking(monkeypatch):
    monkeypatch.setattr(
        "shader_backend.validate_linked_shader_pair",
        lambda pair: {
            "format": "SHIFT.GLESShaderValidation/1",
            "status": "unavailable",
            "validator": None,
            "stages": {
                "vertex": {"valid": None},
                "pixel": {"valid": None},
            },
            "link": {"valid": None},
            "blocking_reasons": [],
        },
    )
    draw = build_static_draw_contract(_packet())
    result = build_render_command(draw, _resources(), validate_shaders=True)
    assert result["ready"] is True
    assert result["shader_validation"]["status"] == "unavailable"


def test_render_command_propagates_sampler_state():
    packet = _packet()
    resources = _resources()
    resources["samplers"][0]["state"] = {
        "format": "SHIFT.SamplerState/1",
        "min_filter": "LINEAR",
        "mag_filter": "LINEAR",
        "mip_filter": "LINEAR",
        "min_filter_gl": "LINEAR_MIPMAP_LINEAR",
        "address_u": "REPEAT",
        "address_v": "CLAMP_TO_EDGE",
        "address_w": "REPEAT",
        "ready": True,
        "blocking_reasons": [],
    }
    static_draw = build_static_draw_contract(packet)
    result = build_render_command(static_draw, resources)
    texture = result["submeshes"][0]["textures"][0]
    assert texture["sampler_state"]["format"] == "SHIFT.SamplerState/1"
    assert texture["sampler_state"]["min_filter"] == "LINEAR"
    assert texture["sampler_state"]["address_v"] == "CLAMP_TO_EDGE"


def test_render_command_accepts_distinct_sampler_registers():
    packet = _packet()
    packet["submeshes"][0]["material"]["textures"] = [
        {
            "material_parameter": "Diffuse",
            "ref": "textures/body.dds",
            "slot": 1,
            "d3d9_sampler_register": 1,
            "sampler": "diffuseMap",
            "binding_source": "fxo-ctab",
            "resolved": [{"path": "textures/diffuse.dds"}],
        },
        {
            "material_parameter": "Diffuse",
            "ref": "textures/body.dds",
            "slot": 2,
            "d3d9_sampler_register": 2,
            "sampler": "specularMap",
            "binding_source": "fxo-ctab",
            "resolved": [{"path": "textures/body.dds"}],
        },
    ]
    resources = _resources()
        resources["samplers"].append({
        "id": "smp_specular",
        "state": {
            "format": "SHIFT.SamplerState/1",
            "min_filter": "POINT",
            "mag_filter": "POINT",
            "ready": True,
            "blocking_reasons": [],
        },
    })
    resources["bindings"].append({
        "id": "tb_specular",
        "texture_id": "tex_body",
        "sampler_id": "smp_specular",
        "material_parameter": "Specular",
        "d3d9_sampler_register": 2,
        "gpu_ready": True,
        "blocking_reasons": [],
    })
    draw = build_static_draw_contract(packet)
    result = build_render_command(draw, resources)
    assert result["ready"] is True, result
    assert [x["d3d9_sampler_register"] for x in result["submeshes"][0]["textures"]] == [1, 2]


def test_render_command_rejects_sampler_register_collision():
    packet = _packet()
    packet["submeshes"][0]["material"]["textures"] = [
        {
            "material_parameter": "Diffuse",
            "ref": "textures/body.dds",
            "slot": 1,
            "d3d9_sampler_register": 1,
            "sampler": "diffuseMap",
            "binding_source": "fxo-ctab",
            "resolved": [{"path": "textures/body.dds"}],
        },
        {
            "material_parameter": "Diffuse",
            "ref": "textures/body.dds",
            "slot": 1,
            "d3d9_sampler_register": 1,
            "sampler": "specularMap",
            "binding_source": "fxo-ctab",
        },
    ]
    draw = build_static_draw_contract(packet)
    result = build_render_command(draw, _resources())
    assert result["ready"] is False
    assert "texture-command:sampler-register-collision:1" in result["blocking_reasons"]


def test_render_command_rejects_bad_sampler_state():
    packet = _packet()
    packet["submeshes"][0]["material"]["textures"][0]["sampler"] = "diffuseMap"
    resources = _resources()
    resources["samplers"][0]["state"] = {
        "format": "SHIFT.NotASamplerState/1",
        "ready": False,
        "blocking_reasons": ["sampler-min-filter:unsupported:MAGIC"],
    }
    draw = build_static_draw_contract(packet)
    result = build_render_command(draw, resources)
    assert result["ready"] is False
    assert "texture-command:sampler-state-invalid:0" in result["blocking_reasons"]
