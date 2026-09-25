from pathlib import Path


def test_linux_vulkan_bootstrap_is_optional_and_headless():
    cmake = Path("native_vulkan/CMakeLists.txt").read_text(encoding="utf-8")
    readme = Path("native_vulkan/README.md").read_text(encoding="utf-8")
    probe = Path("native_vulkan/src/vulkan_probe.cpp").read_text(encoding="utf-8")

    assert "find_package(Vulkan QUIET)" in cmake
    assert "if(NOT Vulkan_FOUND)" in cmake
    assert "shift_vulkan_probe" in cmake

    assert "RenderCommand/1" in readme
    assert "SPIR-V" in readme
    assert "window-system dependency" in readme

    assert "SHIFT.VulkanProbe/1" in probe
    assert "vkCreateInstance" in probe
    assert "vkEnumeratePhysicalDevices" in probe
    assert "VK_QUEUE_GRAPHICS_BIT" in probe
    assert "VK_QUEUE_COMPUTE_BIT" in probe
