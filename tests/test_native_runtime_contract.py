from pathlib import Path


def test_native_runtime_contract():
    cmake = Path("native_runtime/CMakeLists.txt").read_text(encoding="utf-8")
    readme = Path("native_runtime/README.md").read_text(encoding="utf-8")
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(encoding="utf-8")

    assert "project(shift_native_runtime" in cmake
    assert "PkgConfig::XCB" in cmake
    assert "Vulkan::Vulkan" in cmake
    assert "shift_ir" in cmake
    assert "VK_KHR_XCB_SURFACE_EXTENSION_NAME" in source
    assert "SHIFT.NativeRuntimeBootstrap/1" in source
    assert "SHIFT.NativeRuntimeFrameLoop/1" in source
    assert "offline-only" in readme
    assert "EA services" in readme
    assert "DRM" in readme


def test_native_runtime_consumes_bmw_bundle_geometry():
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(encoding="utf-8")
    shader = Path("native_runtime/shaders/runtime.vert").read_text(encoding="utf-8")

    assert "SHIFT.BMWVulkanBundle/1" in source
    assert "SHIFT.NativeSubmissionGate/1" in source
    assert "first_index = geometry.first_index" in source
    assert "first_index, 0, 0" in source
    assert "layout(location = 0) in vec3 inPosition;" in shader
    assert "inNormal" not in shader

def test_native_runtime_has_fixed_clock_and_input_layer():
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(encoding="utf-8")
    assert "XCB_EVENT_MASK_KEY_RELEASE" in source
    assert "struct InputState" in source
    assert "constexpr double kFixedDt = 1.0 / 60.0;" in source
    assert "SHIFT.NativeRuntimeInput/1" in source
    assert "simulation_steps" in source

def test_native_runtime_bundle_executes_material_interface():
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(encoding="utf-8")

    assert "struct BundleAssets" in source
    assert "SHIFT.BMWVulkanInterfaceGate/1" in source
    assert "SHIFT.VulkanBundleSPIRV/1" in source
    assert "bundle->vertex_shader_path" in source
    assert "bundle->fragment_shader_path" in source
    assert "create_material_resources" in source
    assert "upload_material_resources" in source
    assert "VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER" in source
    assert "VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER" in source
    assert "vkCmdBindDescriptorSets" in source
    assert "material_mode ? VK_CULL_MODE_NONE" in source
    assert "geometry.vertex_bytes.empty()" in source
    assert "vkCmdBindDescriptorSets" in source
    assert "if (material_mode)" in source

def test_native_runtime_state_boundary_is_evidence_backed():
    header = Path("native_runtime/src/runtime_state.hpp").read_text(encoding="utf-8")
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(encoding="utf-8")

    assert 'SHIFT.NativeRuntimeState/1' in header
    assert "CameraBufferRuntime" in header
    assert "active_index = 0" in header
    assert "update_in_progress" in header
    assert "VehicleControlIntent" in header
    assert "PhysicsTickBoundary" in header
    assert "fixed_dt = 1.0 / 60.0" in header
    assert "participant_ready = false" in header
    assert "participant_index = -1" in header
    assert 'runtime_state.hpp' in source
    assert "native_state.fixed_step(intent)" in source
    assert "state_layer" in source
    assert "SHIFT.NativeRuntimeState/1" in source

def test_native_runtime_accepts_bmw_physics_manifest():
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(encoding="utf-8")
    workflow = Path(".github/workflows/linux-vulkan.yml").read_text(encoding="utf-8")

    assert "SHIFT.BMWM3VehiclePhysicsResourceManifest/1" in source
    assert "--physics-manifest" in source
    assert "load_physics_manifest" in source
    assert "scalar_count != 40u" in source
    assert "evidence/bmw_m3_vehicle_physics_manifest.json" in workflow
    assert "physics_workspace_scalars" in source

def test_native_camera_defaults_match_recovered_view_constructor():
    header = Path("native_runtime/src/runtime_state.hpp").read_text(encoding="utf-8")

    assert "0x3F490FDBu" in header
    assert "0x3FAAAAABu" in header
    assert "0x3DCCCCCDu" in header
    assert "0x443B8000u" in header
    assert "manager_mode = 0" in header
    assert "buffer_sub_index = -1" in header
    assert "camera_id = -1" in header
    assert "active_group = -1" in header
    assert "group_restore_value = -1" in header
    assert "buffer_count = 2" in header

def test_native_index_draw_count_respects_first_index():
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(encoding="utf-8")

    assert "geometry.indices.size() - first_index" in source
    assert "index_count == 0" in source


def test_native_runtime_uses_per_swapchain_depth_buffers():
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(encoding="utf-8")

    assert "std::vector<Image> depth_images" in source
    assert "create_depth_resources()" in source
    assert "VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT" in source
    assert "VK_IMAGE_ASPECT_DEPTH_BIT" in source
    assert "VK_FORMAT_D32_SFLOAT depth attachment unsupported" in source
    assert "pDepthStencilAttachment = &depth_ref" in source
    assert "depthTestEnable = VK_TRUE" in source
    assert "depthWriteEnable = VK_TRUE" in source
    assert "VK_COMPARE_OP_LESS_OR_EQUAL" in source
    assert "clear[1].depthStencil.depth = 1.0f" in source
    assert '\\"depth_test\\": true' in source


def test_native_runtime_consumes_prepared_multi_draw_bundle_sets():
    source = Path("native_runtime/src/shift_runtime.cpp").read_text(encoding="utf-8")

    assert "struct MaterialDraw" in source
    assert "std::vector<MaterialDraw> material_draws" in source
    assert "load_bundle_set_paths" in source
    assert '"--bundle-set"' in source
    assert "SHIFT.BMWVulkanBundleSetPrepare/1" in source
    assert "bundle set prepare gate is missing or not ready" in source
    assert "for (const MaterialDraw& draw : material_draws)" in source
    assert "draw.pipeline_layout" in source
    assert "draw.vertex_constants" in source
    assert "draw.texture_images" in source
    assert '\\"material_draws\\": ' in source
    assert '\\"bundle_set_mode\\": ' in source
