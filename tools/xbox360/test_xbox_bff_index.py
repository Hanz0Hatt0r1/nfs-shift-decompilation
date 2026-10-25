#!/usr/bin/env python3
"""Focused regression coverage for the Xbox big-endian PAK/BFF index reader."""

from __future__ import annotations

import struct
import tempfile
import unittest
from pathlib import Path

from audit_xbox_bff_index import parse_archive


def make_archive(entries: list[tuple[str, bytes]], endian: str = ">") -> bytes:
    record_bytes = len(entries) * 42
    name_base = 0x438 + record_bytes
    name_records = bytearray(len(entries) * 16)
    strings = bytearray()
    records = bytearray(record_bytes)
    payloads = bytearray()
    payload_base = name_base + len(name_records) + sum(1 + len(name.encode()) for name, _ in entries)

    for index, (name, payload) in enumerate(entries):
        encoded_name = name.encode()
        name_offset = name_base + len(name_records) + len(strings)
        struct.pack_into(f"{endian}Q", name_records, index * 16, name_offset)
        strings.extend(bytes([len(encoded_name)]))
        strings.extend(encoded_name)

        record_at = index * 42
        payload_offset = payload_base + len(payloads)
        struct.pack_into(f"{endian}Q", records, record_at + 8, payload_offset)
        struct.pack_into(f"{endian}I", records, record_at + 16, len(payload))
        struct.pack_into(f"{endian}I", records, record_at + 20, len(payload))
        records[record_at + 32] = 0
        payloads.extend(payload)

    name_table = bytes(name_records + strings)
    header = bytearray(0x130)
    header[:4] = b"PAK "
    header[:4] = b"PAK " if endian == ">" else b" KAP"
    struct.pack_into(f"{endian}I", header, 4, 0x10400003)
    struct.pack_into(f"{endian}I", header, 8, len(entries))
    struct.pack_into(f"{endian}I", header, 0x118, record_bytes)
    struct.pack_into(f"{endian}I", header, 0x120, len(name_table) + 0x308)
    header[0x12D] = 0

    padding = bytes(name_base - len(header) - len(records))
    return bytes(header) + bytes(records) + padding + name_table + bytes(payloads)


class XboxBffIndexTest(unittest.TestCase):
    def test_reads_big_endian_members_and_payload_ranges(self) -> None:
        data = make_archive(
            [
                ("gui/menu_background/background01.sgx", b"shader"),
                ("cameras/cameraconfig.xml", b"config"),
            ]
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "fixture.bff"
            path.write_bytes(data)
            entries = parse_archive(path)

        self.assertEqual([entry.path for entry in entries], [
            "gui/menu_background/background01.sgx",
            "cameras/cameraconfig.xml",
        ])
        self.assertEqual([entry.compressed_size for entry in entries], [6, 6])

    def test_reads_little_endian_kap_variant(self) -> None:
        data = make_archive([("Assets/Options/0", b"option")], endian="<")
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "OPTIONS.BFF"
            path.write_bytes(data)
            entries = parse_archive(path)
        self.assertEqual([entry.path for entry in entries], ["Assets/Options/0"])

    def test_rejects_payload_outside_archive(self) -> None:
        data = bytearray(make_archive([("one.bin", b"x")]))
        struct.pack_into(">Q", data, 0x130 + 8, len(data) + 1)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bad.bff"
            path.write_bytes(data)
            with self.assertRaisesRegex(ValueError, "payload is out of bounds"):
                parse_archive(path)

    def test_rejects_little_endian_or_non_pak_header(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bad.bff"
            path.write_bytes(b"not a PAK" + bytes(0x130))
            with self.assertRaisesRegex(ValueError, "invalid or truncated"):
                parse_archive(path)


if __name__ == "__main__":
    unittest.main()
