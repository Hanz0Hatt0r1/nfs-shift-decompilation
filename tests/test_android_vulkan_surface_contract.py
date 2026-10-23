from pathlib import Path


def test_android_vulkan_surface_probe_is_native_window_backed():
    cmake = Path("native_vulkan/CMakeLists.txt").read_text(encoding="utf-8")
    header = Path(
        "native_vulkan/include/shift_android_surface_probe.h"
    ).read_text(encoding="utf-8")
    source = Path(
        "native_vulkan/src/android_vulkan_surface_probe.cpp"
    ).read_text(encoding="utf-8")
    common = Path(
        "native_vulkan/src/vulkan_surface_backend.cpp"
    ).read_text(encoding="utf-8")

    assert "if(ANDROID)" in cmake
    assert "shift_vulkan_android_surface_probe" in cmake
    assert "shift_vulkan_surface_backend" in cmake
    assert "VK_USE_PLATFORM_ANDROID_KHR" in cmake
    assert "Vulkan::Vulkan" in cmake

    assert "ANativeWindow* window" in header
    assert "shift_android_vulkan_surface_probe" in header

    assert "VK_KHR_ANDROID_SURFACE_EXTENSION_NAME" in source
    assert "VkAndroidSurfaceCreateInfoKHR" in source
    assert "vkCreateAndroidSurfaceKHR" in source
    assert "shift_vulkan_surface_probe_backend(&backend)" in source

    # Device selection, present-queue validation and Vulkan-handle cleanup are
    # platform-neutral and must stay in the shared backend rather than drift
    # independently between Android and XCB adapters.
    assert "vkGetPhysicalDeviceSurfaceSupportKHR" in common
    assert "VK_API_VERSION_1_1" in common
    assert "vkEnumerateInstanceVersion" in common
    assert "properties.apiVersion < VK_API_VERSION_1_1" in common
    assert "SHIFT_VULKAN_SURFACE_PROBE_API_VERSION_FAILURE" in common
    assert "VK_QUEUE_GRAPHICS_BIT" in common
    assert "vkDestroySurfaceKHR" in common
    assert "vkDestroyInstance" in common


def test_captured_draw_path_does_not_require_optional_mobile_features():
    source = Path(
        "native_vulkan/src/vulkan_bundle_execute.cpp"
    ).read_text(encoding="utf-8")
    profile = Path(
        "native_vulkan/ANDROID_VULKAN_SUPPORT.md"
    ).read_text(encoding="utf-8")

    assert "raster.polygonMode = VK_POLYGON_MODE_FILL" in source
    assert "device.pEnabledFeatures" not in source
    assert "vertexPipelineStoresAndAtomics` | unsupported" in profile
    assert "fillModeNonSolid` | unsupported" in profile
    assert "does not enable or require optional device features" in profile
