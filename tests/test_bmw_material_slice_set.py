from copy import deepcopy

from bmw_material_slice_set import (
    FORMAT,
    build_bmw_material_slice_set,
)
from bmw_material_vulkan_adapter import (
    build_bmw_vulkan_set_from_material_slice,
)
from bmw_vulkan_bundle import TARGET_MEB


def _submesh(tag, first_index):
    vertex = """#version 450
layout(location=0) in vec3 inPosition;
void main(){ gl_Position=vec4(inPosition,1.0); }
"""
    pixel = f"""#version 450
layout(location=0) out vec4 outColor;
void main(){{ outColor=vec4({0.25 if tag == 'a' else 0.75},0.5,0.5,1.0); }}
"""
    return {
        "first_index": first_index,
        "index_count": 3,
        "shader": {
            "vertex": vertex,
            "pixel": pixel,
            "vulkan_vertex_glsl": vertex,
            "vulkan_pixel_glsl": pixel,
            "source_payload_sha256": tag * 64,
            "permutation_identity": {
                "format": "SHIFT.ShaderPermutationIdentity/1",
                "identity_sha256": tag.upper() * 64,
            },
        },
        "textures": [],
        "external_samplers": [],
        "constant_payload": {
            "format": "SHIFT.MaterialConstantPayload/1",
            "ready": True,
            "registers": [],
        },
        "constant_commands": [],
    }


def _mesh():
    return {
        "format": "SHIFT.MEB",
        "vertices": [
            [-1.0, -1.0, 0.0],
            [1.0, -1.0, 0.0],
            [1.0, 1.0, 0.0],
            [-1.0, 1.0, 0.0],
        ],
        "indices": [0, 1, 2, 0, 2, 3],
    }


def _slice(primitive_index, tag, first_index, material_ref):
    sha = "1" * 64
    command = {
        "format": "SHIFT.RenderCommand/1",
        "ready": True,
        "blocking_reasons": [],
        "mesh": {
            "ref": TARGET_MEB,
            "vertex_count": 4,
            "triangle_count": 2,
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
            "attributes": [],
            "attribute_setup": [],
        },
        "world_matrix": None,
        "submeshes": [_submesh(tag, first_index)],
        "resource_plan": {
            "format": "SHIFT.RenderResources/1",
            "texture_count": 0,
            "sampler_count": 0,
            "external_sampler_count": 0,
        },
        "validation": {"valid": True, "blocking_reasons": []},
    }
    return {
        "format": "SHIFT.BMWMaterialSlice/1",
        "ready": True,
        "blocking_reasons": [],
        "primitive_index": primitive_index,
        "material_ref": material_ref,
        "material_bmt": material_ref[:-4] + ".bmt",
        "golden_identity": {
            "resource": TARGET_MEB,
            "resource_sha256": sha,
        },
        "generic_material_gate": {
            "format": "SHIFT.BMWGenericMaterialBindingGate/1",
            "ready": True,
            "blocking_reasons": [],
        },
        "slice_golden_gate": {
            "format": "SHIFT.BMWMaterialSliceGoldenGate/1",
            "ready": True,
            "blocking_reasons": [],
        },
        "mesh": _mesh(),
        "packet": {
            "mesh": {
                "ref": TARGET_MEB,
                "resolved": {
                    "path": TARGET_MEB,
                    "resource_sha256": sha,
                },
            },
        },
        "render_command": command,
        "texture_sources": [],
        "provenance": {
            "mesh_entry": {"sha256": sha},
        },
    }


def test_material_slice_set_orders_real_primitive_slices_canonically():
    windows = _slice(
        3, "b", 3,
        "vehicles/bmw_m3_e36/GENERIC_WINDOWS.mtx",
    )
    paint = _slice(
        1, "a", 0,
        "vehicles/bmw_m3_e36/BMW_M3_E36_PAINT.mtx",
    )

    result = build_bmw_material_slice_set([windows, paint])

    assert result["format"] == FORMAT
    assert result["ready"] is True, result["blocking_reasons"]
    assert result["primitive_indices"] == [1, 3]
    assert result["draw_count"] == 2
    assert [
        row["material_ref"] for row in result["draws"]
    ] == [
        "vehicles/bmw_m3_e36/BMW_M3_E36_PAINT.mtx",
        "vehicles/bmw_m3_e36/GENERIC_WINDOWS.mtx",
    ]
    assert [
        row["first_index"]
        for row in result["render_command"]["submeshes"]
    ] == [0, 3]
    assert result["render_command"]["ready"] is True


def test_material_slice_set_rejects_duplicate_primitive_index():
    first = _slice(
        1, "a", 0,
        "vehicles/bmw_m3_e36/BMW_M3_E36_PAINT.mtx",
    )
    second = _slice(
        1, "b", 3,
        "vehicles/bmw_m3_e36/GENERIC_WINDOWS.mtx",
    )

    result = build_bmw_material_slice_set([first, second])

    assert result["ready"] is False
    assert "slice-set:duplicate-primitive-index:1" in result["blocking_reasons"]


def test_material_slice_set_rejects_mesh_identity_mismatch():
    first = _slice(
        1, "a", 0,
        "vehicles/bmw_m3_e36/BMW_M3_E36_PAINT.mtx",
    )
    second = _slice(
        3, "b", 3,
        "vehicles/bmw_m3_e36/GENERIC_WINDOWS.mtx",
    )
    second["golden_identity"]["resource_sha256"] = "2" * 64
    second["packet"]["mesh"]["resolved"]["resource_sha256"] = "2" * 64
    second["provenance"]["mesh_entry"]["sha256"] = "2" * 64

    result = build_bmw_material_slice_set([first, second])

    assert result["ready"] is False
    assert (
        "slice-set:primitive-3:mesh-sha256-differs"
        in result["blocking_reasons"]
    )


def test_material_slice_set_deduplicates_texture_provenance_and_blocks_conflict():
    first = _slice(
        1, "a", 0,
        "vehicles/bmw_m3_e36/BMW_M3_E36_PAINT.mtx",
    )
    second = _slice(
        3, "b", 3,
        "vehicles/bmw_m3_e36/GENERIC_WINDOWS.mtx",
    )
    source = {
        "path": "render/textures/shared.dds",
        "sha256": "3" * 64,
        "archive": "BMW_M3_E36.bff",
    }
    first["texture_sources"] = [source]
    second["texture_sources"] = [deepcopy(source)]

    ready = build_bmw_material_slice_set([first, second])
    assert ready["ready"] is True
    assert len(ready["texture_sources"]) == 1

    second["texture_sources"][0]["sha256"] = "4" * 64
    blocked = build_bmw_material_slice_set([first, second])
    assert blocked["ready"] is False
    assert any(
        reason.startswith("slice-set:texture-source-sha-conflict:")
        for reason in blocked["blocking_reasons"]
    )


def test_material_slice_set_feeds_phase527_vulkan_multidraw_adapter(tmp_path):
    paint = _slice(
        1, "a", 0,
        "vehicles/bmw_m3_e36/BMW_M3_E36_PAINT.mtx",
    )
    windows = _slice(
        3, "b", 3,
        "vehicles/bmw_m3_e36/GENERIC_WINDOWS.mtx",
    )
    material_set = build_bmw_material_slice_set([paint, windows])
    assert material_set["ready"] is True

    vulkan = build_bmw_vulkan_set_from_material_slice(
        material_set,
        tmp_path,
    )

    assert vulkan["ready"] is True, vulkan["blocking_reasons"]
    assert vulkan["draw_count"] == 2
    assert [
        row["source_submesh_index"] for row in vulkan["draws"]
    ] == [0, 1]
    assert (tmp_path / "bundle_set.paths").read_text(
        encoding="utf-8"
    ).splitlines() == [
        "draws/submesh_000",
        "draws/submesh_001",
    ]
