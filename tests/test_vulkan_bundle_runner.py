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


def test_vulkan_bundle_runner_accepts_semantic_svgp_v3_and_legacy_packets():
    source = Path("native_vulkan/src/vulkan_bundle_runner.cpp").read_text(
        encoding="utf-8"
    )
    assert "struct LegacyGeometryAttribute" in source
    assert "uint32_t property_id;" in source
    assert "out.header.version != 3" in source
    assert "legacy.location == 0u ? 200u : 0u" in source
    assert "attribute.property_id != 200u" in source
