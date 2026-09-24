import struct

from bff_meb_render import render_bff_meb


def _mini_meb() -> bytes:
    data = bytearray()
    data += struct.pack(">I", 1)
    data += struct.pack(">I", 0)
    data += b"SMOKE_TRIANGLE\0"
    while len(data) % 4:
        data += b"\0"
    data += struct.pack("<III", 3, 1, 1)
    data += bytes(40)
    data += struct.pack("<III", 2, 0, 0)
    data += struct.pack(
        "<fffffffff",
        -0.7, -0.6, 0.0,
        0.7, -0.6, 0.0,
        0.0, 0.7, 0.0,
    )
    data += b"SMOKE\0"
    while len(data) % 4:
        data += b"\0"
    data += bytes(4)
    data += struct.pack("<I", 1)
    data += struct.pack("<HHH", 0, 1, 2)
    while len(data) % 4:
        data += b"\0"
    data += bytes(4 + 40)
    return bytes(data)


def _mini_bff(path, payload: bytes) -> None:
    name = b"smoke/body.meb"
    name_record = 16
    name_base = 0x438 + 42
    name_table_len = name_record + 1 + len(name)
    x120_raw = 0x308 + name_table_len
    data_offset = (name_base + name_table_len + 0xFF) & ~0xFF

    blob = bytearray(data_offset + len(payload))
    blob[0:4] = b" KAP"
    struct.pack_into("<I", blob, 4, 3)
    struct.pack_into("<I", blob, 8, 1)
    struct.pack_into("<I", blob, 0x118, 42)
    struct.pack_into("<I", blob, 0x120, x120_raw)
    struct.pack_into("<Q", blob, 0x130 + 8, data_offset)
    struct.pack_into("<I", blob, 0x130 + 16, len(payload))
    struct.pack_into("<I", blob, 0x130 + 20, len(payload))
    blob[0x130 + 32] = 0
    struct.pack_into("<Q", blob, name_base, name_base + name_record)
    blob[name_base + name_record] = len(name)
    blob[name_base + name_record + 1:name_base + name_record + 1 + len(name)] = name
    blob[data_offset:data_offset + len(payload)] = payload
    path.write_bytes(blob)


def test_real_bff_meb_adapter_renders_type0_fixture(tmp_path):
    bff = tmp_path / "smoke.bff"
    out = tmp_path / "smoke.ppm"
    mesh_json = tmp_path / "smoke.mesh.json"
    _mini_bff(bff, _mini_meb())

    result = render_bff_meb(
        bff,
        "SMOKE/BODY.MEB",
        out,
        width=64,
        height=48,
        mesh_json=mesh_json,
    )

    assert result["format"] == "SHIFT.BFFMEBReferenceRender/1"
    assert result["resource"] == "smoke/body.meb"
    assert result["mesh"]["vertex_count"] == 3
    assert result["mesh"]["triangle_count"] == 1
    assert result["render"]["color_mode"] == "flat-gray"
    assert out.read_bytes().startswith(b"P6\n64 48\n255\n")
    assert mesh_json.exists()


def test_real_bff_meb_adapter_can_select_a_single_primitive(tmp_path):
    bff = tmp_path / "smoke.bff"
    out = tmp_path / "smoke.ppm"
    _mini_bff(bff, _mini_meb())

    result = render_bff_meb(
        bff,
        "smoke/body.meb",
        out,
        width=32,
        height=32,
        primitive_index=0,
    )

    assert result["selected_primitive"]["index"] == 0
    assert result["selected_primitive"]["material"] == "SMOKE"
