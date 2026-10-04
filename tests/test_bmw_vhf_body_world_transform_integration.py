from __future__ import annotations

import hashlib
import struct
from pathlib import Path

import pytest

from bmw_vhf_body_world_transform import build_bmw_vhf_body_world_transform
from bmw_vulkan_bundle import TARGET_MEB


def _mini_meb() -> bytes:
    data = bytearray(struct.pack(">II", 1, 0))
    data += b"BMW_M3_E36_KIT00_BODY_LODA\0"
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


def _vhf() -> bytes:
    # Parent contributes X translation; body contributes Y translation.
    xml = f"""<?xml version="1.0" encoding="utf-8"?>
<CAR Name="BMW_M3_E36">
  <NODE type="HIERARCHY" Name="Root" MatrixNumber="0">
    <MATRIX id="0" Offset="2 0 0" Orientation="0 0 0 1" />
    <MATRIX id="1" Offset="0 3 0" Orientation="0 0 0 1" parent="0" />
    <NODE type="OBJECT" Name="BMW_M3_E36_KIT00_BODY_LODA" MatrixNumber="1">
      <RESOURCE Filename="{TARGET_MEB.replace('/', chr(92))}" />
    </NODE>
  </NODE>
</CAR>
"""
    return xml.encode("utf-8")


def _mini_bff(path: Path, resources: list[tuple[str, bytes]]) -> None:
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
    for index, ((name, payload), (string_offset, encoded)) in enumerate(
        zip(resources, strings)
    ):
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


def _golden(meb: bytes) -> dict:
    return {
        "format": "SHIFT.BMWGoldenAssetManifest/1",
        "golden": {
            "resource": TARGET_MEB,
            "resource_sha256": hashlib.sha256(meb).hexdigest(),
        },
    }


def test_phase656_uses_real_bff_vhf_hierarchy_and_exact_source_identity(tmp_path: Path):
    meb = _mini_meb()
    vhf = _vhf()
    archive = tmp_path / "BMW_M3_E36.bff"
    _mini_bff(
        archive,
        [
            ("vehicles/bmw_m3_e36/bmw_m3_e36.vhf", vhf),
            (TARGET_MEB, meb),
        ],
    )

    report = build_bmw_vhf_body_world_transform(archive, _golden(meb))

    assert report["ready"] is True
    assert report["source"]["matrix_number"] == "1"
    assert report["source"]["mesh_resource"].replace("\\", "/").lower() == TARGET_MEB
    assert report["source"]["mesh_sha256"] == hashlib.sha256(meb).hexdigest()
    assert report["source"]["vhf_entry"] == {
        "archive": "BMW_M3_E36.bff",
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "entry_index": 0,
        "path": "vehicles/bmw_m3_e36/bmw_m3_e36.vhf",
        "decoded_sha256": hashlib.sha256(vhf).hexdigest(),
        "decoded_size": len(vhf),
    }
    assert report["boundary"]["vhf_source_resource_identity_proven"] is True
    assert report["vhf_world_matrix"] == [
        1.0, 0.0, 0.0, 2.0,
        0.0, 1.0, 0.0, 3.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]
    assert report["world_matrix"] == [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        2.0, 3.0, 0.0, 1.0,
    ]


def test_phase656_rejects_duplicate_exact_vhf_logical_path(tmp_path: Path):
    meb = _mini_meb()
    vhf = _vhf()
    archive = tmp_path / "BMW_M3_E36.bff"
    _mini_bff(
        archive,
        [
            ("vehicles/bmw_m3_e36/bmw_m3_e36.vhf", vhf),
            ("vehicles\\bmw_m3_e36\\bmw_m3_e36.vhf", vhf),
            (TARGET_MEB, meb),
        ],
    )

    with pytest.raises(ValueError, match="exactly one canonical BMW VHF source resource.*found 2"):
        build_bmw_vhf_body_world_transform(archive, _golden(meb))
