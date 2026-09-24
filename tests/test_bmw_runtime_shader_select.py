from bmw_runtime_shader_select import select_runtime_shader


def _material():
    return {
        "format": "SHIFT.RealBMWMaterialBindingEvidence/1",
        "provenance": {
            "mesh_entry": {
                "path": "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb",
                "sha256": "m" * 64,
            }
        },
        "material_binding": {
            "fxo_candidates": [
                {
                    "file": "RENDER.bff::a.fxo",
                    "program_offset": 100,
                    "pixel_sha256": "p" * 64,
                    "vertex_sha256": "v" * 64,
                    "pair_sha256": "q" * 64,
                    "permutation_identity": {
                        "identity_sha256": "i" * 64
                    },
                },
                {
                    "file": "RENDER.bff::b.fxo",
                    "program_offset": 200,
                    "pixel_sha256": "x" * 64,
                    "vertex_sha256": "y" * 64,
                    "pair_sha256": "z" * 64,
                    "permutation_identity": {
                        "identity_sha256": "j" * 64
                    },
                },
            ]
        },
    }


def _frame(identity, resource_sha="m" * 64, frame=17):
    return {
        "frame": frame,
        "vertex_declaration": {
            "resource_sha256": resource_sha,
            "resource_path": "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb",
        },
        "shader_permutation_identity": identity,
    }


def test_select_runtime_shader_matches_exact_identity_and_resource():
    report = select_runtime_shader(
        _material(),
        {
            "format": "SHIFT.D3D9RuntimeBindingEvidence/1",
            "frames": [_frame({
                "format": "SHIFT.ShaderPermutationIdentity/1",
                "identity_sha256": "i" * 64,
                "pair_byte_sha256": "q" * 64,
            })],
        },
    )
    assert report["status"] == "match"
    assert report["ready"] is True
    assert report["selected"]["candidate_file"].endswith("a.fxo")
    assert report["selected"]["score"] == 100
    assert "identity_sha256" in report["selected"]["evidence"]


def test_select_runtime_shader_falls_back_to_exact_pair_byte_hash():
    material = _material()
    material["material_binding"]["fxo_candidates"][0]["permutation_identity"] = None
    report = select_runtime_shader(
        material,
        {
            "format": "SHIFT.D3D9RuntimeBindingEvidence/1",
            "frames": [_frame({
                "format": "SHIFT.ShaderPermutationIdentity/1",
                "identity_sha256": "missing",
                "pair_byte_sha256": "q" * 64,
            })],
        },
    )
    assert report["status"] == "match"
    assert report["selected"]["score"] == 90
    assert report["selected"]["candidate_program_offset"] == 100


def test_select_runtime_shader_is_fail_closed_on_multiple_exact_matches():
    material = _material()
    duplicate = dict(material["material_binding"]["fxo_candidates"][0])
    duplicate["file"] = "RENDER.bff::duplicate.fxo"
    duplicate["program_offset"] = 300
    material["material_binding"]["fxo_candidates"].append(duplicate)

    identity = {
        "format": "SHIFT.ShaderPermutationIdentity/1",
        "identity_sha256": "i" * 64,
    }
    report = select_runtime_shader(
        material,
        {
            "format": "SHIFT.D3D9RuntimeBindingEvidence/1",
            "frames": [_frame(identity)],
        },
    )
    assert report["status"] == "ambiguous"
    assert report["ready"] is False
    assert report["blocking_reasons"] == [
        "runtime:multiple-exact-shader-candidates"
    ]


def test_select_runtime_shader_rejects_wrong_resource_by_default():
    report = select_runtime_shader(
        _material(),
        {
            "format": "SHIFT.D3D9RuntimeBindingEvidence/1",
            "frames": [_frame(
                {
                    "identity_sha256": "i" * 64,
                    "pair_byte_sha256": "q" * 64,
                },
                resource_sha="wrong",
            )],
        },
    )
    assert report["status"] == "not-found"
    assert report["blocking_reasons"] == [
        "runtime:exact-shader-and-resource-instance-not-found"
    ]

def test_select_runtime_shader_requires_external_texture_stages():
    material = _material()
    material["material_binding"]["bindings"] = [
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
    runtime = {
        "format": "SHIFT.D3D9RuntimeBindingEvidence/1",
        "frames": [{
            **_frame({
                "format": "SHIFT.ShaderPermutationIdentity/1",
                "identity_sha256": "i" * 64,
            }),
            "texture_bindings": [],
        }],
    }
    report = select_runtime_shader(material, runtime)
    assert report["status"] == "not-found"
    assert report["blocking_reasons"] == [
        "runtime:exact-shader-and-resource-instance-not-found"
    ]


def test_select_runtime_shader_accepts_external_texture_stage_bindings():
    material = _material()
    material["material_binding"]["bindings"] = [
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
    runtime = {
        "format": "SHIFT.D3D9RuntimeBindingEvidence/1",
        "frames": [{
            **_frame({
                "format": "SHIFT.ShaderPermutationIdentity/1",
                "identity_sha256": "i" * 64,
            }),
            "texture_bindings": [
                {"stage": 0, "texture_ptr": "0x100"},
                {"stage": 3, "texture_ptr": "0x300"},
            ],
        }],
    }
    report = select_runtime_shader(material, runtime)
    assert report["status"] == "match"
    assert report["selected"]["external_texture_stages"] == [0, 3]



def test_select_runtime_shader_blocks_external_texture_type_mismatch():
    material = _material()
    material["material_binding"]["bindings"] = [
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
    frame = _frame({
        "format": "SHIFT.ShaderPermutationIdentity/1",
        "identity_sha256": "i" * 64,
    })
    frame["texture_bindings"] = [
        {"stage": 0, "texture_ptr": "0x100", "resource_type_name": "texture2d"},
        {"stage": 3, "texture_ptr": "0x300", "resource_type_name": "texture2d"},
    ]
    report = select_runtime_shader(
        material,
        {"format": "SHIFT.D3D9RuntimeBindingEvidence/1", "frames": [frame]},
    )
    assert report["status"] == "not-found"


def test_select_runtime_shader_accepts_expected_external_texture_types():
    material = _material()
    material["material_binding"]["bindings"] = [
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
    frame = _frame({
        "format": "SHIFT.ShaderPermutationIdentity/1",
        "identity_sha256": "i" * 64,
    })
    frame["texture_bindings"] = [
        {"stage": 0, "texture_ptr": "0x100", "resource_type_name": "texture2d"},
        {"stage": 3, "texture_ptr": "0x300", "resource_type_name": "cube_texture"},
    ]
    report = select_runtime_shader(
        material,
        {"format": "SHIFT.D3D9RuntimeBindingEvidence/1", "frames": [frame]},
    )
    assert report["status"] == "match"
    assert report["selected"]["external_texture_types"] == {
        0: "texture2d",
        3: "cube_texture",
    }
