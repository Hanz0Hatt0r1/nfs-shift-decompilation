from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


def _load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "tools" / "resource_progress_site" / "sitecustomize.py"
    spec = importlib.util.spec_from_file_location(
        "resource_progress_entry_completion_order_tested",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_entry_progress_is_reported_after_consumer_finishes_each_entry():
    mod = _load_module()
    completed = []

    class RecordingTracker:
        def entry(self, token, index):
            completed.append(index)

    entries = mod._ProgressEntries(
        ["first", "second"],
        RecordingTracker(),
        object(),
    )
    iterator = iter(entries)

    assert next(iterator) == "first"
    assert completed == []

    assert next(iterator) == "second"
    assert completed == [1]

    with pytest.raises(StopIteration):
        next(iterator)
    assert completed == [1, 2]
