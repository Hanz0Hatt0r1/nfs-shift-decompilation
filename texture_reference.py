"""Deterministic software DDS decode and 2D sampling for the SHIFT reference renderer.

This layer is intentionally independent from the shader translator. It decodes
only the DDS pixel payload and applies the sampler contract; HLSL material math
remains a separate runtime stage.
"""
from __future__ import annotations

import math
import struct
from typing import Any


FORMAT = "SHIFT.ReferenceTexture/1"
_HEADER_SIZE = 128


def _u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def _u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def _rgb565(value: int) -> tuple[int, int, int]:
    r = ((value >> 11) & 0x1F) * 255 // 31
    g = ((value >> 5) & 0x3F) * 255 // 63
    b = (value & 0x1F) * 255 // 31
    return r, g, b


def _decode_dxt1_block(block: bytes) -> list[tuple[int, int, int, int]]:
    if len(block) != 8:
        raise ValueError("DXT1 block must contain 8 bytes")
    c0 = _u16(block, 0)
    c1 = _u16(block, 2)
    p0 = _rgb565(c0)
    p1 = _rgb565(c1)
    if c0 > c1:
        colors = [
            (*p0, 255),
            (*p1, 255),
            tuple((2 * p0[i] + p1[i]) // 3 for i in range(3)) + (255,),
            tuple((p0[i] + 2 * p1[i]) // 3 for i in range(3)) + (255,),
        ]
    else:
        colors = [
            (*p0, 255),
            (*p1, 255),
            tuple((p0[i] + p1[i]) // 2 for i in range(3)) + (255,),
            (0, 0, 0, 0),
        ]
    selectors = _u32(block, 4)
    return [colors[(selectors >> (2 * i)) & 3] for i in range(16)]


def _decode_dxt3_block(block: bytes) -> list[tuple[int, int, int, int]]:
    if len(block) != 16:
        raise ValueError("DXT3 block must contain 16 bytes")
    colors = _decode_dxt1_block(block[8:])
    alpha_bits = int.from_bytes(block[:8], "little")
    out = []
    for i, color in enumerate(colors):
        alpha = ((alpha_bits >> (4 * i)) & 0xF) * 17
        out.append((*color[:3], alpha))
    return out


def _decode_dxt5_alpha_table(a0: int, a1: int) -> list[int]:
    if a0 > a1:
        return [
            a0,
            a1,
            (6 * a0 + a1) // 7,
            (5 * a0 + 2 * a1) // 7,
            (4 * a0 + 3 * a1) // 7,
            (3 * a0 + 4 * a1) // 7,
            (2 * a0 + 5 * a1) // 7,
            (a0 + 6 * a1) // 7,
        ]
    return [
        a0,
        a1,
        (4 * a0 + a1) // 5,
        (3 * a0 + 2 * a1) // 5,
        (2 * a0 + 3 * a1) // 5,
        (a0 + 4 * a1) // 5,
        0,
        255,
    ]


def _decode_dxt5_block(block: bytes) -> list[tuple[int, int, int, int]]:
    if len(block) != 16:
        raise ValueError("DXT5 block must contain 16 bytes")
    alpha_table = _decode_dxt5_alpha_table(block[0], block[1])
    alpha_bits = int.from_bytes(block[2:8], "little")
    colors = _decode_dxt1_block(block[8:])
    return [
        (*color[:3], alpha_table[(alpha_bits >> (3 * i)) & 7])
        for i, color in enumerate(colors)
    ]


def _mask_shift(mask: int) -> tuple[int, int]:
    if mask == 0:
        return 0, 0
    shift = (mask & -mask).bit_length() - 1
    bits = (mask >> shift).bit_length()
    return shift, bits


def _extract_masked(value: int, mask: int, *, default: int) -> int:
    if mask == 0:
        return default
    shift, bits = _mask_shift(mask)
    raw = (value & mask) >> shift
    max_value = (1 << bits) - 1
    return raw * 255 // max_value if max_value else default


def _decode_uncompressed_rgba(data: bytes, width: int, height: int, rgb_bits: int, masks: tuple[int, int, int, int]) -> bytes:
    if rgb_bits != 32:
        raise ValueError(f"unsupported uncompressed DDS rgb_bits={rgb_bits}; only 32-bit is supported")
    row_bytes = width * 4
    payload_size = row_bytes * height
    if len(data) < payload_size:
        raise ValueError("DDS pixel payload is truncated")
    r_mask, g_mask, b_mask, a_mask = masks
    out = bytearray(payload_size)
    for i in range(width * height):
        value = _u32(data, i * 4)
        out[i * 4 + 0] = _extract_masked(value, r_mask, default=0)
        out[i * 4 + 1] = _extract_masked(value, g_mask, default=0)
        out[i * 4 + 2] = _extract_masked(value, b_mask, default=0)
        out[i * 4 + 3] = _extract_masked(value, a_mask, default=255)
    return bytes(out)


def _decode_block_compressed(data: bytes, width: int, height: int, fourcc: str) -> bytes:
    decoder = {
        "DXT1": (_decode_dxt1_block, 8),
        "DXT3": (_decode_dxt3_block, 16),
        "DXT5": (_decode_dxt5_block, 16),
    }.get(fourcc)
    if decoder is None:
        raise ValueError(f"unsupported block-compressed DDS format {fourcc!r}")

    decode_block, block_bytes = decoder
    blocks_x = max(1, (width + 3) // 4)
    blocks_y = max(1, (height + 3) // 4)
    expected = blocks_x * blocks_y * block_bytes
    if len(data) < expected:
        raise ValueError("DDS block-compressed pixel payload is truncated")

    out = bytearray(width * height * 4)
    for by in range(blocks_y):
        for bx in range(blocks_x):
            offset = (by * blocks_x + bx) * block_bytes
            pixels = decode_block(data[offset:offset + block_bytes])
            for py in range(4):
                y = by * 4 + py
                if y >= height:
                    continue
                for px in range(4):
                    x = bx * 4 + px
                    if x >= width:
                        continue
                    src = pixels[py * 4 + px]
                    dst = (y * width + x) * 4
                    out[dst:dst + 4] = bytes(src)
    return bytes(out)


def decode_dds(data: bytes, *, base_level_only: bool = True) -> dict[str, Any]:
    """Decode the DDS base level into RGBA8 pixels."""
    if len(data) < _HEADER_SIZE or data[:4] != b"DDS ":
        raise ValueError("not a DDS resource")

    height = _u32(data, 12)
    width = _u32(data, 16)
    mipmaps = _u32(data, 28) or 1
    pf_flags = _u32(data, 80)
    pf_fourcc_value = _u32(data, 84)
    rgb_bits = _u32(data, 88)
    masks = (
        _u32(data, 92),
        _u32(data, 96),
        _u32(data, 100),
        _u32(data, 104),
    )
    fourcc = struct.pack("<I", pf_fourcc_value).decode("ascii", "replace").rstrip("\x00")

    if width <= 0 or height <= 0:
        raise ValueError("DDS dimensions must be positive")

    payload = data[_HEADER_SIZE:]
    if fourcc in {"DXT1", "DXT3", "DXT5"}:
        pixels = _decode_block_compressed(payload, width, height, fourcc)
        storage = "block-compressed"
    elif not fourcc and (pf_flags & 0x40):
        pixels = _decode_uncompressed_rgba(payload, width, height, rgb_bits, masks)
        storage = "uncompressed"
    else:
        raise ValueError(f"unsupported DDS pixel format fourcc={fourcc!r} flags=0x{pf_flags:X}")

    return {
        "format": FORMAT,
        "source_format": fourcc or "RGBA32",
        "width": width,
        "height": height,
        "mipmaps": mipmaps,
        "base_level_only": base_level_only,
        "storage": storage,
        "pixel_format": "RGBA8",
        "pixels": pixels,
        "byte_size": len(pixels),
    }


def _wrap_coordinate(value: float, mode: str | None) -> float:
    state = str(mode or "REPEAT").upper()
    if state == "CLAMP_TO_EDGE":
        return max(0.0, min(1.0, value))
    if state == "MIRRORED_REPEAT":
        whole = math.floor(value)
        frac = value - whole
        return frac if whole % 2 == 0 else 1.0 - frac
    return value - math.floor(value)


def _pixel(image: dict[str, Any], x: int, y: int) -> tuple[float, float, float, float]:
    width = int(image["width"])
    height = int(image["height"])
    x = max(0, min(width - 1, x))
    y = max(0, min(height - 1, y))
    p = (y * width + x) * 4
    raw = image["pixels"][p:p + 4]
    return tuple(v / 255.0 for v in raw)  # type: ignore[return-value]


def sample_texture_2d(
    image: dict[str, Any],
    u: float,
    v: float,
    sampler: dict[str, Any] | None = None,
) -> tuple[float, float, float, float]:
    """Sample a decoded RGBA8 base level with explicit sampler addressing/filtering."""
    sampler = sampler or {}
    uu = _wrap_coordinate(float(u), sampler.get("address_u") or "REPEAT")
    vv = _wrap_coordinate(float(v), sampler.get("address_v") or "REPEAT")
    width = int(image["width"])
    height = int(image["height"])

    min_filter = str(sampler.get("min_filter") or "NEAREST").upper()
    mag_filter = str(sampler.get("mag_filter") or "NEAREST").upper()
    linear = min_filter == "LINEAR" or mag_filter == "LINEAR" or str(sampler.get("min_filter_gl") or "").startswith("LINEAR")

    x = uu * max(0, width - 1)
    y = vv * max(0, height - 1)
    if not linear:
        return _pixel(image, int(round(x)), int(round(y)))

    x0 = math.floor(x)
    y0 = math.floor(y)
    x1 = min(width - 1, x0 + 1)
    y1 = min(height - 1, y0 + 1)
    fx = x - x0
    fy = y - y0
    c00 = _pixel(image, x0, y0)
    c10 = _pixel(image, x1, y0)
    c01 = _pixel(image, x0, y1)
    c11 = _pixel(image, x1, y1)
    return tuple(
        (1 - fy) * ((1 - fx) * c00[k] + fx * c10[k])
        + fy * ((1 - fx) * c01[k] + fx * c11[k])
        for k in range(4)
    )


def image_hash(image: dict[str, Any]) -> str:
    import hashlib
    return hashlib.sha256(bytes(image["pixels"])).hexdigest()
