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
