from copy import deepcopy
from pathlib import Path
import hashlib
import json
import struct

from bmw_vulkan_bundle import TARGET_MEB
from bmw_material_vulkan_adapter import (\n    build_bmw_vulkan_from_material_slice,\n    build_bmw_vulkan_set_from_material_slice,\n)


def _slice():
    return {
        "format": "SHIFT.BMWRealMaterialSlice/1",
        "render_command": {
            "format": "SHIFT.RenderCommand/1",
            "ready": True,
            "validation": {"valid": True, "blocking_reasons": []},
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
                    "source_payload_sha256": "a" * 64,
                    "permutation_identity": {
                        "format": "SHIFT.ShaderPermutationIdentity/1",
                        "identity_sha256": "b" * 64,
                    },
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


def _multi_slice():
    payload = _slice()
    command = payload["render_command"]
    command["mesh"]["vertex_count"] = 4
    command["mesh"]["triangle_count"] = 2
    payload["mesh"] = {
        "format": "SHIFT.MEB",
        "vertices": [
            [-1.0, -1.0, 0.0],
            [1.0, -1.0, 0.0],
            [1.0, 1.0, 0.0],
            [-1.0, 1.0, 0.0],
        ],
        "indices": [0, 1, 2, 0, 2, 3],
    }
    first = command["submeshes"][0]
    first["first_index"] = 0
    first["index_count"] = 3
    second = deepcopy(first)
    second["shader"]["source_payload_sha256"] = "c" * 64
    second["shader"]["permutation_identity"]["identity_sha256"] = "d" * 64
    second["first_index"] = 3
    second["index_count"] = 3
    command["submeshes"].append(second)
    return payload


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



class FakeDDSEntry:
    def __init__(self, path):
        self.path = path
        self.index = 7


class FakeDDSArchive:
    def __init__(self, path, payload):
        self.path = Path(path)
        self.entries = [FakeDDSEntry("render/textures/diffuse.dds")]
        self.payload = payload

    def extract_entry(self, entry):
        return self.payload

    def close(self):
        pass


def _tiny_dds():
    header = struct.pack(
        "<31I",
        124, 0, 4, 4, 0, 0, 1,
        *([0] * 11),
        32, 0x4, struct.unpack("<I", b"DXT1")[0], 0,
        0, 0, 0, 0,
        0x1000, 0, 0, 0, 0,
    )
    return b"DDS " + header + struct.pack("<HHI", 0xF800, 0x07E0, 0)


def test_material_slice_can_bridge_exact_bff_dds_into_vulkan_packet(monkeypatch, tmp_path):
    source = tmp_path / "Textures.bff"
    source.write_bytes(b"fixture-bff")
    dds_payload = _tiny_dds()
    monkeypatch.setattr(
        "bmw_material_vulkan_adapter.BFF",
        lambda path: FakeDDSArchive(source, dds_payload),
    )

    payload = _slice()
    payload["render_command"]["submeshes"][0]["textures"] = [{
        "sampler": "diffuseMap",
        "d3d9_sampler_register": 1,
        "ref": "render/textures/diffuse.dds",
        "sampler_state": {
            "min_filter": "LINEAR",
            "mag_filter": "LINEAR",
            "address_u": "REPEAT",
            "address_v": "REPEAT",
        },
    }]
    payload["texture_sources"] = [{
        "archive": source.name,
        "path": "render/textures/diffuse.dds",
        "sha256": hashlib.sha256(dds_payload).hexdigest(),
        "analysis": {"format": "DDS", "width": 4, "height": 4},
    }]

    result = build_bmw_vulkan_from_material_slice(
        payload,
        tmp_path / "out",
        source_bffs=[source],
    )

    assert result["format"] == "SHIFT.BMWMaterialSliceVulkan/1"
    assert result["blocking_reasons"] == [], result["blocking_reasons"]
    assert result["ready"] is True, result["blocking_reasons"]
    assert result["bundle"]["artifacts"]["textures"]["path"] == "textures.svtp"
    assert result["dds_bridge"]["ready"] is True
    assert result["dds_bridge"] == result["bundle"]["dds_bridge"]
    assert result["dds_bridge"]["blocking_reasons"] == []
    assert result["source"]["dds_sources"][0]["source_sha256"] == hashlib.sha256(dds_payload).hexdigest()
    assert "temporary_path" not in result["source"]["dds_sources"][0]
    assert "shift_bmw_dds_" not in result["dds_bridge"]["decoded_sources"][0]["source_path"]
    persisted = json.loads((tmp_path / "out" / "dds_sources.json").read_text(encoding="utf-8"))
    assert "shift_bmw_dds_" not in persisted["sources"][0]["source_path"]
    assert result["source"]["dds_source_bffs"] == [source.name]
    assert (tmp_path / "out" / "textures.svtp").is_file()


def test_material_slice_blocks_when_exact_bff_dds_sha_mismatches(monkeypatch, tmp_path):
    source = tmp_path / "Textures.bff"
    source.write_bytes(b"fixture-bff")
    dds_payload = _tiny_dds()
    monkeypatch.setattr(
        "bmw_material_vulkan_adapter.BFF",
        lambda path: FakeDDSArchive(source, dds_payload),
    )

    payload = _slice()
    payload["render_command"]["submeshes"][0]["textures"] = [{
        "sampler": "diffuseMap",
        "d3d9_sampler_register": 1,
        "ref": "render/textures/diffuse.dds",
        "sampler_state": {
            "min_filter": "LINEAR",
            "mag_filter": "LINEAR",
            "address_u": "REPEAT",
            "address_v": "REPEAT",
        },
    }]
    payload["texture_sources"] = [{
        "archive": source.name,
        "path": "render/textures/diffuse.dds",
        "sha256": "0" * 64,
    }]

    result = build_bmw_vulkan_from_material_slice(
        payload,
        tmp_path / "out",
        source_bffs=[source],
    )

    assert result["ready"] is False
    assert any(
        reason.startswith("bmw-material-vulkan:dds-source-sha256-mismatch:")
        for reason in result["blocking_reasons"]
    )
    assert result["dds_bridge"]["ready"] is False
    assert result["dds_bridge"]["status"] == "blocked"


def test_adapter_merge_recomputes_ready_from_final_blockers(tmp_path):
    from bmw_material_vulkan_adapter import _merge_dds_bridge_into_bundle
    bundle = {
        "ready": True,
        "status": "ready",
        "blocking_reasons": [],
        "artifacts": {},
        "external_samplers": [],
    }
    bridge = {
        "format": "SHIFT.VulkanDDSResourceBridge/1",
        "ready": False,
        "blocking_reasons": ["dds-bridge:test-blocker"],
        "packets": {"textures": None, "environment_cube": None},
        "provenance": None,
    }
    merged = _merge_dds_bridge_into_bundle(bundle, bridge, tmp_path)
    assert merged["ready"] is False
    assert merged["status"] == "partial"
    assert merged["blocking_reasons"] == ["dds-bridge:test-blocker"]


def test_material_slice_set_builds_all_submeshes_into_canonical_children(tmp_path):
    result = build_bmw_vulkan_set_from_material_slice(
        _multi_slice(),
        tmp_path,
    )

    assert result["format"] == "SHIFT.BMWMaterialSliceVulkanSet/1"
    assert result["ready"] is True, result["blocking_reasons"]
    assert result["draw_count"] == 2
    assert result["bundle_set"]["format"] == "SHIFT.BMWVulkanBundleSet/1"
    assert result["bundle_set"]["ready"] is True
    assert [
        row["source_submesh_index"] for row in result["draws"]
    ] == [0, 1]
    assert (tmp_path / "bundle_set.paths").read_text(
        encoding="utf-8"
    ).splitlines() == [
        "draws/submesh_000",
        "draws/submesh_001",
    ]

    for index in (0, 1):
        child = tmp_path / "draws" / f"submesh_{index:03d}"
        source = json.loads(
            (child / "material_slice_source.json").read_text(
                encoding="utf-8"
            )
        )
        manifest = json.loads(
            (child / "bundle_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        assert source["submesh_index"] == index
        assert manifest["format"] == "SHIFT.BMWVulkanBundle/1"
        assert manifest["source"]["submesh_index"] == index

    top_source = json.loads(
        (tmp_path / "material_slice_set_source.json").read_text(
            encoding="utf-8"
        )
    )
    assert top_source["selected_submesh_indices"] == [0, 1]


def test_material_slice_set_preserves_explicit_draw_order(tmp_path):
    result = build_bmw_vulkan_set_from_material_slice(
        _multi_slice(),
        tmp_path,
        submesh_indices=[1, 0],
    )

    assert result["ready"] is True
    assert [
        row["source_submesh_index"] for row in result["draws"]
    ] == [1, 0]
    assert (tmp_path / "bundle_set.paths").read_text(
        encoding="utf-8"
    ).splitlines() == [
        "draws/submesh_001",
        "draws/submesh_000",
    ]


def test_material_slice_set_keeps_ready_children_when_one_gate_blocks(tmp_path):
    payload = _multi_slice()
    payload["render_command"]["submeshes"][1]["shader"].pop(
        "source_payload_sha256"
    )

    result = build_bmw_vulkan_set_from_material_slice(
        payload,
        tmp_path,
    )

    assert result["ready"] is False
    assert result["draws"][0]["ready"] is True
    assert result["draws"][1]["ready"] is False
    assert result["bundle_set"]["draws"][0]["ready"] is True
    assert result["bundle_set"]["draws"][1]["ready"] is False
    assert any(
        reason.startswith(
            "bmw-material-vulkan-set:submesh-1:"
            "native-submission:shader-payload-identity-missing"
        )
        for reason in result["blocking_reasons"]
    )
    assert any(
        reason.startswith(
            "bundle-set:submesh-1:"
            "native-submission:shader-payload-identity-missing"
        )
        for reason in result["blocking_reasons"]
    )


def test_material_slice_set_missing_shader_only_blocks_affected_child(tmp_path):
    payload = _multi_slice()
    payload["render_command"]["submeshes"][1]["shader"].pop(
        "vulkan_pixel_glsl"
    )

    result = build_bmw_vulkan_set_from_material_slice(
        payload,
        tmp_path,
    )

    assert result["ready"] is False
    assert result["draws"][0]["ready"] is True
    assert result["draws"][1]["ready"] is False
    assert (
        "bmw-material-vulkan:vulkan-pixel-source-missing:1"
        in result["draws"][1]["blocking_reasons"]
    )
    assert (
        "bundle-set:submesh-1:manifest-missing"
        in result["blocking_reasons"]
    )
