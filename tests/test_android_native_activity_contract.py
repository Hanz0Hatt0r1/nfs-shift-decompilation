from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_native_activity_routes_window_lifecycle_into_shared_vulkan_probe():
    header = _text("native_vulkan/include/shift_android_native_activity.h")
    source = _text("native_vulkan/src/android_native_activity.cpp")

    assert "ANativeActivity_onCreate" in header
    assert "shift_android_activity_last_surface_probe_status" in header

    assert "activity->callbacks->onNativeWindowCreated" in source
    assert "activity->callbacks->onNativeWindowDestroyed" in source
    assert "activity->callbacks->onDestroy" in source
    assert "shift_android_vulkan_surface_probe(window)" in source
    assert "SHIFT_VULKAN_SURFACE_PROBE_INVALID_BACKEND" in source
    assert "activity->instance = nullptr" in source


def test_android_native_activity_has_real_ndk_cross_build_gate():
    cmake = _text("native_vulkan/android/CMakeLists.txt")
    workflow = _text(".github/workflows/android-vulkan.yml")

    assert "if(NOT ANDROID)" in cmake
    assert "shift_vulkan_android_native_activity" in cmake
    assert "../src/vulkan_surface_backend.cpp" in cmake
    assert "../src/android_vulkan_surface_probe.cpp" in cmake
    assert "../src/android_native_activity.cpp" in cmake
    assert "find_library(SHIFT_ANDROID_LIB android REQUIRED)" in cmake
    assert "find_library(SHIFT_VULKAN_LIB vulkan REQUIRED)" in cmake

    assert "ANDROID_ABI=arm64-v8a" in workflow
    assert "ANDROID_PLATFORM=android-26" in workflow
    assert "android.toolchain.cmake" in workflow
    assert "ANativeActivity_onCreate" in workflow
    assert "shift_android_activity_last_surface_probe_status" in workflow
    assert "unexpectedly depends on XCB" in workflow
