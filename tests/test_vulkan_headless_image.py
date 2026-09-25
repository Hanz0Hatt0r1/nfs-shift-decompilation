from pathlib import Path


def test_headless_vulkan_target_and_contract():
    cmake = Path("native_vulkan/CMakeLists.txt").read_text(encoding="utf-8")
    source = Path("native_vulkan/src/vulkan_headless_clear.cpp").read_text(encoding="utf-8")
    readme = Path("native_vulkan/README.md").read_text(encoding="utf-8")

    assert "shift_vulkan_headless_clear" in cmake
    assert "VK_IMAGE_USAGE_TRANSFER_DST_BIT" in source
    assert "VK_IMAGE_USAGE_TRANSFER_SRC_BIT" in source
    assert "vkCmdClearColorImage" in source
    assert "vkCmdCopyImageToBuffer" in source
    assert "vkQueueSubmit" in source
    assert "SHIFT.VulkanHeadlessImage/1" in source
    assert "P6" in source
    assert "headless" in readme.lower()
