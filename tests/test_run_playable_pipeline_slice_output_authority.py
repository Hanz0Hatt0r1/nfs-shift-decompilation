from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "run_playable_pipeline_slice.py"
SPEC = importlib.util.spec_from_file_location(
    "run_playable_pipeline_slice_output_authority",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_output_authority_accepts_repeated_identical_path(tmp_path):
    out = tmp_path / "out"
    resolved = MODULE._output_from_bootstrap_args(
        [
            "input.bff",
            "-o",
            str(out),
            "--output",
            str(out),
            f"--output={out}",
        ]
    )
    assert resolved == out.resolve()


def test_output_authority_rejects_conflicting_paths_before_bootstrap(tmp_path, monkeypatch):
    first = tmp_path / "first"
    second = tmp_path / "second"
    calls = {"bootstrap": 0, "runtime": 0}

    def fake_bootstrap(args):
        calls["bootstrap"] += 1
        return 0

    def fake_runner(*args, **kwargs):
        calls["runtime"] += 1
        raise AssertionError("runtime must not execute")

    monkeypatch.setattr(MODULE.bootstrap, "main", fake_bootstrap)
    with pytest.raises(MODULE.ExecutionError, match="conflicting output authorities"):
        MODULE.execute_playable_pipeline_slice(
            [
                "input.bff",
                "--output",
                str(first),
                "--output",
                str(second),
            ],
            runner=fake_runner,
        )
    assert calls == {"bootstrap": 0, "runtime": 0}


def test_output_authority_rejects_conflicting_short_and_equals_forms(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    with pytest.raises(MODULE.ExecutionError, match="conflicting output authorities"):
        MODULE._output_from_bootstrap_args(
            ["-o", str(first), f"--output={second}"]
        )


def test_output_authority_requires_value_and_presence(tmp_path):
    with pytest.raises(MODULE.ExecutionError, match="requires a value"):
        MODULE._output_from_bootstrap_args(["input.bff", "--output"])
    with pytest.raises(MODULE.ExecutionError, match="must include"):
        MODULE._output_from_bootstrap_args(["input.bff", "--track", "Track"])
