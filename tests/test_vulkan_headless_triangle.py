from pathlib import Path


def test_vulkan_triangle_target_contract():
    cmake = Path("native_vulkan/CMakeLists.txt").read_text(encoding="utf-8")
    vert = Path("native_vulkan/shaders/triangle.vert").read_text(encoding="utf-8")
    frag = Path("native_vulkan/shaders/triangle.frag").read_text(encoding="utf-8")
    source = Path("native_vulkan/src/vulkan_headless_triangle.cpp").read_text(encoding="utf-8")

    assert "find_program(GLSLANG_VALIDATOR" in cmake
    assert "shift_vulkan_headless_triangle" in cmake
    assert "glslangValidator" in cmake
    assert "gl_VertexIndex" in vert
    assert "v_color" in frag
    assert "vkCreateGraphicsPipelines" in source
    assert "vkCmdDraw(command, 3, 1, 0, 0)" in source
    assert "VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT" in source
    assert "VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL" in source
    assert "SHIFT.VulkanHeadlessTriangle/1" in source
