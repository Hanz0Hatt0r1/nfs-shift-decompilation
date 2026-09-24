from pathlib import Path

import bmw_bff_intake as intake


class Entry:
    def __init__(self, path, index=0, compressed_size=10, uncompressed_size=10, entry_type=0, crc=0):
        self.path = path
        self.index = index
        self.compressed_size = compressed_size
        self.uncompressed_size = uncompressed_size
        self.type = entry_type
        self.crc = crc
        self.offset = 0


class FakeBFF:
    magic = b" KAP"
    version = 2

    def __init__(self, entries, payloads):
        self.entries = entries
        self.payloads = payloads

    def extract_entry(self, entry):
        return self.payloads[entry.path]

    def close(self):
        pass


def _setup(monkeypatch, tmp_path, *, include_bmt=True, meb_payload=b"meb"):
    archive_path = tmp_path / "BMW_M3_E36.bff"
    archive_path.write_bytes(b"fixture")
    entries = []
    payloads = {}
    if include_bmt:
        bmt = Entry(intake.TARGET_BMT, 100)
        entries.append(bmt)
        payloads[bmt.path] = b"bmt"
    meb = Entry(intake.TARGET_MEB, 863, 170520, 300764)
    entries.append(meb)
    payloads[meb.path] = meb_payload
    monkeypatch.setattr(intake, "BFF", lambda path: FakeBFF(entries, payloads))
    monkeypatch.setattr(intake, "EXPECTED_SIZE", archive_path.stat().st_size)
    monkeypatch.setattr(intake, "EXPECTED_MEB_SHA256", intake._sha256(meb_payload))
    monkeypatch.setattr(intake, "EXPECTED_MEB_SIZE", len(meb_payload))
    return archive_path


def test_bmw_bff_intake_accepts_exact_targets(monkeypatch, tmp_path):
    path = _setup(monkeypatch, tmp_path)
    report = intake.validate_bmw_bff(path)
    assert report["ready"] is True
    assert report["entries"]["paint_bmt"]["index"] == 100
    assert report["entries"]["body_meb"]["index"] == 863
    assert report["entries"]["body_meb"]["extracted_sha256"] == intake._sha256(b"meb")


def test_bmw_bff_intake_blocks_missing_paint_bmt(monkeypatch, tmp_path):
    path = _setup(monkeypatch, tmp_path, include_bmt=False)
    report = intake.validate_bmw_bff(path)
    assert report["ready"] is False
    assert "paint_bmt:entry-count-mismatch" in report["blocking_reasons"]


def test_bmw_bff_intake_blocks_wrong_meb_sha(monkeypatch, tmp_path):
    path = _setup(monkeypatch, tmp_path, meb_payload=b"wrong")
    monkeypatch.setattr(intake, "EXPECTED_MEB_SHA256", "f" * 64)
    report = intake.validate_bmw_bff(path)
    assert report["ready"] is False
    assert "body_meb:sha256-mismatch" in report["blocking_reasons"]


def test_bmw_bff_intake_blocks_archive_size_drift(monkeypatch, tmp_path):
    path = _setup(monkeypatch, tmp_path)
    monkeypatch.setattr(intake, "EXPECTED_SIZE", path.stat().st_size + 1)
    report = intake.validate_bmw_bff(path)
    assert report["ready"] is False
    assert "archive:size-mismatch" in report["blocking_reasons"]
