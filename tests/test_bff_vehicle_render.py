import struct

from bff_vehicle_render import assemble_vehicle


def _mini_meb() -> bytes:
    data = bytearray()
    data += struct.pack(">I", 1)
    data += struct.pack(">I", 0)
    data += b"SMOKE\0"
    while len(data) % 4:
        data += b"\0"
    data += struct.pack("<III", 3, 1, 1)
    data += bytes(40)
    data += struct.pack("<III", 2, 0, 0)
    data += struct.pack(
        "<fffffffff",
        0.0, 0.0, 0.0,
        1.0, 0.0, 0.0,
        0.0, 1.0, 0.0,
    )
    data += b"SMOKE_MAT\0"
    while len(data) % 4:
        data += b"\0"
    data += bytes(4)
    data += struct.pack("<I", 1)
    data += struct.pack("<HHH", 0, 1, 2)
    while len(data) % 4:
        data += b"\0"
    data += bytes(4 + 40)
    return bytes(data)


def _mini_vhf() -> bytes:
    return b"""<?xml version="1.0"?>
<CAR Name="SMOKE">
  <NODE type="HIERARCHY" Name="Root" MatrixNumber="0">
    <MATRIX id="0" Offset="2.0 0.0 0.0" Orientation="0 0 0 1" />
    <NODE type="OBJECT" Name="BMW_M3_E36_KIT00_BODY_LODA" MatrixNumber="0">
      <RESOURCE Filename="vehicles\\BMW_M3_E36\\SMOKE.meb" />
    </NODE>
  </NODE>
</CAR>
"""


def _mini_bff(path, vhf: bytes, meb: bytes) -> None:
    names = [b"vehicles/bmw_m3_e36/vehicle.vhf", b"vehicles/BMW_M3_E36/SMOKE.meb"]
    records = 2
    name_base = 0x438 + records * 42
    string_base = name_base + records * 16
    string_blob = b""
    string_offsets = []
    for name in names:
        string_offsets.append(string_base + len(string_blob))
        string_blob += bytes([len(name)]) + name
    data_offset = (string_base + len(string_blob) + 0xFF) & ~0xFF
    payloads = [vhf, meb]
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


def test_vhf_vehicle_assembly_applies_world_matrix(tmp_path):
    archive = tmp_path / "smoke.bff"
    _mini_bff(archive, _mini_vhf(), _mini_meb())

    result = assemble_vehicle(
        archive,
        "VEHICLES/BMW_M3_E36/VEHICLE.VHF",
    )

    assert result["format"] == "SHIFT.BFFVehicleMesh/1"
    assert result["parts"][0]["node"] == "BMW_M3_E36_KIT00_BODY_LODA"
    assert result["vertex_count"] == 3
    assert result["triangle_count"] == 1
    assert result["vertices"][0][0] == 2.0
    assert result["vertices"][1][0] == 3.0
    assert result["unresolved"] == []
