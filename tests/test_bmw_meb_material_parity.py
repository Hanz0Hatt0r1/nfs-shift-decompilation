import json
import struct
import tempfile
from pathlib import Path

import bmw_meb_material_parity as mod


def _write_bff(path: Path, names):
    count = len(names)
    x118 = count * 42
    name_base = 0x438 + x118
    name_blob = bytearray()
    offsets = []
    for name in names:
        raw = name.encode()
        offsets.append(name_base + count * 16 + len(name_blob))
        name_blob.extend(bytes([len(raw)]))
        name_blob.extend(raw)

    x120_raw = count * 16 + len(name_blob) + 0x308
    data = bytearray(name_base + count * 16)
    data[0:4] = b" KAP"
    struct.pack_into("<I", data, 4, 3)
    struct.pack_into("<I", data, 8, count)
    struct.pack_into("<I", data, 0x118, x118)
    struct.pack_into("<I", data, 0x120, x120_raw)

    for i, name_offset in enumerate(offsets):
        record = 0x130 + i * 42
        struct.pack_into("<Q", data, record + 8, 0)
        struct.pack_into("<I", data, record + 16, 0)
        struct.pack_into("<I", data, record + 20, 0)
        data[record + 32] = 2
        struct.pack_into("<Q", data, name_base + i * 16, name_offset)

    data.extend(name_blob)
    path.write_bytes(data)


def _meb(tmp: Path):
    path = tmp / "m.json"
    path.write_text(json.dumps({
        "resource": mod.TARGET_RESOURCE,
        "source_sha256": mod.TARGET_SHA256,
        "primitives": [
            {
                "material": "vehicles/BMW_M3_E36/BMW_M3_E36_BADGING.mtx",
                "index_count": 150,
            },
            {
                "material": "vehicles/BMW_M3_E36/BMW_M3_E36_PAINT.mtx",
                "index_count": 6294,
            },
        ],
    }))
    return path


def test_exact_mtx_to_bmt_identity_and_reuse():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        meb = _meb(tmp)
        bff = tmp / "a.bff"
        _write_bff(bff, [
            "vehicles/bmw_m3_e36/bmw_m3_e36_badging.bmt",
            "vehicles/bmw_m3_e36/bmw_m3_e36_paint.bmt",
        ])
        report = mod.build_report(meb, bff)
        assert report["ready"] is True
        assert report["unique_material_reference_count"] == 2
        assert report["primitive_correlations"][1]["status"] == "match"


def test_missing_bmt_blocks():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        meb = _meb(tmp)
        bff = tmp / "a.bff"
        _write_bff(bff, [
            "vehicles/bmw_m3_e36/bmw_m3_e36_badging.bmt",
        ])
        report = mod.build_report(meb, bff)
        assert report["ready"] is False
        assert "material:bmt-entry-count:1:0" in report["blocking_reasons"]


def test_non_type2_bmt_blocks():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        meb = _meb(tmp)
        bff = tmp / "a.bff"
        _write_bff(bff, [
            "vehicles/bmw_m3_e36/bmw_m3_e36_badging.bmt",
            "vehicles/bmw_m3_e36/bmw_m3_e36_paint.bmt",
        ])
        raw = bytearray(bff.read_bytes())
        raw[0x130 + 42 + 32] = 1
        bff.write_bytes(raw)

        report = mod.build_report(meb, bff)
        assert report["ready"] is False
        assert "material:bmt-entry-type:1:1" in report["blocking_reasons"]


def test_wrong_resource_hash_blocks():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        meb = _meb(tmp)
        bff = tmp / "a.bff"
        _write_bff(bff, [
            "vehicles/bmw_m3_e36/bmw_m3_e36_badging.bmt",
            "vehicles/bmw_m3_e36/bmw_m3_e36_paint.bmt",
        ])
        doc = json.loads(meb.read_text())
        doc["source_sha256"] = "00" * 32
        meb.write_text(json.dumps(doc))

        report = mod.build_report(meb, bff)
        assert report["ready"] is False
        assert "material:unexpected-target-sha256" in report["blocking_reasons"]
