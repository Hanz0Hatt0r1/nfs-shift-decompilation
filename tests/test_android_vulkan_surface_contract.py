from pathlib import Path


def test_android_vulkan_surface_probe_is_native_window_backed():
    cmake = Path("native_vulkan/CMakeLists.txt").read_text(encoding="utf-8")
    header = Path(
        "native_vulkan/include/shift_android_surface_probe.h"
    ).read_text(encoding="utf-8")
    source = Path(
        "native_vulkan/src/android_vulkan_surface_probe.cpp"
    ).read_text(encoding="utf-8")

    assert "if(ANDROID)" in cmake
    assert "shift_vulkan_android_surface_probe" in cmake
    assert "VK_USE_PLATFORM_ANDROID_KHR" in cmake
    assert "Vulkan::Vulkan" in cmake

    assert "ANativeWindow* window" in header
    assert "shift_android_vulkan_surface_probe" in header

    assert "VK_KHR_ANDROID_SURFACE_EXTENSION_NAME" in source
    assert "VkAndroidSurfaceCreateInfoKHR" in source
    assert "vkCreateAndroidSurfaceKHR" in source
    assert "vkGetPhysicalDeviceSurfaceSupportKHR" in source
    assert "VK_QUEUE_GRAPHICS_BIT" in source
    assert "vkDestroySurfaceKHR" in source
    assert "vkDestroyInstance" in source
