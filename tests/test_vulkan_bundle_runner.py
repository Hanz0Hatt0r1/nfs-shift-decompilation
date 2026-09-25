from pathlib import Path


def test_vulkan_bundle_runner_has_explicit_resource_boundary():
    source = Path("native_vulkan/src/vulkan_bundle_runner.cpp").read_text(encoding="utf-8")
    assert "geometry.svpk" in source
    assert "constants.svcp" in source
    assert "textures.svtp" in source
    assert "environment_cube.svcp" in source
    assert "Phase 218 native bundle execution currently requires shader reflection" in source
    assert "load_geometry" in source
    assert "load_constants" in source
