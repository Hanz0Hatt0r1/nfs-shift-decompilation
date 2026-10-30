from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RENDERER_SOURCES = (
    "native_vulkan/src/vulkan_headless_clear.cpp",
    "native_vulkan/src/vulkan_headless_triangle.cpp",
    "native_vulkan/src/vulkan_render_geometry.cpp",
    "native_vulkan/src/vulkan_constant_upload.cpp",
    "native_vulkan/src/vulkan_texture_upload.cpp",
    "native_vulkan/src/vulkan_sampler_cube.cpp",
    "native_vulkan/src/vulkan_bundle_runner.cpp",
    "native_vulkan/src/vulkan_bundle_execute.cpp",
    "native_vulkan/src/vulkan_surface_backend.cpp",
)


def test_native_vulkan_renderer_and_surface_paths_request_vulkan_1_1():
    for source_path in RENDERER_SOURCES:
        source = (ROOT / source_path).read_text(encoding="utf-8")
        assert "VK_API_VERSION_1_1" in source, source_path


def test_vulkan_probe_negotiates_loader_version_instead_of_renderer_floor():
    source = (ROOT / "native_vulkan/src/vulkan_probe.cpp").read_text(
        encoding="utf-8"
    )
    assert "vkEnumerateInstanceVersion" in source
