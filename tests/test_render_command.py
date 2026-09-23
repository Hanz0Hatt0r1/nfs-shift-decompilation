from static_draw import build_static_draw_contract
from render_command import build_render_command


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
