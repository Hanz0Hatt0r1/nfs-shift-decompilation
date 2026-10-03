from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_cli():
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "bootstrap_native_vertical_slice_cli",
        root / "tools" / "bootstrap_native_vertical_slice.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _report(out: Path, *, profile_ready: bool = True) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    profile = out / "vertical_slice_profile.json"
    if profile_ready:
        profile.write_text(
            json.dumps({
                "format": "SHIFT.NativeVerticalSliceProfile/1",
                "version": 1,
            }),
            encoding="utf-8",
        )
    return {
        "format": "SHIFT.OfflineNativeVerticalSliceBootstrap/1",
        "version": 1,
        "status": "profile-ready" if profile_ready else "profile-blocked",
        "ready": profile_ready,
        "offline_bootstrap_ready": True,
        "profile_ready": profile_ready,
        "launch_plan_ready": False,
        "track": "Silverstone_Era3_GrandPrix",
        "vehicle": "BMW_M3_E36",
        "blocking_reasons": [] if profile_ready else ["profile:scene-set-missing"],
        "stages": {},
        "artifacts": {
            "runtime_bootstrap": str(out / "runtime-bootstrap" / "runtime_bootstrap.json"),
            "runtime_requirements": str(out / "runtime_requirements.json"),
            "profile_prepare": str(out / "vertical_slice_profile.prepare.json"),
            "profile": str(profile) if profile_ready else None,
            "launch_plan": None,
        },
        "boundary": {
            "launcher_validation_performed": False,
            "runtime_execution_claimed": False,
        },
    }


def _args(tmp_path: Path) -> list[str]:
    return [
        "Vehicles.zip",
        "Silverstone_Era3_.zip",
        "-o",
        str(tmp_path / "out"),
        "--track",
        "Silverstone_Era3_GrandPrix",
        "--vehicle",
        "BMW_M3_E36",
        "--workspace-root",
        str(tmp_path),
        "--keyboard",
        "--frames",
        "120",
    ]


def test_cli_optional_launcher_validation_writes_plan(monkeypatch, tmp_path):
    cli = _load_cli()
    out = tmp_path / "out"
    calls = {}

    def fake_bootstrap(*args, **kwargs):
        calls["bootstrap"] = {"args": args, "kwargs": kwargs}
        return _report(out)

    def fake_plan(profile_path, *, runtime, validation):
        calls["plan"] = {
            "profile": str(profile_path),
            "runtime": str(runtime),
            "validation": validation,
        }
        return {
            "format": "SHIFT.NativeVerticalSliceLaunchPlan/1",
            "version": 1,
            "ready": True,
        }

    monkeypatch.setattr(cli, "build_offline_vertical_slice_bootstrap", fake_bootstrap)
    monkeypatch.setattr(cli, "build_launch_plan", fake_plan)

    rc = cli.main(_args(tmp_path) + ["--validate-launch-plan", "--validation"])

    assert rc == 0
    persisted = json.loads((out / "vertical_slice_bootstrap.json").read_text())
    assert persisted["status"] == "launch-plan-ready"
    assert persisted["ready"] is True
    assert persisted["profile_ready"] is True
    assert persisted["launch_plan_ready"] is True
    assert persisted["boundary"]["launcher_validation_requested"] is True
    assert persisted["boundary"]["launcher_validation_performed"] is True
    assert persisted["artifacts"]["launch_plan"] == str(out / "launch_plan.json")
    plan = json.loads((out / "launch_plan.json").read_text())
    assert plan["format"] == "SHIFT.NativeVerticalSliceLaunchPlan/1"
    assert calls["plan"]["runtime"] == "native_runtime/build/shift_runtime"
    assert calls["plan"]["validation"] is True
    assert calls["bootstrap"]["kwargs"]["keyboard"] is True
    assert calls["bootstrap"]["kwargs"]["frames"] == 120


def test_cli_launcher_validation_failure_removes_stale_plan(monkeypatch, tmp_path):
    cli = _load_cli()
    out = tmp_path / "out"
    out.mkdir()
    stale = out / "launch_plan.json"
    stale.write_text('{"stale": true}\n', encoding="utf-8")

    monkeypatch.setattr(
        cli,
        "build_offline_vertical_slice_bootstrap",
        lambda *args, **kwargs: _report(out),
    )

    def fail(*args, **kwargs):
        raise cli.ProfileError("participant runtime evidence is not ready")

    monkeypatch.setattr(cli, "build_launch_plan", fail)
    rc = cli.main(_args(tmp_path) + ["--validate-launch-plan"])

    assert rc == 2
    assert not stale.exists()
    persisted = json.loads((out / "vertical_slice_bootstrap.json").read_text())
    assert persisted["status"] == "launch-plan-blocked"
    assert persisted["ready"] is False
    assert persisted["profile_ready"] is True
    assert persisted["launch_plan_ready"] is False
    assert any(
        "participant runtime evidence is not ready" in reason
        for reason in persisted["blocking_reasons"]
    )


def test_cli_blocked_profile_removes_stale_plan_without_calling_launcher(
    monkeypatch,
    tmp_path,
):
    cli = _load_cli()
    out = tmp_path / "out"
    out.mkdir()
    stale = out / "launch_plan.json"
    stale.write_text('{"stale": true}\n', encoding="utf-8")

    monkeypatch.setattr(
        cli,
        "build_offline_vertical_slice_bootstrap",
        lambda *args, **kwargs: _report(out, profile_ready=False),
    )

    def unexpected(*args, **kwargs):
        raise AssertionError("launcher must not run without a ready profile")

    monkeypatch.setattr(cli, "build_launch_plan", unexpected)
    rc = cli.main(_args(tmp_path) + ["--validate-launch-plan"])

    assert rc == 2
    assert not stale.exists()
    persisted = json.loads((out / "vertical_slice_bootstrap.json").read_text())
    assert persisted["status"] == "profile-blocked"
    assert persisted["ready"] is False
    assert persisted["profile_ready"] is False
    assert persisted["launch_plan_ready"] is False


def test_cli_without_validation_preserves_profile_ready_semantics(monkeypatch, tmp_path):
    cli = _load_cli()
    out = tmp_path / "out"
    monkeypatch.setattr(
        cli,
        "build_offline_vertical_slice_bootstrap",
        lambda *args, **kwargs: _report(out),
    )

    def unexpected(*args, **kwargs):
        raise AssertionError("launcher validation is opt-in")

    monkeypatch.setattr(cli, "build_launch_plan", unexpected)
    rc = cli.main(_args(tmp_path))

    assert rc == 0
    persisted = json.loads((out / "vertical_slice_bootstrap.json").read_text())
    assert persisted["status"] == "profile-ready"
    assert persisted["ready"] is True
    assert persisted["profile_ready"] is True
    assert persisted["launch_plan_ready"] is False
    assert persisted["boundary"]["launcher_validation_requested"] is False
