from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "tools" / "resource_progress_site" / "sitecustomize.py"
    spec = importlib.util.spec_from_file_location(
        "resource_progress_archive_identity_fail_safe_tested",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_archive_identity_resolution_failure_does_not_block_wrapped_bff(
    monkeypatch, tmp_path
):
    mod = _load_module()
    source = tmp_path / "A.bff"
    source.write_bytes(b"fixture")
    constructed = []

    class FakeBFF:
        def __init__(self, path):
            constructed.append(path)
            self.entries = []

    tracker = mod._ProgressTracker(entry_interval=1)
    tracker._phase = mod._PhaseState(name="resource-catalog", total=1)
    ProgressBFF = mod._progress_bff_type(FakeBFF, tracker)

    def fail_resolve(self):
        raise OSError("identity resolution unavailable")

    monkeypatch.setattr(mod.Path, "resolve", fail_resolve)

    archive = ProgressBFF(source)

    assert constructed == [source]
    assert archive._token is None
    assert tracker._phase.ordinals == {}
    assert tracker._phase.outcomes == {}
