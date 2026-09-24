import struct

from bff_meb_texture_render import render_bff_textured


def _mini_meb() -> bytes:
    data = bytearray()
    data += struct.pack(">I", 1)
    data += struct.pack(">I", 0)
    data += b"SMOKE_TEXTURE\0"
    while len(data) % 4:
        data += b"\0"
    data += struct.pack("<III", 3, 2, 1)
    data += bytes(40)
    data += struct.pack("<III", 2, 0, 0)
    data += struct.pack(
        "<fffffffff",
        -0.7, -0.6, 0.0,
        0.7, -0.6, 0.0,
        0.0, 0.7, 0.0,
    )
    data += struct.pack("<III", 1, 3, 0)
    data += struct.pack("<ffffff", 0.0, 0.0, 1.0, 0.0, 0.5, 1.0)
    data += b"SMOKE_PAINT\0"
    while len(data) % 4:
        data += b"\0"
    data += bytes(4)
    data += struct.pack("<I", 1)
    data += struct.pack("<HHH", 0, 1, 2)
    while len(data) % 4:
        data += b"\0"
    data += bytes(44)
    return bytes(data)


def _mini_dds() -> bytes:
    header = [
        124, 0, 1, 4, 4, 0, 1,
        *([0] * 11),
        32, 0x4, 0, 0,
        int.from_bytes(b"DXT1", "little"), 0, 0, 0, 0,
        0x1000, 0, 0, 0, 0,
    ]
    block = struct.pack("<HHI", 0xF800, 0x001F, 0)
    return b"DDS " + struct.pack("<31I", *header) + block


def _mini_bff(path, meb: bytes, dds: bytes) -> None:
    names = [b"vehicles/bmw_m3_e36/smoke.meb", b"vehicles/textures/smoke.dds"]
    records = 2
    name_base = 0x438 + records * 42
    string_base = name_base + records * 16
    string_blob = b""
    string_offsets = []
    for name in names:
        string_offsets.append(string_base + len(string_blob))
        string_blob += bytes([len(name)]) + name
    data_offset = (string_base + len(string_blob) + 0xFF) & ~0xFF
    payloads = [meb, dds]
    offsets = []
    cursor = data_offset
    for payload in payloads:
        offsets.append(cursor)
        cursor += len(payload)
    blob = bytearray(cursor)
    blob[0:4] = b" KAP"
    struct.pack_into("<I", blob, 4, 3)
    struct.pack_into("<I", blob, 8, records)
    struct.pack_into("<I", blob, 0x118, records * 42)
    struct.pack_into("<I", blob, 0x120, 0x308 + records * 16 + len(string_blob))
    for index, (payload, offset, name_offset) in enumerate(zip(payloads, offsets, string_offsets)):
        ro = 0x130 + index * 42
        struct.pack_into("<Q", blob, ro + 8, offset)
        struct.pack_into("<I", blob, ro + 16, len(payload))
        struct.pack_into("<I", blob, ro + 20, len(payload))
        blob[ro + 32] = 0
        struct.pack_into("<Q", blob, name_base + index * 16, name_offset)
    blob[string_base:string_base + len(string_blob)] = string_blob
    for payload, offset in zip(payloads, offsets):
        blob[offset:offset + len(payload)] = payload
    path.write_bytes(blob)


def test_real_bff_meb_texture_adapter_renders_dxt1_uv0(tmp_path):
    archive = tmp_path / "smoke.bff"
    out = tmp_path / "smoke.ppm"
    _mini_bff(archive, _mini_meb(), _mini_dds())

    result = render_bff_textured(
        archive,
        meb_resource="vehicles/bmw_m3_e36/smoke.meb",
        texture_resource="vehicles/textures/smoke.dds",
        output=out,
        width=48,
        height=48,
    )

    assert result["format"] == "SHIFT.BFFMEBTextureReferenceRender/1"
    assert result["texture"]["source_format"] == "DXT1"
    assert result["texture"]["width"] == 4
    assert result["meb"]["summary"]["uv_layers"]["130"] == 3
    assert result["render"]["mode"] == "UV0-texture-only"
    assert out.read_bytes().startswith(b"P6\n48 48\n255\n")
