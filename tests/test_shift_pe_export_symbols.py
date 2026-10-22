"""Offline, synthetic PE32 tests for the retail export-anchor extractor."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "ghidra" / "export_shift_named_pe_symbols.py"
spec = importlib.util.spec_from_file_location("shift_export_symbols", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture(path: Path) -> str:
    b = bytearray(0x800)
    b[:2] = b"MZ"
    struct.pack_into("<I", b, 0x3c, 0x80)
    b[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<HH", b, 0x84, 0x14c, 2)
    struct.pack_into("<H", b, 0x80 + 20, 0xe0)
    op = 0x80 + 24
    struct.pack_into("<H", b, op, 0x10b)
    struct.pack_into("<I", b, op + 28, 0x00400000)
    struct.pack_into("<II", b, op + 96, 0x2000, 0x180)
    sec = op + 0xe0
    struct.pack_into("<8sIIII", b, sec, b".text\0\0\0", 0x200, 0x1000, 0x200, 0x200)
    struct.pack_into("<8sIIII", b, sec + 40, b".rdata\0\0", 0x400, 0x2000, 0x400, 0x400)
    # Export dir at RVA 0x2000 -> file offset 0x400.
    struct.pack_into("<IIHHIIIIIII", b, 0x400,
                     0, 0, 0, 0, 0x2060, 1, 3, 3, 0x2080, 0x2090, 0x20a0)
    b[0x460:0x460 + 10] = b"Mock.dll\0\0"
    struct.pack_into("<III", b, 0x480, 0x1010, 0x1010, 0x1030)
    struct.pack_into("<III", b, 0x490, 0x20c0, 0x20d0, 0x20e0)
    struct.pack_into("<HHH", b, 0x4a0, 0, 1, 2)
    for offset, string in ((0x4c0, b"?A@Mock@@QAEXXZ\0"),
                           (0x4d0, b"?B@Mock@@QAEXXZ\0"),
                           (0x4e0, b"?C@Mock@@QAEXXZ\0")):
        b[offset:offset + len(string)] = string
    path.write_bytes(b)
    return hashlib.sha256(b).hexdigest()


class ExportAnchorTests(unittest.TestCase):
    def test_extract_duplicate_rvas_and_image_base(self):
        with tempfile.TemporaryDirectory() as d:
            file = Path(d) / "mock.exe"
            sha = fixture(file)
            with mock.patch.object(module, "RETAIL_SHA256", sha):
                rows, meta = module.pe_exports(file)
            self.assertEqual(meta["pe_export_name"], "Mock.dll")
            self.assertEqual(len(rows), 3)
            self.assertEqual([r["va"] for r in rows],
                             ["0x00401010", "0x00401010", "0x00401030"])
            self.assertEqual(meta["unique_address_count"], 2)
            self.assertEqual([r["ordinal"] for r in rows], [1, 2, 3])
            self.assertTrue(all(r["kind"] == "code_candidate" for r in rows))

    def test_rejects_unpinned_binary(self):
        with tempfile.TemporaryDirectory() as d:
            file = Path(d) / "mock.exe"
            fixture(file)
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                module.pe_exports(file)


if __name__ == "__main__":
    unittest.main()
