from __future__ import annotations

import importlib.util
import sys
import zipfile
from pathlib import Path

import pytest


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "tools" / "resource_progress_site" / "sitecustomize.py"
    spec = importlib.util.spec_from_file_location(
        "resource_progress_sitecustomize_tested",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_emit_swallows_stream_failures():
    mod = _load_module()

    class BrokenStream:
        def write(self, value):
            raise OSError("stream closed")

        def flush(self):
            raise OSError("stream closed")

    mod._emit("diagnostic", stream=BrokenStream())


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

    assert mod._count_bff_inputs([
        corpus,
        single,
        bundle,
        single,
        corpus,
        corpus / "Tracks" / "Track.bff",
    ]) == 5


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

    with tracker.phase("resource-catalog", [source, source]):
        with ProgressBFF(source) as first:
            list(first.entries)
        with ProgressBFF(source) as reopened:
            list(reopened.entries)

    output = capsys.readouterr().out
    assert output.count("status=done done=1/1") == 1
    assert "event=complete processed=1/1 done=1 failed=0" in output


def test_reopen_failure_downgrades_prior_done_outcome(tmp_path, capsys):
    mod = _load_module()
    source = tmp_path / "A.bff"
    source.write_bytes(b"fixture")

    class FlakyBFF:
        attempts = 0

        def __init__(self, path):
            type(self).attempts += 1
            if type(self).attempts == 2:
                raise RuntimeError("reopen failed")
            self.path = Path(path)
            self.entries = [1]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    tracker = mod._ProgressTracker(entry_interval=1)
    ProgressBFF = mod._progress_bff_type(FlakyBFF, tracker)

    with tracker.phase("resource-catalog", [source]):
        with ProgressBFF(source) as first:
            list(first.entries)
        with pytest.raises(RuntimeError, match="reopen failed"):
            ProgressBFF(source)

    output = capsys.readouterr().out
    assert output.count("status=done done=1/1") == 1
    assert "status=failed" in output
    assert "error=RuntimeError" in output
    assert "event=complete processed=1/1 done=0 failed=1" in output


def test_progress_bff_reports_enter_failure_as_failed(tmp_path, capsys):
    mod = _load_module()
    source = tmp_path / "A.bff"
    source.write_bytes(b"fixture")

    class FakeBFF:
        def __init__(self, path):
            self.path = Path(path)
            self.entries = []

        def __enter__(self):
            raise RuntimeError("enter failed")

        def __exit__(self, exc_type, exc, tb):
            return False

    tracker = mod._ProgressTracker(entry_interval=1)
    ProgressBFF = mod._progress_bff_type(FakeBFF, tracker)

    with tracker.phase("resource-catalog", [source]):
        with pytest.raises(RuntimeError, match="enter failed"):
            with ProgressBFF(source):
                pass

    output = capsys.readouterr().out
    assert "status=failed" in output
    assert "error=RuntimeError" in output
    assert "status=done" not in output
    assert "event=complete processed=1/1 done=0 failed=1" in output


def test_progress_bff_reports_close_failure_as_failed(tmp_path, capsys):
    mod = _load_module()
    source = tmp_path / "A.bff"
    source.write_bytes(b"fixture")

    class FakeBFF:
        def __init__(self, path):
            self.path = Path(path)
            self.entries = []

        def close(self):
            raise OSError("close failed")

    tracker = mod._ProgressTracker(entry_interval=1)
    ProgressBFF = mod._progress_bff_type(FakeBFF, tracker)

    with tracker.phase("resource-catalog", [source]):
        archive = ProgressBFF(source)
        with pytest.raises(OSError, match="close failed"):
            archive.close()

    output = capsys.readouterr().out
    assert "status=failed" in output
    assert "error=OSError" in output
    assert "status=done" not in output
    assert "event=complete processed=1/1 done=0 failed=1" in output


def test_archive_count_failure_does_not_block_wrapped_work_or_leak_phase(tmp_path, capsys):
    mod = _load_module()
    outer_source = tmp_path / "Outer.bff"
    outer_source.write_bytes(b"fixture")
    broken_zip = tmp_path / "broken.zip"
    broken_zip.write_bytes(b"not a zip archive")
    tracker = mod._ProgressTracker(entry_interval=1)

    with tracker.phase("outer", [outer_source]):
        outer_state = tracker._phase
        assert outer_state is not None
        ran = False
        with tracker.phase("inner", [broken_zip]):
            ran = True
            assert tracker._phase is None
        assert ran
        assert tracker._phase is outer_state

    captured = capsys.readouterr()
    assert "phase=inner event=count-unavailable" in captured.err
    assert "type=BadZipFile" in captured.err
    assert "phase=inner event=start" not in captured.out
    assert "phase=outer event=complete" in captured.out
