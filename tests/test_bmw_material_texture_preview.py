import struct

import bmw_material_texture_preview as preview


def _mini_meb() -> bytes:
    data = bytearray(struct.pack(">II", 1, 0))
    data += b"BODY\0"
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
    data += struct.pack("<III", 130, 0, 0)
    data += struct.pack("<ffffff", 0.0, 0.0, 1.0, 0.0, 0.0, 1.0)
    data += b"cars\\paint.mtx\0"
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
    header = bytearray(128)
    header[:4] = b"DDS "
    struct.pack_into("<I", header, 4, 124)
    struct.pack_into("<I", header, 8, 0x1007)
    struct.pack_into("<I", header, 12, 1)
    struct.pack_into("<I", header, 16, 1)
    struct.pack_into("<I", header, 20, 8)
    struct.pack_into("<I", header, 76, 32)
    struct.pack_into("<I", header, 80, 4)
    struct.pack_into("<I", header, 84, int.from_bytes(b"DXT1", "little"))
    block = struct.pack("<HHI", 0xF800, 0x07E0, 0)
    return bytes(header) + block


def _mini_bff(path, resources):
    count = len(resources)
    name_base = 0x438 + count * 42
    cursor = count * 16
    strings = []
    for name, _payload in resources:
        encoded = name.encode("utf-8")
        strings.append((cursor, encoded))
        cursor += 1 + len(encoded)

    data_offset = (name_base + cursor + 0xFF) & ~0xFF
    blob = bytearray(data_offset + sum(len(payload) for _, payload in resources))
    blob[0:4] = b" KAP"
    struct.pack_into("<I", blob, 4, 3)
    struct.pack_into("<I", blob, 8, count)
    struct.pack_into("<I", blob, 0x118, count * 42)
    struct.pack_into("<I", blob, 0x120, 0x308 + cursor)

    payload_offset = data_offset
    for index, ((name, payload), (string_offset, encoded)) in enumerate(zip(resources, strings)):
        ro = 0x130 + index * 42
        struct.pack_into("<Q", blob, ro + 8, payload_offset)
        struct.pack_into("<I", blob, ro + 16, len(payload))
        struct.pack_into("<I", blob, ro + 20, len(payload))
        blob[ro + 32] = 0
        no = name_base + index * 16
        struct.pack_into("<Q", blob, no, name_base + string_offset)
        string_pos = name_base + string_offset
        blob[string_pos] = len(encoded)
        blob[string_pos + 1:string_pos + 1 + len(encoded)] = encoded
        blob[payload_offset:payload_offset + len(payload)] = payload
        payload_offset += len(payload)

    path.write_bytes(blob)


def test_bmw_material_texture_preview_resolves_bmt_and_dds(tmp_path, monkeypatch):
    bff = tmp_path / "smoke.bff"
    out = tmp_path / "paint.ppm"

    _mini_bff(
        bff,
        [
            ("cars/body.meb", _mini_meb()),
            ("cars/paint.bmt", b"material"),
            ("textures/common.dds", _mini_dds()),
        ],
    )

    monkeypatch.setattr(
        preview,
        "parse_bmt_material",
        lambda _data: {
            "material": {
                "name": "PAINT",
                "shader": "bodywork.fx",
                "shaderparams": [
                    {"name": "diffuseTexture", "value": "textures/common.dds"}
                ],
            }
        },
    )

    result = preview.render_bmw_material_texture(
        bff,
        "cars/body.meb",
        out,
        material_ref="cars/paint.mtx",
        width=32,
        height=32,
    )

    assert result["format"] == "SHIFT.BMWMaterialTextureReference/1"
    assert result["meb"]["summary"]["vertex_count"] == 3
    assert result["material"]["primitive_indices"] == [0]
    assert result["texture"]["path"] == "textures/common.dds"
    assert result["texture"]["format"] == "DXT1"
    assert out.read_bytes().startswith(b"P6\n32 32\n255\n")
