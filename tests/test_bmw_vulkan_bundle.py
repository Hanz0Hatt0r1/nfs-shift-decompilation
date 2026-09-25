import json
from pathlib import Path

from bmw_vulkan_bundle import TARGET_MEB, build_bmw_vulkan_bundle


def _command():
    return {
        "format": "SHIFT.RenderCommand/1",
        "mesh": {
            "ref": TARGET_MEB,
            "resolved": {"resource_sha256": "a" * 64},
            "vertex_count": 3,
            "triangle_count": 1,
            "vertex_layout": {
                "format": "SHIFT.VertexLayout/1",
                "buffer_stride": 12,
                "attributes": [{
                    "property_id": "200",
                    "usage": "POSITION",
                    "usage_index": 0,
                    "location": 0,
                    "offset": 0,
                    "stride": 12,
                    "storage": "FLOAT32x3",
                    "android": "FLOAT32x3",
                    "components": 3,
                    "normalized": False,
                    "element_size": 12,
                    "abi_status": "proven",
                }],
            },
        },
        "submeshes": [{
            "shader": {
                "vertex": "#version 450\nvoid main(){}",
                "pixel": "#version 450\nvoid main(){}",
            },
            "constant_commands": [],
            "constant_payload": {"format": "SHIFT.MaterialConstantPayload/1", "registers": [], "ready": True},
            "textures": [],
            "external_samplers": [],
            "first_index": 0,
            "index_count": 3,
        }],
    }


def _mesh():
    return {
        "format": "SHIFT.MEB",
        "vertices": [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
        "indices": [0, 1, 2],
    }


def test_bmw_vulkan_bundle_prepares_geometry_constants_and_shaders(tmp_path):
    result = build_bmw_vulkan_bundle(_command(), _mesh(), tmp_path)

    assert result["format"] == "SHIFT.BMWVulkanBundle/1"
    assert result["ready"] is True
    assert result["target"]["meb"] == TARGET_MEB
    assert result["artifacts"]["geometry"]["ready"] is True
    assert result["artifacts"]["constants"]["ready"] is True
    assert len(result["artifacts"]["shaders"]) == 2
    assert (tmp_path / "geometry.svpk").exists()
    assert (tmp_path / "constants.svcp").exists()
    assert (tmp_path / "bundle_manifest.json").exists()

    manifest = json.loads((tmp_path / "bundle_manifest.json").read_text(encoding="utf-8"))
    assert manifest["format"] == "SHIFT.BMWVulkanBundle/1"


def test_bmw_vulkan_bundle_requires_exact_bmw_m3_mesh_reference(tmp_path):
    command = _command()
    command["mesh"]["ref"] = "vehicles/other/body.meb"
    try:
        build_bmw_vulkan_bundle(command, _mesh(), tmp_path)
    except ValueError as error:
        assert "exact M3 KIT00 body MEB" in str(error)
    else:
        raise AssertionError("foreign MEB must be blocked")


def test_bmw_vulkan_bundle_blocks_missing_material_textures(tmp_path):
    command = _command()
    command["submeshes"][0]["textures"] = [{
        "d3d9_sampler_register": 1,
        "resource_binding_id": 1,
        "texture_id": 2,
        "sampler_id": 3,
    }]
    result = build_bmw_vulkan_bundle(command, _mesh(), tmp_path)
    assert result["ready"] is False
    assert "bmw-vulkan-bundle:material-textures-not-supplied" in result["blocking_reasons"]
