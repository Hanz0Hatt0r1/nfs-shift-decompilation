import struct
from pathlib import Path

from vulkan_sampler_packet import HEADER, RECORD, build_vulkan_sampler_packet


def _command(**state):
    return {
        "format": "SHIFT.RenderCommand/1",
        "submeshes": [{
            "textures": [{
                "sampler": "diffuseMap",
                "d3d9_sampler_register": 1,
                "sampler_state": state or {
                    "min_filter": "LINEAR",
                    "mag_filter": "LINEAR",
                    "mip_filter": "NONE",
                    "address_u": "REPEAT",
                    "address_v": "REPEAT",
                    "address_w": "REPEAT",
                    "srgb": True,
                },
            }]
        }],
    }


def test_sampler_packet_roundtrip_for_native_supported_subset(tmp_path):
    output = tmp_path / "samplers.svss"
    result = build_vulkan_sampler_packet(_command(), output)
    assert result["ready"] is True
    assert result["records"][0]["register"] == 1
    assert result["records"][0]["srgb"] == 1
    assert result["records"][0]["min_filter"] == 2
    raw = output.read_bytes()
    assert HEADER.unpack_from(raw)[:4] == (b"SVSS", 1, 1, 1)
    assert len(raw) == HEADER.size + RECORD.size


def test_sampler_packet_blocks_mip_filter_for_single_mip_native_path(tmp_path):
    result = build_vulkan_sampler_packet(
        _command(
            min_filter="LINEAR",
            mag_filter="LINEAR",
            mip_filter="LINEAR",
            address_u="REPEAT",
            address_v="REPEAT",
            srgb=True,
        ),
        tmp_path / "bad.svss",
    )
    assert result["ready"] is False
    assert "mip-filter-requires-mip-chain" in result["blocking_reasons"][0]


def test_sampler_packet_rejects_anisotropy_for_current_native_path(tmp_path):
    result = build_vulkan_sampler_packet(
        _command(
            min_filter="LINEAR",
            mag_filter="LINEAR",
            mip_filter="NONE",
            address_u="REPEAT",
            address_v="REPEAT",
            max_anisotropy=4,
        ),
        tmp_path / "bad.svss",
    )
    assert result["ready"] is False
    assert "anisotropy-not-enabled" in result["blocking_reasons"][0]
