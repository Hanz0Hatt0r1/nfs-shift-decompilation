from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "tools" / "resource_progress_site" / "sitecustomize.py"
    spec = importlib.util.spec_from_file_location(
        "resource_progress_sitecustomize_tested",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_count_bff_inputs_matches_directory_file_and_zip(tmp_path):
    mod = _load_module()
    corpus = tmp_path / "Pakfiles"
    (corpus / "Tracks").mkdir(parents=True)
    (corpus / "Vehicles").mkdir(parents=True)
    (corpus / "Tracks" / "Track.bff").write_bytes(b"track")
    (corpus / "Vehicles" / "Car.bff").write_bytes(b"car")
    single = tmp_path / "Render.bff"
    single.write_bytes(b"render")
    bundle = tmp_path / "extra.zip"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("Dir/A.bff", b"a")
        archive.writestr("Dir/readme.txt", b"x")
        archive.writestr("Dir/B.BFF", b"b")

    assert mod._count_bff_inputs([corpus, single, bundle]) == 5


def test_progress_bff_reports_archive_and_entry_completion(tmp_path, capsys):
    mod = _load_module()
    source = tmp_path / "A.bff"
    source.write_bytes(b"fixture")

    class FakeBFF:
        def __init__(self, path):
            self.path = Path(path)
            self.entries = list(range(5))
            self.closed = False

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            self.closed = True
            return False

        def close(self):
            self.closed = True

    tracker = mod._ProgressTracker(entry_interval=2)
    ProgressBFF = mod._progress_bff_type(FakeBFF, tracker)

    with tracker.phase("resource-catalog", [source]):
        with ProgressBFF(source) as archive:
            assert list(archive.entries) == [0, 1, 2, 3, 4]

    output = capsys.readouterr().out
    assert "phase=resource-catalog event=start archives_total=1" in output
    assert "archive=1/1 status=open done=0/1" in output
    assert "archive=1/1 status=header entries=5" in output
    assert "archive=1/1 entry=2/5" in output
    assert "archive=1/1 entry=4/5" in output
    assert "archive=1/1 entry=5/5" in output
    assert "archive=1/1 status=done done=1/1" in output
    assert "event=complete processed=1/1 done=1 failed=0" in output


def test_duplicate_reopen_in_same_phase_does_not_inflate_total(tmp_path, capsys):
    mod = _load_module()
    source = tmp_path / "A.bff"
    source.write_bytes(b"fixture")

    class FakeBFF:
        def __init__(self, path):
            self.path = Path(path)
            self.entries = [1]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    tracker = mod._ProgressTracker(entry_interval=1)
    ProgressBFF = mod._progress_bff_type(FakeBFF, tracker)

    with tracker.phase("resource-catalog", [source]):
        with ProgressBFF(source) as first:
            list(first.entries)
        with ProgressBFF(source) as reopened:
            list(reopened.entries)

    output = capsys.readouterr().out
    assert output.count("status=done done=1/1") == 1
    assert "event=complete processed=1/1 done=1 failed=0" in output
