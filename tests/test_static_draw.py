from static_draw import build_static_draw_contract


def _packet(source="fxo-ctab"):
    return {
        "scene": {"archive": "CAR.bff", "path": "cars/body.vhf"},
        "node": {"name": "BODY", "type": "OBJECT", "matrix": "0"},
        "mesh": {
            "ref": "cars/body.meb",
            "resolved": {"path": "cars/body.meb"},
            "vertex_count": 3,
            "triangle_count": 1,
            "vertex_layout": {
                "format": "SHIFT.VertexLayout/1",
                "buffer_stride": 32,
                "attributes": [{"property_id": "200", "location": 0, "offset": 0, "element_size": 12}],
            },
        },
        "submeshes": [{
            "first_index": 0,
            "index_count": 3,
            "material": {
                "name": "BODY",
                "shader_selection": {
                    "status": "unique",
                    "shader_pair": {
                        "selection_status": "unique",
                        "interface": {"valid": True},
                        "vertex_format": {"valid": True},
                    },
                    "linked_shader_pair": {
                        "format": "SHIFT.LinkedShaderPair/1",
                        "varying_locations": [],
                        "vertex_input_locations": {0: 0},
                        "vertex_glsl": "#version 310 es\n",
                        "pixel_glsl": "#version 310 es\n",
                    },
                    "uniform_binding": {"bindings": []},
                },
                "textures": [{
                    "material_parameter": "Diffuse",
                    "ref": "textures/body.dds",
                    "slot": 1 if source == "fxo-ctab" else None,
                    "d3d9_sampler_register": 1 if source == "fxo-ctab" else None,
                    "sampler": "diffuseMap" if source == "fxo-ctab" else None,
                    "sampler_type": "sampler2D" if source == "fxo-ctab" else None,
                    "binding_source": source,
                    "resolved": [{"path": "textures/body.dds"}] if source == "fxo-ctab" else [],
                }],
            },
        }],
    }


def _binding_packet():
    packet = _packet()
    material = packet["submeshes"][0]["material"]
    material["shader_selection"] = {
        "selection_status": "unique",
        "shader_pair": {
            "selection_status": "unique",
            "interface": {"valid": True},
            "vertex_format": {"valid": True},
            "vertex_bindings": [],
        },
        "linked_shader_pair": {
            "format": "SHIFT.LinkedShaderPair/1",
            "varying_locations": [],
            "vertex_input_locations": {0: 0},
            "vertex_glsl": "#version 310 es\n",
            "pixel_glsl": "#version 310 es\n",
        },
        "uniform_binding": {"bindings": []},
    }
    return packet


def test_static_draw_contract_accepts_explicit_unique_binding():
    r = build_static_draw_contract(_packet())
    assert r["ready"] is True
    assert r["blocking_reasons"] == []
    assert r["submeshes"][0]["material"]["textures"][0]["slot"] == 1


def test_static_draw_contract_accepts_direct_material_binding_shape():
    packet = _binding_packet()
    material = packet["submeshes"][0]["material"]
    material.pop("shader_selection")
    material.update({
        "selection_status": "unique",
        "shader_pair": {
            "selection_status": "unique",
            "interface": {"valid": True},
            "vertex_format": {"valid": True},
            "vertex_bindings": [],
        },
        "linked_shader_pair": {
            "format": "SHIFT.LinkedShaderPair/1",
            "varying_locations": [],
            "vertex_input_locations": {0: 0},
            "vertex_glsl": "#version 310 es\n",
            "pixel_glsl": "#version 310 es\n",
        },
        "uniform_binding": {"bindings": []},
    })
    r = build_static_draw_contract(packet)
    assert r["ready"] is True
    assert r["blocking_reasons"] == []
    assert r["submeshes"][0]["material"]["shader_selection"]["selection_status"] == "unique"


def test_static_draw_contract_rejects_inferred_texture_binding():
    r = build_static_draw_contract(_packet("unresolved"))
    assert r["ready"] is False
    assert "material-texture-binding:unresolved" in r["blocking_reasons"]


def test_static_draw_contract_rejects_ambiguous_shader_pair():
    packet = _packet()
    packet["submeshes"][0]["material"]["shader_selection"]["status"] = "ambiguous"
    packet["submeshes"][0]["material"]["shader_selection"]["shader_pair"]["selection_status"] = "ambiguous"
    r = build_static_draw_contract(packet)
    assert r["ready"] is False
    assert "shader-selection:ambiguous" in r["blocking_reasons"]


def test_static_draw_blocks_ambiguous_vertex_abi_when_shader_uses_it():
    packet = _packet()
    packet["mesh"]["vertex_layout"]["attributes"].append({
        "property_id": "460",
        "location": 1,
        "offset": 12,
        "element_size": 4,
        "abi_status": "ambiguous",
    })
    packet["submeshes"][0]["material"]["shader_selection"]["shader_pair"]["vertex_bindings"] = [{
        "property_id": "460",
        "matched": True,
    }]
    r = build_static_draw_contract(packet)
    assert r["ready"] is False
    assert "vertex-layout:ambiguous-attribute:460" in r["blocking_reasons"]


def test_static_draw_allows_unused_ambiguous_vertex_abi():
    packet = _packet()
    packet["mesh"]["vertex_layout"]["attributes"].append({
        "property_id": "460",
        "location": 1,
        "offset": 12,
        "element_size": 4,
        "abi_status": "ambiguous",
    })
    packet["submeshes"][0]["material"]["shader_selection"]["shader_pair"]["vertex_bindings"] = []
    r = build_static_draw_contract(packet)
    assert r["ready"] is True


def test_static_draw_blocks_missing_linked_glsl_pair():
    packet = _packet()
    del packet["submeshes"][0]["material"]["shader_selection"]["linked_shader_pair"]
    r = build_static_draw_contract(packet)
    assert r["ready"] is False
    assert "shader-glsl:missing" in r["blocking_reasons"]


def test_static_draw_blocks_linked_glsl_translation_error():
    packet = _packet()
    packet["submeshes"][0]["material"]["shader_selection"]["linked_shader_error"] = "ValueError: translator"
    r = build_static_draw_contract(packet)
    assert r["ready"] is False
    assert "shader-glsl:error" in r["blocking_reasons"]


def test_static_draw_accepts_valid_uniform_binding():
    packet = _packet()
    packet["submeshes"][0]["material"]["shader_selection"]["uniform_binding"] = {
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
    result = build_static_draw_contract(packet)
    assert result["ready"] is True
    assert result["blocking_reasons"] == []


def test_static_draw_rejects_uniform_binding_with_unexpected_register_set():
    packet = _packet()
    packet["submeshes"][0]["material"]["shader_selection"]["uniform_binding"] = {
        "format": "SHIFT.MaterialUniformBinding/1",
        "bindings": [{
            "name": "primerBasis",
            "binding": "unexpected-register-set",
            "register_set": 3,
            "register_index": 5,
            "register_count": 1,
        }],
    }
    result = build_static_draw_contract(packet)
    assert result["ready"] is False
    assert "material-uniform-binding:register-set:3" in result["blocking_reasons"]


def test_static_draw_rejects_uniform_shape_warning():
    packet = _packet()
    packet["submeshes"][0]["material"]["shader_selection"]["uniform_binding"] = {
        "format": "SHIFT.MaterialUniformBinding/1",
        "bindings": [{
            "name": "primerBasis",
            "binding": "material-constant",
            "register_set": 2,
            "register_index": 5,
            "register_count": 1,
            "shape_warning": "value-exceeds-register-range",
        }],
    }
    result = build_static_draw_contract(packet)
    assert result["ready"] is False
    assert "material-uniform-binding:value-exceeds-register-range" in result["blocking_reasons"]


def test_static_draw_rejects_nonempty_uniform_binding_without_schema():
    packet = _packet()
    packet["submeshes"][0]["material"]["shader_selection"]["uniform_binding"] = {
        "bindings": [{
            "name": "primerBasis",
            "binding": "material-constant",
            "register_set": 2,
            "register_index": 5,
            "register_count": 1,
        }],
    }
    result = build_static_draw_contract(packet)
    assert result["ready"] is False
    assert "material-uniform-binding:invalid" in result["blocking_reasons"]


def test_static_draw_rejects_unresolved_direct_material_texture():
    packet = _binding_packet()
    material = packet["submeshes"][0]["material"]
    material["bindings"] = [{
        "sampler": "diffuseMap",
        "texture": "textures/body.dds",
        "texture_resolved": None,
        "binding": "material-texture",
    }]
    material.pop("textures", None)
    result = build_static_draw_contract(packet)
    assert result["ready"] is False
    assert "material-texture-binding:unresolved" in result["blocking_reasons"]


def test_static_draw_accepts_resolved_direct_material_texture_path():
    packet = _binding_packet()
    material = packet["submeshes"][0]["material"]
    material["bindings"] = [{
        "sampler": "diffuseMap",
        "texture": "textures/body.dds",
        "texture_resolved": "textures/body.dds",
        "binding": "material-texture",
    }]
    material.pop("textures", None)
    result = build_static_draw_contract(packet)
    assert result["ready"] is True
    assert result["blocking_reasons"] == []


def test_static_draw_keeps_external_specialized_texture_as_external_requirement():
    packet = _binding_packet()
    material = packet["submeshes"][0]["material"]
    material["bindings"] = [{
        "sampler": "environmentMap",
        "texture": None,
        "binding": "external-or-specialised",
    }]
    material.pop("textures", None)
    result = build_static_draw_contract(packet)
    assert result["ready"] is True
    assert result["submeshes"][0]["material"]["textures"][0]["resolution_status"] == "external"
