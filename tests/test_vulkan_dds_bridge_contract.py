from pathlib import Path

def test_dds_bridge_has_cli_contract():
    source = Path("vulkan_dds_bridge.py").read_text(encoding="utf-8")
    assert "def bridge_bmw_dds_resources(" in source
    assert "def main(" in source
    assert "decode_dds" in source
    assert "build_vulkan_texture_packet" in source
    assert "build_vulkan_cube_packet" in source
    assert "dds_sources.json" in source
    assert "dds_bridge_manifest.json" in source
