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
    assert state["format"] == "SHIFT.MaterialPipelineState/1"
    assert state["cull"]["engine_enum_index"] == 1
    assert state["cull"]["d3d9_value"] == 2
    assert state["vulkan"]["cull_mode"] == "VK_CULL_MODE_BACK_BIT"
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



def test_bmw_vulkan_bundle_emits_depth_and_blend_pipeline_state(tmp_path):
    command = _command()
    command["render_commands"][0]["submeshes"][0]["render_state"] = {
        "format": "SHIFT.BMTRenderState/1",
        "cull": "EBFCT_ANTICLOCKWISE",
        "depth": {
            "format": "SHIFT.BMTDepthState/1",
            "enabled": True,
            "write_enabled": False,
            "function": {
                "raw": "ETF_GREATER_THAN",
                "engine_enum_index": 4,
                "status": "known",
            },
        },
        "alpha_test": {
            "format": "SHIFT.BMTAlphaTestState/1",
            "enabled": False,
        },
        "alpha_blend": {
            "format": "SHIFT.BMTAlphaBlendState/1",
            "enabled": True,
            "source_blend": {
                "raw": "EBF_SOURCE_ALPHA",
                "engine_enum_index": 4,
                "status": "known",
            },
            "dest_blend": {
                "raw": "EBF_INV_SOURCE_ALPHA",
                "engine_enum_index": 5,
                "status": "known",
            },
            "blend_op": {
                "raw": "EBO_ADD",
                "engine_enum_index": 0,
                "status": "known",
            },
        },
    }
    result = build_bmw_vulkan_bundle(
        command, _mesh(), tmp_path, submesh_index=0
    )

    assert result["ready"] is True, result["blocking_reasons"]
    state = json.loads(
        (tmp_path / "pipeline_state.json").read_text(encoding="utf-8")
    )
    assert state["vulkan"] == {
        "alpha_blend_op": "VK_BLEND_OP_ADD",
        "blend_enable": True,
        "color_blend_op": "VK_BLEND_OP_ADD",
        "cull_mode": "VK_CULL_MODE_FRONT_BIT",
        "depth_compare_op": "VK_COMPARE_OP_GREATER",
        "depth_test_enable": True,
        "depth_write_enable": False,
        "dst_alpha_blend_factor": "VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA",
        "dst_color_blend_factor": "VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA",
        "front_face": "VK_FRONT_FACE_COUNTER_CLOCKWISE",
        "src_alpha_blend_factor": "VK_BLEND_FACTOR_SRC_ALPHA",
        "src_color_blend_factor": "VK_BLEND_FACTOR_SRC_ALPHA",
    }


def test_bmw_vulkan_bundle_blocks_enabled_alpha_test(tmp_path):
    command = _command()
    command["render_commands"][0]["submeshes"][0]["render_state"] = {
        "alpha_test": {
            "format": "SHIFT.BMTAlphaTestState/1",
            "enabled": True,
            "function": {
                "raw": "ETF_GREATER_THAN_OR_EQUAL",
                "engine_enum_index": 6,
                "status": "known",
            },
            "value_normalized": 0.5,
        },
    }
    result = build_bmw_vulkan_bundle(
        command, _mesh(), tmp_path, submesh_index=0
    )
    assert result["ready"] is False
    assert (
        "material-pipeline:alpha-test-enabled-unsupported"
        in result["blocking_reasons"]
    )


def test_vulkan_bundle_accepts_exact_neutral_scene_mesh_when_explicit(tmp_path):
    command = _command()
    scene_ref = "tracks/silverstone/runtime_proven.imb"
    command["render_commands"][0]["mesh"]["ref"] = scene_ref
    neutral = {
        **_mesh(),
        "format": "SHIFT.NeutralMesh/1",
    }

    result = build_bmw_vulkan_bundle(
        command,
        neutral,
        tmp_path,
        expected_mesh_ref=scene_ref,
    )

    assert result["ready"] is True, result["blocking_reasons"]
    assert result["target"]["meb"] is None
    assert result["target"]["resource"] == scene_ref
    assert result["target"]["expected_resource"] == scene_ref
    assert result["target"]["mesh_format"] == "SHIFT.NeutralMesh/1"


def test_vulkan_bundle_rejects_wrong_explicit_scene_mesh_reference(tmp_path):
    command = _command()
    command["render_commands"][0]["mesh"]["ref"] = "tracks/a.imb"
    neutral = {**_mesh(), "format": "SHIFT.NeutralMesh/1"}

    try:
        build_bmw_vulkan_bundle(
            command,
            neutral,
            tmp_path,
            expected_mesh_ref="tracks/b.imb",
        )
    except ValueError as error:
        assert "does not match expected resource" in str(error)
    else:
        raise AssertionError("wrong exact scene resource must be blocked")
