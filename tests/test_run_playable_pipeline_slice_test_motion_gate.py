from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "run_playable_pipeline_slice.py"
SPEC = importlib.util.spec_from_file_location(
    "run_playable_pipeline_slice_test_motion_gate",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _ready_output(tmp_path: Path, *, plan_environment: dict[str, str] | None = None) -> Path:
    out = tmp_path / "out"
    runtime = out / "shift_runtime"
    runtime.parent.mkdir(parents=True, exist_ok=True)
    runtime.write_bytes(b"runtime")
    runtime.chmod(0o755)
    plan_path = out / "launch_plan.json"
    _write_json(
        plan_path,
        {
            "format": "SHIFT.NativeVerticalSliceLaunchPlan/1",
            "ready": True,
            "argv": [str(runtime.resolve())],
            "environment": plan_environment or {"SHIFT_NATIVE_BODY_FEEDBACK": "1"},
        },
    )
    _write_json(
        out / "playable_pipeline_bootstrap.json",
        {
            "format": "SHIFT.PlayableResourcePipelineBootstrap/1",
            "ready": True,
            "launch_plan_ready": True,
            "track": "Silverstone_Era3_GrandPrix",
            "vehicle": "BMW_M3_E36",
            "artifacts": {"launch_plan": str(plan_path.resolve())},
        },
    )
    return out


def test_host_test_motion_hook_blocks_before_bootstrap_and_runtime(tmp_path, monkeypatch):
    out = tmp_path / "out"
    out.mkdir()
    stale = out / "execution_result.json"
    stale.write_text('{"ready": true}\n', encoding="utf-8")
    calls = {"bootstrap": 0, "runtime": 0}
    monkeypatch.setenv(
        MODULE.TEST_ONLY_VEHICLE_TRANSFORM_ENV,
        str(tmp_path / "test-motion.script"),
    )

    def fake_bootstrap(args):
        calls["bootstrap"] += 1
        return 0

    def fake_runner(*args, **kwargs):
        calls["runtime"] += 1
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(MODULE.bootstrap, "main", fake_bootstrap)
    with pytest.raises(MODULE.ExecutionError, match="host environment contains test-only"):
        MODULE.execute_playable_pipeline_slice(
            ["input.bff", "--output", str(out)],
            runner=fake_runner,
        )
    assert calls == {"bootstrap": 0, "runtime": 0}
    assert not stale.exists()


def test_launch_plan_test_motion_hook_blocks_before_runtime(tmp_path, monkeypatch):
    out = _ready_output(
        tmp_path,
        plan_environment={
            "SHIFT_NATIVE_BODY_FEEDBACK": "1",
            MODULE.TEST_ONLY_VEHICLE_TRANSFORM_ENV: "/tmp/regression.script",
        },
    )
    calls = {"runtime": 0}
    monkeypatch.delenv(MODULE.TEST_ONLY_VEHICLE_TRANSFORM_ENV, raising=False)
    monkeypatch.setattr(MODULE.bootstrap, "main", lambda args: 0)

    def fake_runner(*args, **kwargs):
        calls["runtime"] += 1
        return SimpleNamespace(returncode=0)

    with pytest.raises(
        MODULE.ExecutionError,
        match="validated launch-plan environment contains test-only",
    ):
        MODULE.execute_playable_pipeline_slice(
            ["input.bff", "--output", str(out)],
            runner=fake_runner,
        )
    assert calls["runtime"] == 0
    assert not (out / "execution_result.json").exists()


def test_production_body_feedback_environment_remains_allowed(tmp_path, monkeypatch):
    out = _ready_output(tmp_path)
    monkeypatch.delenv(MODULE.TEST_ONLY_VEHICLE_TRANSFORM_ENV, raising=False)
    monkeypatch.setattr(MODULE.bootstrap, "main", lambda args: 0)
    captured: dict[str, object] = {}

    def fake_runner(argv, *, env, check):
        captured["env"] = dict(env)
        return SimpleNamespace(returncode=0)

    result = MODULE.execute_playable_pipeline_slice(
        ["input.bff", "-o", str(out)],
        runner=fake_runner,
    )
    assert result["ready"] is True
    assert captured["env"]["SHIFT_NATIVE_BODY_FEEDBACK"] == "1"
    assert MODULE.TEST_ONLY_VEHICLE_TRANSFORM_ENV not in captured["env"]
    assert result["boundary"]["test_only_vehicle_world_transform_script_allowed"] is False
    assert result["boundary"]["production_persistent_vehicle_motion_required"] is True
