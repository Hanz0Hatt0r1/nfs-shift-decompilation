import struct
import zlib
from pathlib import Path

import pytest

import shift_importer


def _make_bff(path: Path, payload: bytes, *, entry_type: int, x12d: int = 0, plain_size: int | None = None):
    name = b"smoke/body.bin"
    name_base = 0x438 + 42
    name_table = bytearray(16 + 1 + len(name))
    struct.pack_into("<Q", name_table, 0, name_base + 16)
    name_table[16] = len(name)
    name_table[17:17 + len(name)] = name
    x120_raw = 0x308 + len(name_table)
    data_offset = (name_base + len(name_table) + 0xFF) & ~0xFF

    record = bytearray(42)
    struct.pack_into("<Q", record, 8, data_offset)
    struct.pack_into("<I", record, 16, len(payload))
    struct.pack_into("<I", record, 20, plain_size if plain_size is not None else len(payload))
    record[32] = entry_type
    struct.pack_into("<I", record, 34, 0)
    struct.pack_into("<I", record, 38, 0)

    if x12d == 2:
        record_blob = shift_importer.rc4_crypt(bytes(record))
        name_blob = shift_importer.rc4_crypt(bytes(name_table))
        data_blob = shift_importer.rc4_crypt(payload)
    else:
        record_blob = bytes(record)
        name_blob = bytes(name_table)
        data_blob = payload

    total = data_offset + len(data_blob)
    blob = bytearray(total)
    blob[0:4] = b" KAP"
    struct.pack_into("<I", blob, 4, 3)
    struct.pack_into("<I", blob, 8, 1)
    struct.pack_into("<I", blob, 0x118, 42)
    struct.pack_into("<I", blob, 0x120, x120_raw)
    blob[0x12D] = x12d
    blob[0x130:0x130 + 42] = record_blob
    blob[name_base:name_base + len(name_blob)] = name_blob
    blob[data_offset:data_offset + len(data_blob)] = data_blob
    path.write_bytes(blob)


def test_x12d2_decrypts_record_name_and_zlib_payload(tmp_path):
    plain = b"SHIFT RC4 + zlib integration"
    compressed = zlib.compress(plain)
    path = tmp_path / "encrypted.bff"
    _make_bff(
        path,
        compressed,
        entry_type=1,
        x12d=2,
        plain_size=len(plain),
    )

    with shift_importer.BFF(path) as archive:
        assert archive.x12d == 2
        assert archive.entries[0].path == "smoke/body.bin"
        assert archive.extract_entry(archive.entries[0]) == plain


def test_x12d2_streaming_raw_extraction_preserves_rc4_state(tmp_path):
    plain = b"streaming RC4 must continue across chunk boundaries"
    path = tmp_path / "encrypted_raw.bff"
    _make_bff(path, plain, entry_type=0, x12d=2)

    with shift_importer.BFF(path) as archive:
        out = tmp_path / "out.bin"
        archive.extract_entry_to_file(archive.entries[0], out, chunk_size=3)
        assert out.read_bytes() == plain


def test_type3_dispatches_to_oodle_backend(tmp_path, monkeypatch):
    path = tmp_path / "oodle.bff"
    payload = b"fake-oodle-compressed"
    plain = b"decoded by external oodle"
    _make_bff(path, payload, entry_type=3, plain_size=len(plain))

    calls = {}

    def fake_oodle(data, expected_size):
        calls["data"] = data
        calls["expected_size"] = expected_size
        return plain

    monkeypatch.setattr(shift_importer, "oodle_decompress", fake_oodle)

    with shift_importer.BFF(path) as archive:
        assert archive.extract_entry(archive.entries[0]) == plain
        out = tmp_path / "oodle.bin"
        archive.extract_entry_to_file(archive.entries[0], out)
        assert out.read_bytes() == plain

    assert calls == {"data": payload, "expected_size": len(plain)}


def test_x12d1_is_explicitly_rejected(tmp_path):
    path = tmp_path / "x12d1.bff"
    _make_bff(path, b"payload", entry_type=0, x12d=1)
    with pytest.raises(NotImplementedError, match=r"X12d==1"):
        shift_importer.BFF(path)
