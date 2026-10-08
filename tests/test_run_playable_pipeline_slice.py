from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "run_playable_pipeline_slice.py"
SPEC = importlib.util.spec_from_file_location("run_playable_pipeline_slice", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _ready_output(tmp_path: Path) -> Path:
    out = tmp_path / "out"
    plan = {
        "format": "SHIFT.NativeVerticalSliceLaunchPlan/1",
        "version": 1,
        "ready": True,
        "argv": ["/tmp/runtime", "--scene-set", "/tmp/scene"],
        "environment": {"SHIFT_NATIVE_BODY_FEEDBACK": "1"},
    }
    plan_path = out / "launch_plan.json"
    _write_json(plan_path, plan)
    _write_json(
        out / "playable_pipeline_bootstrap.json",
        {
            "format": "SHIFT.PlayableResourcePipelineBootstrap/1",
            "version": 1,
            "ready": True,
            "launch_plan_ready": True,
            "track": "Silverstone_Era3_GrandPrix",
            "vehicle": "BMW_M3_E36",
            "artifacts": {"launch_plan": str(plan_path.resolve())},
        },
    )
    return out


def test_execution_forces_launch_plan_validation_and_reuses_saved_plan(tmp_path, monkeypatch):
    out = _ready_output(tmp_path)
    captured: dict[str, object] = {}

    def fake_bootstrap(args):
        captured["bootstrap_args"] = list(args)
        return 0

    def fake_runner(argv, *, env, check):
        captured["argv"] = list(argv)
        captured["env"] = dict(env)
        captured["check"] = check
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(MODULE.bootstrap, "main", fake_bootstrap)
    result = MODULE.execute_playable_pipeline_slice(
        ["input.bff", "--output", str(out)],
        runner=fake_runner,
    )

    assert "--validate-launch-plan" in captured["bootstrap_args"]
    assert captured["argv"] == ["/tmp/runtime", "--scene-set", "/tmp/scene"]
    assert captured["env"]["SHIFT_NATIVE_BODY_FEEDBACK"] == "1"
    assert captured["check"] is False
    assert result["ready"] is True
    assert result["runtime_returncode"] == 0
    assert result["boundary"]["launch_plan_argv_reconstructed"] is False
    assert result["boundary"]["launch_plan_environment_reconstructed"] is False


def test_bootstrap_failure_prevents_runtime_execution(tmp_path, monkeypatch):
    out = tmp_path / "out"
    calls = {"runtime": 0}
    monkeypatch.setattr(MODULE.bootstrap, "main", lambda args: 2)

    def fake_runner(*args, **kwargs):
        calls["runtime"] += 1
        return SimpleNamespace(returncode=0)

    with pytest.raises(MODULE.ExecutionError, match="bootstrap failed"):
        MODULE.execute_playable_pipeline_slice(
            ["input.bff", "-o", str(out)],
            runner=fake_runner,
        )
    assert calls["runtime"] == 0


def test_missing_or_unready_launch_plan_fails_closed(tmp_path, monkeypatch):
    out = tmp_path / "out"
    _write_json(
        out / "playable_pipeline_bootstrap.json",
        {
            "format": "SHIFT.PlayableResourcePipelineBootstrap/1",
            "ready": True,
            "launch_plan_ready": False,
            "artifacts": {"launch_plan": None},
        },
    )
    monkeypatch.setattr(MODULE.bootstrap, "main", lambda args: 0)

    with pytest.raises(MODULE.ExecutionError, match="no ready validated launch plan"):
        MODULE.execute_playable_pipeline_slice(
            ["input.bff", "--output", str(out)],
            runner=lambda *args, **kwargs: pytest.fail("runtime must not run"),
        )


def test_launch_plan_path_substitution_fails_closed(tmp_path, monkeypatch):
    out = _ready_output(tmp_path)
    report_path = out / "playable_pipeline_bootstrap.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    other = out / "other-plan.json"
    _write_json(other, json.loads((out / "launch_plan.json").read_text(encoding="utf-8")))
    report["artifacts"]["launch_plan"] = str(other.resolve())
    _write_json(report_path, report)
    monkeypatch.setattr(MODULE.bootstrap, "main", lambda args: 0)

    with pytest.raises(MODULE.ExecutionError, match="path disagrees"):
        MODULE.execute_playable_pipeline_slice(
            ["input.bff", "--output", str(out)],
            runner=lambda *args, **kwargs: pytest.fail("runtime must not run"),
        )


def test_runtime_nonzero_is_reported_without_success_claim(tmp_path, monkeypatch):
    out = _ready_output(tmp_path)
    monkeypatch.setattr(MODULE.bootstrap, "main", lambda args: 0)
    result = MODULE.execute_playable_pipeline_slice(
        ["input.bff", "--output", str(out), "--validate-launch-plan"],
        runner=lambda *args, **kwargs: SimpleNamespace(returncode=7),
    )
    assert result["ready"] is False
    assert result["status"] == "runtime-failed"
    assert result["runtime_returncode"] == 7
    assert result["boundary"]["runtime_success_claimed"] is False
