import json


def test_runtime_shader_render_forwards_exact_contract(monkeypatch, tmp_path):
    import bmw_runtime_shader_render as render

    contract = {
        "format": "SHIFT.BMWRuntimeRenderContract/1",
        "reference_render_ready": True,
        "blocking_reasons": [],
        "shader": {
            "identity": {"identity_sha256": "i" * 64},
            "candidate": {"file": "RENDER.bff::body.fxo", "program_offset": 128},
            "linked_shader_pair": {
                "vertex": {"schema": "SHIFT.ShaderProgram/1", "stage": "vertex"},
                "pixel": {"schema": "SHIFT.ShaderProgram/1", "stage": "pixel"},
            },
        },
        "constants": {
            "vertex": {"c": {"0": [1.0, 0.0, 0.0, 1.0]}},
            "pixel": {"c": {"2": [0.2, 0.3, 0.4, 1.0]}},
        },
    }
    material = {
        "format": "SHIFT.RealBMWMaterialBindingEvidence/1",
        "material_binding": {
            "bindings": [{
                "binding": "material-texture",
                "sampler": "diffuseMap",
                "d3d9_sampler_register": 1,
                "texture_resolved": "vehicles/textures/common_paint.dds",
            }]
        },
    }
    mesh = {
        "format": "SHIFT.MEB",
        "vertices": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
        "indices": [0, 1, 2],
        "uv_layers": {"130": [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]]},
        "colors": [[255, 255, 255, 255]] * 3,
        "normals": [[0.0, 0.0, 1.0]] * 3,
        "tangents": [[1.0, 0.0, 0.0]] * 3,
        "tangents2": [[0.0, 1.0, 0.0]] * 3,
    }
    contract_path = tmp_path / "contract.json"
    material_path = tmp_path / "material.json"
    mesh_path = tmp_path / "mesh.json"
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    material_path.write_text(json.dumps(material), encoding="utf-8")
    mesh_path.write_text(json.dumps(mesh), encoding="utf-8")

    class Archive:
        def __init__(self, path):
            self.path = path
            self.entries = [type("Entry", (), {
                "path": "vehicles/textures/common_paint.dds"
            })()]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def extract_entry(self, entry):
            return b"dds"

    monkeypatch.setattr(render, "BFF", Archive)
    monkeypatch.setattr(
        render,
        "decode_dds",
        lambda data: {
            "format": "SHIFT.ReferenceTexture/1",
            "width": 1,
            "height": 1,
            "pixels": [255, 20, 10, 255],
        },
    )

    captured = {}

    def fake_rasterize(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return b"P6\n1 1\n255\n\x01\x02\x03"

    monkeypatch.setattr(render, "rasterize_textured_mesh", fake_rasterize)

    output = tmp_path / "frame.ppm"
    result = render.render_runtime_shader(
        contract_path,
        material_path,
        mesh_path,
        tmp_path / "BMW_M3_E36.bff",
        output,
    )

    assert result["format"] == "SHIFT.BMWRuntimeShaderRender/1"
    assert result["shader_execution"] is True
    assert captured["args"][0] == mesh["vertices"]
    assert captured["args"][1] == mesh["indices"]
    assert captured["kwargs"]["vertex_program"]["schema"] == "SHIFT.ShaderProgram/1"
    assert captured["kwargs"]["pixel_program"]["stage"] == "pixel"
    assert captured["kwargs"]["uv_layers"] == mesh["uv_layers"]
    assert captured["kwargs"]["semantic_rows"][("COLOR", 0)] == mesh["colors"]
    assert captured["kwargs"]["texture_images"][1]["pixels"] == [255, 20, 10, 255]
    assert output.read_bytes().startswith(b"P6\n1 1\n255\n")



def _write_ppm(path, rgb=(10, 20, 30)):
    path.write_bytes(
        b"P6\n1 1\n255\n" + bytes(rgb)
    )


def test_runtime_render_contract_loads_captured_sampler_snapshots(tmp_path):
    import bmw_runtime_shader_render as render

    s0 = tmp_path / "s0.ppm"
    _write_ppm(s0, (20, 30, 40))

    cube_paths = {}
    for face in ("px", "nx", "py", "ny", "pz", "nz"):
        path = tmp_path / f"s3_{face}.ppm"
        _write_ppm(path, (50, 60, 70))
        cube_paths[face] = path

    contract = {
        "external_textures": [
            {
                "d3d9_sampler_register": 0,
                "snapshot_status": "captured",
                "snapshot_paths": [str(s0)],
            },
            {
                "d3d9_sampler_register": 3,
                "snapshot_status": "captured",
                "snapshot_paths": [str(cube_paths[face]) for face in ("px", "nx", "py", "ny", "pz", "nz")],
            },
        ]
    }

    images, resources = render._contract_snapshot_resources(contract, None)
    assert images[0]["format"] == "SHIFT.ReferenceTexture/1"
    assert resources[3]["format"] == "SHIFT.ReferenceCubeTexture/1"
    assert set(resources[3]["faces"]) == {"px", "nx", "py", "ny", "pz", "nz"}
