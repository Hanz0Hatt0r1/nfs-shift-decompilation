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
