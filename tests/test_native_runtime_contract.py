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
