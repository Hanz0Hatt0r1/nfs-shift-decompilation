import json
from pathlib import Path

from bmw_vulkan_bundle import TARGET_MEB, build_bmw_vulkan_bundle


def _command():
    return {
        "format": "SHIFT.RenderBinding/1",
        "render_commands": [{
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
                "vertex": "#version 450\nvoid main(){}",
                "pixel": "#version 450\nvoid main(){}",
                "source_payload_sha256": "a" * 64,
                "permutation_identity": {
                    "format": "SHIFT.ShaderPermutationIdentity/1",
                    "identity_sha256": "b" * 64,
                },
            },
            "constant_commands": [],
            "constant_payload": {"format": "SHIFT.MaterialConstantPayload/1", "registers": [], "ready": True},
            "textures": [],
            "external_samplers": [],
                "first_index": 0,
                "index_count": 3,
            }, {
                "shader": {
                    "vertex": "unused",
                    "pixel": "unused",
                    "source_payload_sha256": "c" * 64,
                    "permutation_identity": {
                        "format": "SHIFT.ShaderPermutationIdentity/1",
                        "identity_sha256": "d" * 64,
                    },
                },
                "constant_commands": [],
                "constant_payload": {"format": "SHIFT.MaterialConstantPayload/1", "registers": [], "ready": True},
                "textures": [],
                "external_samplers": [],
                "first_index": 0,
                "index_count": 3,
            }],
        }],
    }


def _mesh():
    return {
        "format": "SHIFT.MEB",
        "vertices": [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
        "indices": [0, 1, 2],
    }


def test_bmw_vulkan_bundle_prepares_geometry_constants_and_shaders(tmp_path):
    result = build_bmw_vulkan_bundle(_command(), _mesh(), tmp_path, command_index=0, submesh_index=1)

    assert result["format"] == "SHIFT.BMWVulkanBundle/1"
    assert result["ready"] is True
    assert result["target"]["meb"] == TARGET_MEB
    assert result["artifacts"]["geometry"]["ready"] is True
    assert result["artifacts"]["constants"]["ready"] is True
    assert len(result["artifacts"]["shaders"]) == 2
    assert (tmp_path / "geometry.svpk").exists()
    assert (tmp_path / "constants.svcp").exists()
    assert (tmp_path / "bundle_manifest.json").exists()
    gate = json.loads(
        (tmp_path / "native_submission_gate.json").read_text(encoding="utf-8")
    )
    assert gate["format"] == "SHIFT.NativeSubmissionGate/1"
    assert gate["ready"] is True

    manifest = json.loads((tmp_path / "bundle_manifest.json").read_text(encoding="utf-8"))
    assert manifest["format"] == "SHIFT.BMWVulkanBundle/1"


def test_bmw_vulkan_bundle_requires_exact_bmw_m3_mesh_reference(tmp_path):
    command = _command()
    command["render_commands"][0]["mesh"]["ref"] = "vehicles/other/body.meb"
    try:
        build_bmw_vulkan_bundle(command, _mesh(), tmp_path)
    except ValueError as error:
        assert "exact M3 KIT00 body MEB" in str(error)
    else:
        raise AssertionError("foreign MEB must be blocked")


def test_bmw_vulkan_bundle_blocks_missing_material_textures(tmp_path):
    command = _command()
    command["render_commands"][0]["submeshes"][0]["textures"] = [{
        "d3d9_sampler_register": 1,
        "resource_binding_id": 1,
        "texture_id": 2,
        "sampler_id": 3,
    }]
    result = build_bmw_vulkan_bundle(command, _mesh(), tmp_path)
    assert result["ready"] is False
    assert "bmw-vulkan-bundle:material-textures-not-supplied" in result["blocking_reasons"]



def test_bmw_vulkan_bundle_blocks_missing_native_shader_provenance(tmp_path):
    command = _command()
    command["render_commands"][0]["submeshes"][1]["shader"].pop("source_payload_sha256")
    result = build_bmw_vulkan_bundle(
        command,
        _mesh(),
        tmp_path,
        command_index=0,
        submesh_index=1,
    )
    assert result["ready"] is False
    assert "native-submission:shader-payload-identity-missing:0" in result["blocking_reasons"]
    assert result["native_execution"]["status"] == "blocked-by-provenance-gate"


def test_bmw_vulkan_bundle_blocked_result_has_stable_artifacts_schema(tmp_path):
    command = _command()
    command["render_commands"][0]["submeshes"][0]["shader"].pop("source_payload_sha256")
    result = build_bmw_vulkan_bundle(
        command,
        _mesh(),
        tmp_path,
        command_index=0,
        submesh_index=0,
    )
    assert result["ready"] is False
    assert isinstance(result["artifacts"], dict)
    assert result["external_samplers"] == []
    assert result["native_execution"]["status"] == "blocked-by-provenance-gate"



def test_bmw_vulkan_bundle_emits_evidence_backed_cull_state(tmp_path):
    command = _command()
    command["render_commands"][0]["submeshes"][0]["render_state"] = {
        "cull": "EBFCT_CLOCKWISE"
    }
    result = build_bmw_vulkan_bundle(
        command, _mesh(), tmp_path, submesh_index=0
    )
    assert result["ready"] is True, result["blocking_reasons"]
    state = json.loads(
        (tmp_path / "pipeline_state.json").read_text(encoding="utf-8")
    )
    assert state["format"] == "SHIFT.MaterialCullState/1"
    assert state["engine_enum_index"] == 1
    assert state["d3d9_value"] == 2
    assert state["vulkan_cull_mode"] == "VK_CULL_MODE_BACK_BIT"
    assert result["artifacts"]["pipeline_state"]["ready"] is True


def test_bmw_vulkan_bundle_blocks_unknown_bmt_cull(tmp_path):
    command = _command()
    command["render_commands"][0]["submeshes"][0]["render_state"] = {
        "cull": "EBFCT_MAGIC"
    }
    result = build_bmw_vulkan_bundle(
        command, _mesh(), tmp_path, submesh_index=0
    )
    assert result["ready"] is False
    assert (
        "material-cull:unsupported:EBFCT_MAGIC"
        in result["blocking_reasons"]
    )
    assert result["artifacts"]["pipeline_state"]["ready"] is False
