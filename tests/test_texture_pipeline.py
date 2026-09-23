from texture_pipeline import build_texture_contract, build_sampler_contract, classify_dds


def _dds(fourcc="DXT1", width=128, height=64, mipmaps=5):
    return {
        "format": "DDS",
        "width": width,
        "height": height,
        "mipmaps": mipmaps,
        "fourcc": fourcc,
        "rgb_bits": 0,
        "byte_size": 1024,
    }


def test_classify_dxt1_preserves_block_geometry():
    r = classify_dds(_dds("DXT1"))
    assert r["status"] == "known"
    assert r["gpu_format"] == "BC1_RGBA"
    assert r["blocks_x"] == 32
    assert r["blocks_y"] == 16
    assert r["block_bytes"] == 8


def test_classify_uncompressed_rgba_is_known():
    r = classify_dds(_dds("", 16, 8, 1) | {"rgb_bits": 32})
    assert r["status"] == "known"
    assert r["upload"] == "uncompressed"


def test_sampler_contract_maps_d3d9_state():
    r = build_sampler_contract({
        "min_filter": "LINEAR",
        "mag_filter": "LINEAR",
        "mip_filter": "POINT",
        "address_u": "WRAP",
        "address_v": "CLAMP",
        "address_w": "MIRROR",
        "max_anisotropy": 4,
        "lod_bias": 0,
    })
    assert r["ready"] is True
    assert r["min_filter_gl"] == "LINEAR_MIPMAP_NEAREST"
    assert r["address_u"] == "REPEAT"
    assert r["address_v"] == "CLAMP_TO_EDGE"
    assert r["address_w"] == "MIRRORED_REPEAT"


def test_texture_contract_marks_s3tc_as_runtime_extension_requirement():
    r = build_texture_contract(
        _dds("DXT5"),
        {"min_filter": "LINEAR", "mag_filter": "LINEAR", "mip_filter": "LINEAR"},
    )
    assert r["ready"] is False
    assert "gpu-extension-required:EXT_texture_compression_s3tc" in r["blocking_reasons"]


def test_texture_contract_rejects_conflicting_color_space_flags():
    r = build_texture_contract(
        _dds("DXT1"),
        {
            "min_filter": "POINT",
            "mag_filter": "POINT",
            "mip_filter": "NONE",
            "srgb": True,
            "linear": True,
        },
    )
    assert r["color_space"] == "conflict"
    assert "color-space:srgb-and-linear-both-set" in r["blocking_reasons"]


def test_sampler_contract_rejects_border_address_mode():
    r = build_sampler_contract({"address_u": "BORDER"})
    assert r["ready"] is False
    assert "sampler-address-u:unsupported:BORDER" in r["blocking_reasons"]
