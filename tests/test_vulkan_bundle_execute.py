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


def test_vulkan_bundle_runner_contract():
    source = Path("vulkan_bundle_run.py").read_text(encoding="utf-8")
    assert "compile_bmw_vulkan_bundle" in source
    assert "validate_bmw_vulkan_interface" in source
    assert "shift_vulkan_bundle_execute" in source
    assert "vulkan_interface.json" in source
