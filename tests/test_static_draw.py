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
                    "uniform_binding": {"bindings": []},
                },
                "textures": [{
                    "material_parameter": "Diffuse",
                    "ref": "textures/body.dds",
                    "slot": 1 if source == "fxo-ctab" else None,
                    "sampler": "diffuseMap" if source == "fxo-ctab" else None,
                    "sampler_type": "sampler2D" if source == "fxo-ctab" else None,
                    "binding_source": source,
                    "resolved": [{"path": "textures/body.dds"}] if source == "fxo-ctab" else [],
                }],
            },
        }],
    }


def test_static_draw_contract_accepts_explicit_unique_binding():
    r = build_static_draw_contract(_packet())
    assert r["ready"] is True
    assert r["blocking_reasons"] == []
    assert r["submeshes"][0]["material"]["textures"][0]["slot"] == 1


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
