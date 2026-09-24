import struct

import pytest

from texture_reference import decode_dds, image_hash, sample_texture_2d


def _dds_header(
    width=4,
    height=4,
    *,
    fourcc=b"",
    rgb_bits=0,
    pf_flags=None,
    r_mask=0,
    g_mask=0,
    b_mask=0,
    a_mask=0,
    mipmaps=1,
):
    if pf_flags is None:
        pf_flags = 0x4 if fourcc else 0x40
    pf_fourcc = struct.unpack("<I", fourcc.ljust(4, b"\x00"))[0]
    values = (
        124,
        0,
        height,
        width,
        0,
        0,
        mipmaps,
        *([0] * 11),
        32,
        pf_flags,
        pf_fourcc,
        rgb_bits,
        r_mask,
        g_mask,
        b_mask,
        a_mask,
        0,
        0,
        0,
        0,
        0,
    )
    header = struct.pack("<31I", *values)
    assert len(header) == 124
    return b"DDS " + header


def test_decode_dxt1_to_rgba8():
    # c0=red, c1=green, selector 0 for all 16 texels.
    block = struct.pack("<HHI", 0xF800, 0x07E0, 0)
    image = decode_dds(_dds_header(fourcc=b"DXT1") + block)
    assert image["format"] == "SHIFT.ReferenceTexture/1"
    assert image["source_format"] == "DXT1"
    assert image["width"] == 4
    assert image["height"] == 4
    assert image["pixels"][:4] == bytes((255, 0, 0, 255))
    assert image_hash(image) == "fec0f57de0b19bc7dacb5b0fc3de7b56fc68dfdbeeebc8f9f4c506bf6e821c77"


def test_decode_dxt3_preserves_explicit_alpha():
    alpha = int("f" * 16, 16).to_bytes(8, "little")
    color = struct.pack("<HHI", 0x001F, 0x07E0, 0)
    image = decode_dds(_dds_header(fourcc=b"DXT3") + alpha + color)
    assert image["pixels"][:4] == bytes((0, 0, 255, 255))


def test_decode_dxt5_preserves_alpha_table():
    alpha = bytes((0, 255)) + bytes(6)
    color = struct.pack("<HHI", 0xF800, 0x07E0, 0)
    image = decode_dds(_dds_header(fourcc=b"DXT5") + alpha + color)
    assert image["pixels"][:4] == bytes((255, 0, 0, 0))


def test_decode_uncompressed_bgra32_from_masks():
    masks = (0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)
    pixel = struct.pack("<I", 0x80402010)
    image = decode_dds(
        _dds_header(
            width=1,
            height=1,
            rgb_bits=32,
            pf_flags=0x40,
            r_mask=masks[0],
            g_mask=masks[1],
            b_mask=masks[2],
            a_mask=masks[3],
        )
        + pixel
    )
    assert image["pixels"] == bytes((64, 32, 16, 128))


def test_texture_sampler_wrap_modes():
    image = {
        "width": 2,
        "height": 1,
        "pixels": bytes((255, 0, 0, 255, 0, 255, 0, 255)),
    }
    assert sample_texture_2d(
        image, 1.25, 0.0, {"min_filter": "POINT", "mag_filter": "POINT", "address_u": "REPEAT"}
    ) == pytest.approx((1.0, 0.0, 0.0, 1.0))
    assert sample_texture_2d(
        image, 1.25, 0.0, {"min_filter": "POINT", "mag_filter": "POINT", "address_u": "CLAMP_TO_EDGE"}
    ) == pytest.approx((0.0, 1.0, 0.0, 1.0))


def test_texture_sampler_linear_filter_interpolates_texels():
    image = {
        "width": 2,
        "height": 1,
        "pixels": bytes((255, 0, 0, 255, 0, 0, 255, 255)),
    }
    result = sample_texture_2d(
        image,
        0.5,
        0.0,
        {"min_filter": "LINEAR", "mag_filter": "LINEAR", "address_u": "CLAMP_TO_EDGE"},
    )
    assert result == pytest.approx((0.5, 0.0, 0.5, 1.0))


def test_decode_dds_rejects_truncated_block():
    with pytest.raises(ValueError, match="truncated"):
        decode_dds(_dds_header(fourcc=b"DXT1") + b"\x00" * 7)


def _cube_resource():
    faces = {}
    colors = {
        "px": (255, 0, 0, 255),
        "nx": (0, 255, 0, 255),
        "py": (0, 0, 255, 255),
        "ny": (255, 255, 0, 255),
        "pz": (255, 0, 255, 255),
        "nz": (0, 255, 255, 255),
    }
    for face, rgba in colors.items():
        faces[face] = {
            "format": "SHIFT.ReferenceTexture/1",
            "source_format": "RGBA32",
            "width": 1,
            "height": 1,
            "pixels": bytes(rgba),
        }
    return {
        "format": "SHIFT.ReferenceCubeTexture/1",
        "faces": faces,
    }


def test_sample_texture_cube_selects_d3d9_faces():
    from texture_reference import sample_texture_cube

    cube = _cube_resource()
    assert sample_texture_cube(cube, 1.0, 0.0, 0.0) == pytest.approx((1.0, 0.0, 0.0, 1.0))
    assert sample_texture_cube(cube, -1.0, 0.0, 0.0) == pytest.approx((0.0, 1.0, 0.0, 1.0))
    assert sample_texture_cube(cube, 0.0, 1.0, 0.0) == pytest.approx((0.0, 0.0, 1.0, 1.0))
    assert sample_texture_cube(cube, 0.0, -1.0, 0.0) == pytest.approx((1.0, 1.0, 0.0, 1.0))
    assert sample_texture_cube(cube, 0.0, 0.0, 1.0) == pytest.approx((1.0, 0.0, 1.0, 1.0))
    assert sample_texture_cube(cube, 0.0, 0.0, -1.0) == pytest.approx((0.0, 1.0, 1.0, 1.0))


def test_sample_texture_cube_rejects_incomplete_resource():
    from texture_reference import sample_texture_cube

    cube = _cube_resource()
    del cube["faces"]["nz"]
    with pytest.raises(ValueError, match="missing faces: nz"):
        sample_texture_cube(cube, 0.0, 0.0, 1.0)


def test_sample_texture_cube_rejects_zero_direction():
    from texture_reference import sample_texture_cube

    with pytest.raises(ValueError, match="finite non-zero major component"):
        sample_texture_cube(_cube_resource(), 0.0, 0.0, 0.0)
