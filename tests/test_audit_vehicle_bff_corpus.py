from pathlib import Path
import zipfile

import audit_vehicle_bff_corpus as runtime


def _fake_archive(path: Path, *, count: int, type2: int, x12d: int = 0):
    return {
        "archive": {
            "path": str(path),
            "filename": path.name,
            "file_count": count,
            "x12d": x12d,
        },
        "summary": {
            "entries": count,
            "compression_types": {
                "0": count - type2,
                "2": type2,
            },
        },
    }


def test_audit_vehicle_corpus_directory_aggregates_headers(monkeypatch, tmp_path: Path):
    (tmp_path / "A.bff").write_bytes(b"")
    (tmp_path / "B.bff").write_bytes(b"")

    def fake_audit(source):
        reports = [
            _fake_archive(tmp_path / "A.bff", count=3, type2=2),
            _fake_archive(tmp_path / "B.bff", count=4, type2=4),
        ]
        if Path(source).name == "B.bff":
            reports = [reports[1]]
        return {"archives": reports}

    monkeypatch.setattr(runtime, "audit_source", fake_audit)

    result = runtime.audit_vehicle_corpus(tmp_path)

    assert result["archive_count"] == 2
    assert result["total_entries"] == 7
    assert result["compression_type_counts"] == {"0": 1, "2": 6}
    assert result["x12d_values"] == [0]
    assert result["ready"] is True


def test_audit_vehicle_corpus_reads_bffs_from_zip(monkeypatch, tmp_path: Path):
    archive_path = tmp_path / "Vehicles.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("cars/One.bff", b"one")
        archive.writestr("cars/Two.bff", b"two")
        archive.writestr("README.txt", b"ignore")

    seen = []

    def fake_audit(source):
        source = Path(source)
        seen.append(source)
        files = sorted(source.glob("*.bff"))
        return {
            "archives": [
                _fake_archive(
                    item,
                    count=index + 1,
                    type2=index + 1,
                )
                for index, item in enumerate(files)
            ]
        }

    monkeypatch.setattr(runtime, "audit_source", fake_audit)

    result = runtime.audit_vehicle_corpus(archive_path)

    assert result["archive_count"] == 2
    assert result["total_entries"] == 3
    assert result["compression_type_counts"] == {"0": 0, "2": 3}
    assert result["x12d_values"] == [0]
    assert result["ready"] is True
    assert len(seen) == 1
    assert all(path.is_dir() for path in seen)


def test_audit_vehicle_corpus_rejects_empty_input(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        runtime,
        "audit_source",
        lambda _source: {"archives": []},
    )
    result = runtime.audit_vehicle_corpus(tmp_path)
    assert result["archive_count"] == 0
    assert result["ready"] is False
