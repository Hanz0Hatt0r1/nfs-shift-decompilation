from bmw_runtime_render_contract import build_runtime_render_contract


def _material():
    return {
        "format": "SHIFT.RealBMWMaterialBindingEvidence/1",
        "material_binding": {
            "bindings": [
                {
                    "binding": "external-or-specialised",
                    "sampler": "sShadowMap_f1_0",
                    "d3d9_sampler_register": 0,
                    "sampler_type": "sampler2D",
                },
                {
                    "binding": "external-or-specialised",
                    "sampler": "environmentMap",
                    "d3d9_sampler_register": 3,
                    "sampler_type": "samplerCube",
                },
            ]
        },
        "provenance": {
            "mesh_entry": {
                "path": "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb",
                "sha256": "m" * 64,
            }
        },
    }


def _runtime():
    return {
        "format": "SHIFT.D3D9RuntimeBindingEvidence/1",
        "frames": [{
            "frame": 22,
            "vertex_declaration": {
                "declaration_ptr": "0x20",
                "resource_path": "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb",
                "resource_sha256": "m" * 64,
                "bound_declaration_valid": True,
            },
            "vertex_shader": {
                "shader_ptr": "0x50",
                "create_known": True,
            },
            "pixel_shader": {
                "shader_ptr": "0x60",
                "create_known": True,
            },
            "shader_permutation_identity": {
                "format": "SHIFT.ShaderPermutationIdentity/1",
                "identity_sha256": "i" * 64,
                "pair_byte_sha256": "q" * 64,
                "payload": {
                    "vertex": {"byte_sha256": "v" * 64},
                    "pixel": {"byte_sha256": "p" * 64},
                },
            },
            "constant_writes": [{
                "stage": "pixel",
                "start_register": 20,
                "vector4f_count": 1,
                "values": [1.0, 0.0, 0.0, 1.0],
            }],
            "texture_bindings": [
                {"stage": 0, "texture_ptr": "0x100"},
                {"stage": 3, "texture_ptr": "0x300"},
            ],
            "draws": [{
                "primitive_count": 100,
                "start_index": 150,
                "base_vertex_index": 0,
            }],
        }]
    }


def _selection():
    return {
        "format": "SHIFT.BMWRuntimeShaderSelection/1",
        "status": "match",
        "ready": True,
        "blocking_reasons": [],
        "selected": {
            "frame": 22,
            "candidate_file": "RENDER.bff::paint.fxo",
            "candidate_program_offset": 128,
            "score": 100,
        },
    }


def test_runtime_render_contract_is_ready_with_complete_frame():
    report = build_runtime_render_contract(_material(), _runtime(), _selection())
    assert report["format"] == "SHIFT.BMWRuntimeRenderContract/1"
    assert report["ready_for_shader_reference"] is True
    assert report["blocking_reasons"] == []
    assert report["render_input"]["shader"]["identity_sha256"] == "i" * 64
    assert report["render_input"]["external_samplers"] == [
        {"stage": 0, "texture_ptr": "0x100", "resource": "runtime-external"},
        {"stage": 3, "texture_ptr": "0x300", "resource": "runtime-external"},
    ]
    assert report["render_input"]["constant_banks"]["pixel"]["20"] == [1.0, 0.0, 0.0, 1.0]


def test_runtime_render_contract_blocks_when_external_texture_is_missing():
    runtime = _runtime()
    runtime["frames"][0]["texture_bindings"] = [{"stage": 0, "texture_ptr": "0x100"}]
    report = build_runtime_render_contract(_material(), runtime, _selection())
    assert report["ready_for_shader_reference"] is False
    assert "runtime:external-texture-bindings-missing:3" in report["blocking_reasons"]


def test_runtime_render_contract_blocks_when_resource_identity_is_unknown():
    runtime = _runtime()
    runtime["frames"][0]["vertex_declaration"].pop("resource_sha256")
    runtime["frames"][0]["vertex_declaration"].pop("resource_path")
    report = build_runtime_render_contract(_material(), runtime, _selection())
    assert report["ready_for_shader_reference"] is False
    assert "runtime:same-meb-resource-not-proven" in report["blocking_reasons"]
