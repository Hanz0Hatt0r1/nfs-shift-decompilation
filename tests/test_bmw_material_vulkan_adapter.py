import json

from bmw_vulkan_bundle import TARGET_MEB
from bmw_material_vulkan_adapter import build_bmw_vulkan_from_material_slice


def _slice():
    return {
        "format": "SHIFT.BMWRealMaterialSlice/1",
        "render_command": {
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
                    "vulkan_vertex_glsl": "#version 450\nvoid main(){gl_Position=vec4(0.0);}",
                    "vulkan_pixel_glsl": "#version 450\nlayout(location=0) out vec4 o;void main(){o=vec4(1.0);}",
                },
                "constant_commands": [],
                "constant_payload": {"registers": [], "ready": True},
                "textures": [],
                "external_samplers": [],
                "first_index": 0,
                "index_count": 3,
            }],
        },
        "mesh": {
            "format": "SHIFT.MEB",
            "vertices": [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
            "indices": [0, 1, 2],
        },
    }


def test_material_slice_becomes_bmw_vulkan_bundle(tmp_path):
    result = build_bmw_vulkan_from_material_slice(_slice(), tmp_path)
    assert result["format"] == "SHIFT.BMWMaterialSliceVulkan/1"
    assert result["ready"] is True
    assert result["source"]["mesh_ref"] == TARGET_MEB
    assert (tmp_path / "geometry.svpk").exists()
    assert (tmp_path / "constants.svcp").exists()
    assert (tmp_path / "material_slice_source.json").exists()


def test_material_slice_rejects_foreign_mesh(tmp_path):
    payload = _slice()
    payload["render_command"]["mesh"]["ref"] = "vehicles/other/body.meb"
    try:
        build_bmw_vulkan_from_material_slice(payload, tmp_path)
    except ValueError as error:
        assert "exact KIT00 body MEB" in str(error)
    else:
        raise AssertionError("foreign mesh must be rejected")


def test_material_slice_rejects_missing_vulkan_shader_source(tmp_path):
    payload = _slice()
    payload["render_command"]["submeshes"][0]["shader"].pop("vulkan_pixel_glsl")
    result = build_bmw_vulkan_from_material_slice(payload, tmp_path)
    assert result["ready"] is False
    assert "bmw-material-vulkan:vulkan-pixel-source-missing:0" in result["blocking_reasons"]
