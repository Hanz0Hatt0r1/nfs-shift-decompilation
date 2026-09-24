import struct

from vhf_scene_preview import build_vhf_scene, render_vhf_scene


def _mini_meb() -> bytes:
    data = bytearray(struct.pack(">II", 1, 0))
    data += b"BODY\0"
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
    data += b"BODYMAT\0"
    while len(data) % 4:
        data += b"\0"
    data += bytes(4)
    data += struct.pack("<I", 1)
    data += struct.pack("<HHH", 0, 1, 2)
    while len(data) % 4:
        data += b"\0"
    data += bytes(44)
    return bytes(data)


def _mini_vhf() -> bytes:
    xml = """<?xml version="1.0" encoding="utf-8"?>
<CAR Name="SMOKE">
  <NODE type="HIERARCHY" Name="Root" MatrixNumber="0">
    <MATRIX id="0" Offset="0 0 0" Orientation="0 0 0 1" />
    <MATRIX id="1" Offset="1 0 0" Orientation="0 0 0 1" parent="0" />
    <NODE type="OBJECT" Name="BMW_M3_E36_KIT00_BODY_LODA" MatrixNumber="1">
      <RESOURCE Filename="vehicles\BMW_M3_E36\BODY.meb" />
    </NODE>
  </NODE>
</CAR>
"""
    return xml.encode("utf-8")


def _mini_bff(path, resources):
    count = len(resources)
    name_base = 0x438 + count * 42
    strings = []
    cursor = count * 16
    for name, _payload in resources:
        encoded = name.encode("utf-8")
        strings.append((cursor, encoded))
        cursor += 1 + len(encoded)
    data_start = (name_base + cursor + 0xFF) & ~0xFF
    total = data_start + sum(len(payload) for _, payload in resources)
    blob = bytearray(total)
    blob[0:4] = b" KAP"
    struct.pack_into("<I", blob, 4, 3)
    struct.pack_into("<I", blob, 8, count)
    struct.pack_into("<I", blob, 0x118, count * 42)
    struct.pack_into("<I", blob, 0x120, 0x308 + cursor)
    data_offset = data_start
    for index, ((name, payload), (string_offset, encoded)) in enumerate(zip(resources, strings)):
        ro = 0x130 + index * 42
        struct.pack_into("<Q", blob, ro + 8, data_offset)
        struct.pack_into("<I", blob, ro + 16, len(payload))
        struct.pack_into("<I", blob, ro + 20, len(payload))
        blob[ro + 32] = 0
        no = name_base + index * 16
        struct.pack_into("<Q", blob, no, name_base + string_offset)
        string_pos = name_base + string_offset
        blob[string_pos] = len(encoded)
        blob[string_pos + 1:string_pos + 1 + len(encoded)] = encoded
        blob[data_offset:data_offset + len(payload)] = payload
        data_offset += len(payload)
    path.write_bytes(blob)


def test_vhf_scene_selects_exact_kit_and_lod(tmp_path):
    bff = tmp_path / "smoke.bff"
    _mini_bff(
        bff,
        [
            ("vehicles/bmw_m3_e36/bmw_m3_e36.vhf", _mini_vhf()),
            ("vehicles/bmw_m3_e36/body.meb", _mini_meb()),
        ],
    )
    scene = build_vhf_scene(
        bff,
        "vehicles/BMW_M3_E36/BMW_M3_E36.vhf",
        kit="00",
        lod="A",
        include_generic=False,
    )
    assert scene["format"] == "SHIFT.VHFScene/1"
    assert len(scene["parts"]) == 1
    part = scene["parts"][0]
    assert part["name"] == "BMW_M3_E36_KIT00_BODY_LODA"
    assert part["matrix_number"] == "1"
    assert part["world_matrix"][3] == 1.0
    assert part["mesh"].vertex_count == 3


def test_vhf_scene_render_writes_deterministic_ppm(tmp_path):
    bff = tmp_path / "smoke.bff"
    out = tmp_path / "scene.ppm"
    report_path = tmp_path / "scene.json"
    _mini_bff(
        bff,
        [
            ("vehicles/bmw_m3_e36/bmw_m3_e36.vhf", _mini_vhf()),
            ("vehicles/bmw_m3_e36/body.meb", _mini_meb()),
        ],
    )

    result = render_vhf_scene(
        bff,
        "vehicles/bmw_m3_e36/bmw_m3_e36.vhf",
        out,
        width=48,
        height=32,
        include_generic=False,
        scene_json=report_path,
    )

    assert result["format"] == "SHIFT.VHFSceneReferenceRender/1"
    assert result["vertex_count"] == 3
    assert result["triangle_count"] == 1
    assert result["render"]["sha256"]
    assert out.read_bytes().startswith(b"P6\n48 32\n255\n")
    assert report_path.exists()
