from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "tools" / "resource_progress_site" / "sitecustomize.py"
    spec = importlib.util.spec_from_file_location(
        "resource_progress_phase_failure_event_tested",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_failed_phase_reports_failure_and_reraises(tmp_path, capsys):
    mod = _load_module()
    source = tmp_path / "A.bff"
    source.write_bytes(b"fixture")
    tracker = mod._ProgressTracker(entry_interval=1)

    with pytest.raises(RuntimeError, match="pipeline failed"):
        with tracker.phase("resource-catalog", [source]):
            raise RuntimeError("pipeline failed")

    output = capsys.readouterr().out
    assert "phase=resource-catalog event=failed" in output
    assert "type=RuntimeError" in output
    assert "processed=0/1 done=0 failed=0" in output
    assert "phase=resource-catalog event=complete" not in output
    assert tracker._phase is None
