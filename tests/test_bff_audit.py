from pathlib import Path

import bff_audit as audit


class Entry:
    def __init__(self, path, index, typ, comp, raw, crc=123):
        self.path = path
        self.index = index
        self.offset = 0x100 + index * 0x40
        self.compressed_size = comp
        self.uncompressed_size = raw
        self.type = typ
        self.crc32_field = crc
        self.fileext = 0


class FakeBFF:
    magic = b" KAP"
    version = 3
    records_offset = 0x130
    x118 = 84
    x120 = 0x200
    x12d = 0

    def __init__(self, path):
        self.path = Path(path)
        self.entries = [
            Entry("vehicles/a/test.meb", 0, 2, 20, 40),
            Entry("vehicles/a/test.dds", 1, 2, 10, 16),
            Entry("vehicles/a/test.fxo", 2, 2, 12, 48),
            Entry("vehicles/a/test.unknown", 3, 0, 8, 8),
        ]
        self.name_base = 0x184
        self.name_end = 0x384

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def extract_entry(self, entry, type2="lzx"):
        return {
            ".meb": b"MEB-PAYLOAD",
            ".dds": b"DDS " + b"\0" * 12,
            ".fxo": b"FXOBLOB",
            ".unknown": b"raw-data",
        }[Path(entry.path).suffix]


def test_audit_archive_keeps_index_metadata_and_classifies_extensions(monkeypatch, tmp_path):
    source = tmp_path / "A.bff"
    source.write_bytes(b"fixture")
    monkeypatch.setattr(audit, "BFF", FakeBFF)
    report = audit.audit_archive(source)

    assert report["ready"] is True
    assert report["archive"]["file_count"] == 4
    assert report["summary"]["compression_types"] == {"0": 1, "2": 3}
    assert report["summary"]["categories"]["MESH"] == 1
    assert report["summary"]["categories"]["TEXTURE"] == 1
    assert report["summary"]["categories"]["SHADER_BINARY"] == 1
    assert report["summary"]["categories"]["UNKNOWN"] == 1
    assert ".unknown" in report["summary"]["unknown_extensions"]
    assert report["entries"][0]["offset"] == 0x100


def test_audit_archive_decode_records_format_and_failures(monkeypatch, tmp_path):
    source = tmp_path / "A.bff"
    source.write_bytes(b"fixture")
    monkeypatch.setattr(audit, "BFF", FakeBFF)

    def analyze(path, payload):
        if path.endswith(".fxo"):
            raise ValueError("unsupported FXO decoder")
        return {"format": "SHIFT.TEST", "analysis": {"format": "SHIFT.TEST"}}

    monkeypatch.setattr(audit, "analyze_decoded_resource", analyze)
    report = audit.audit_archive(
        source,
        decode=True,
        decode_extensions=[".meb", ".fxo"],
        max_decode=2,
    )

    assert report["summary"]["decode_attempted"] == 2
    assert report["summary"]["decode_failures"] == 1
    assert report["summary"]["decoded_formats"] == {"SHIFT.TEST": 1}
    assert report["decode_failures"][0]["path"].endswith(".fxo")
    assert report["entries"][0]["decode"]["status"] == "ok"
    assert report["entries"][2]["decode"]["status"] == "error"


def test_audit_source_merges_multiple_archives(monkeypatch, tmp_path):
    first = tmp_path / "a.bff"
    second = tmp_path / "b.bff"
    first.write_bytes(b"a")
    second.write_bytes(b"b")
    monkeypatch.setattr(audit, "BFF", FakeBFF)

    report = audit.audit_source(tmp_path)
    assert report["archive_count"] == 2
    assert report["summary"]["entries"] == 8
    assert report["summary"]["compression_types"]["2"] == 6
