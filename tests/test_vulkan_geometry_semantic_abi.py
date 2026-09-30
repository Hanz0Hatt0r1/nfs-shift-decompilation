from pathlib import Path


def test_vulkan_geometry_checkpoint_accepts_svgp_v3_semantics_and_legacy_packets():
    source = Path("native_vulkan/src/vulkan_render_geometry.cpp").read_text(
        encoding="utf-8"
    )
    assert "struct LegacyPacketAttribute" in source
    assert "uint32_t property_id;" in source
    assert "packet.header.version != 3" in source
    assert "legacy.location == 0u ? 200u : 0u" in source
    assert "attribute.property_id != 200u" in source
    assert "sizeof(PacketAttribute) == 20" in source
