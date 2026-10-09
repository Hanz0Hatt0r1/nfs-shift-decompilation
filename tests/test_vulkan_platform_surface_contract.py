from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_android_and_xcb_share_one_vulkan_surface_probe_contract():
    cmake = _text("native_vulkan/CMakeLists.txt")
    header = _text("native_vulkan/include/shift_vulkan_surface_backend.h")
    common = _text("native_vulkan/src/vulkan_surface_backend.cpp")
    android = _text("native_vulkan/src/android_vulkan_surface_probe.cpp")
    xcb = _text("native_vulkan/src/xcb_vulkan_surface_probe.cpp")

    assert "ShiftVulkanSurfaceBackend" in header
    assert "ShiftVulkanCreateSurfaceFn" in header
    assert "caller owns `context`" in header
    assert "common probe owns and destroys that surface" in header

    assert "vkCreateInstance" in common
    assert "vkGetPhysicalDeviceSurfaceSupportKHR" in common
    assert "vkDestroySurfaceKHR" in common
    assert "vkDestroyInstance" in common
    assert "SHIFT_VULKAN_SURFACE_PROBE_INVALID_BACKEND" in common

    assert "VK_KHR_ANDROID_SURFACE_EXTENSION_NAME" in android
    assert "shift_vulkan_surface_probe_backend(&backend)" in android
    assert "VK_KHR_XCB_SURFACE_EXTENSION_NAME" in xcb
    assert "shift_vulkan_surface_probe_backend(&backend)" in xcb

    assert "shift_vulkan_surface_backend" in cmake
    assert "shift_vulkan_android_surface_probe" in cmake
    assert "shift_vulkan_xcb_surface_probe" in cmake
    assert "PkgConfig::XCB" in cmake


def test_platform_adapters_fail_closed_before_common_probe_on_missing_native_handle():
    android = _text("native_vulkan/src/android_vulkan_surface_probe.cpp")
    xcb = _text("native_vulkan/src/xcb_vulkan_surface_probe.cpp")

    assert "if (window == nullptr)" in android
    assert "SHIFT_VULKAN_SURFACE_PROBE_INVALID_BACKEND" in android
    assert "connection == nullptr || window == XCB_WINDOW_NONE" in xcb
    assert "SHIFT_VULKAN_SURFACE_PROBE_INVALID_BACKEND" in xcb
