from pathlib import Path


def test_native_vulkan_bundle_executor_contract():
    source = Path("native_vulkan/src/vulkan_bundle_execute.cpp").read_text(encoding="utf-8")
    cmake = Path("native_vulkan/CMakeLists.txt").read_text(encoding="utf-8")
    assert "shift_vulkan_bundle_execute" in cmake
    assert "geometry.svpk" in source
    assert "constants.svcp" in source
    assert "textures.svtp" in source
    assert "environment_cube.svcp" in source
    assert "vkCmdDrawIndexed" in source
    assert "VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER" in source
    assert "VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER" in source
    assert "VK_IMAGE_VIEW_TYPE_CUBE" in source
    assert "VK_FORMAT_D32_SFLOAT" in source
    assert "SHIFT.VulkanBundleExecution/1" in source
    assert "load_pipeline_cull_mode" in source
    assert "SHIFT.MaterialCullState/1" in source
    assert "SHIFT.MaterialPipelineState/1" in source
    assert "load_pipeline_state" in source
    assert "raster.cullMode = pipeline_state.cull_mode;" in source
    assert "depth_state.depthTestEnable = pipeline_state.depth_test_enable;" in source
    assert "depth_state.depthWriteEnable = pipeline_state.depth_write_enable;" in source
    assert "depth_state.depthCompareOp = pipeline_state.depth_compare_op;" in source
    assert "blend_attachment.blendEnable = pipeline_state.blend_enable;" in source
    assert "world_transform.svwt" in source
    assert "WorldTransformHeader" in source
    assert "apply_world_transform_affine" in source
    assert "affine-semantic-v3" in source
    assert "SVWT affine linear transform is singular" in source
    assert "case 220u:" in source
    assert "case 240u:" in source
    assert "case 250u:" in source
    assert "transpose(inverse(A))" in source
    assert "world_transform_executed" in source
    assert "world_transform_mode" in source
    assert "world_transformed_properties" in source
    assert "world_probe_normal_xyz" in source
    assert "world_probe_tangent_xyz" in source
    assert "struct LegacyGeometryAttribute" in source
    assert "uint32_t property_id;" in source
    assert "geometry.header.version != 3" in source
    assert "legacy.location == 0u ? 200u : 0u" in source
    assert "attribute.property_id != 200u" in source


def test_vulkan_bundle_runner_contract():
    source = Path("src/render/vulkan/vulkan_bundle_run.py").read_text(encoding="utf-8")
    assert "compile_bmw_vulkan_bundle" in source
    assert "validate_bmw_vulkan_interface" in source
    assert "shift_vulkan_bundle_execute" in source
    assert "vulkan_interface.json" in source


def test_native_bundle_cube_staging_offset_excludes_packet_header():
    source = Path("native_vulkan/src/vulkan_bundle_execute.cpp").read_text(encoding="utf-8")
    assert "copy.bufferOffset =\n                    static_cast<VkDeviceSize>(face) * cube.header.face_bytes;" in source
    assert "sizeof(CubeHeader)) +" not in source
