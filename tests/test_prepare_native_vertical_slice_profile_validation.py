from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_cli():
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "prepare_native_vertical_slice_profile_validation_cli",
        root / "tools" / "prepare_native_vertical_slice_profile.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _prepare_report(profile_path: Path) -> dict:
    return {
        "format": "SHIFT.OfflineNativeVerticalSliceProfilePrepare/1",
        "version": 1,
        "status": "profile-complete",
        "ready": True,
        "profile": {
            "format": "SHIFT.NativeVerticalSliceProfile/1",
            "version": 1,
            "workspace_root": ".",
            "persist_post_solve_body_state": True,
        },
        "track": "Silverstone_Era3_GrandPrix",
        "vehicle": "BMW_M3_E36",
        "workspace_root": str(profile_path.parent),
        "profile_path": str(profile_path),
        "auto_filled_inputs": ["physics_manifest", "participant_boundary"],
        "explicit_filled_inputs": ["scene_set", "camera_state"],
        "blocking_reasons": [],
        "boundary": {
            "launcher_validation_performed": False,
            "launcher_validation_still_required": True,
            "runtime_execution_claimed": False,
        },
    }


def _base_args(tmp_path: Path):
    requirements = tmp_path / "runtime_requirements.json"
    requirements.write_text("{}\n", encoding="utf-8")
    profile = tmp_path / "profile.json"
    return requirements, profile, [
        str(requirements),
        "--workspace-root",
        str(tmp_path),
        "-o",
        str(profile),
        "--keyboard",
        "--frames",
        "120",
    ]


def test_cli_can_validate_profile_with_existing_launcher(monkeypatch, tmp_path):
    cli = _load_cli()
    requirements, profile, args = _base_args(tmp_path)
    calls = {}

    monkeypatch.setattr(
        cli,
        "build_vertical_slice_profile_prepare",
        lambda *a, **kw: _prepare_report(profile),
    )

    def fake_launch_plan(profile_path, *, runtime, validation):
        calls["profile"] = str(profile_path)
        calls["runtime"] = str(runtime)
        calls["validation"] = validation
        return {
            "format": "SHIFT.NativeVerticalSliceLaunchPlan/1",
            "version": 1,
            "ready": True,
        }

    monkeypatch.setattr(cli, "build_launch_plan", fake_launch_plan)
    rc = cli.main(args + ["--validate-launch-plan", "--validation"])

    assert rc == 0
    prepare = json.loads(
        profile.with_suffix(profile.suffix + ".prepare.json").read_text()
    )
    launch_plan_path = profile.with_suffix(profile.suffix + ".launch_plan.json")
    launch_plan = json.loads(launch_plan_path.read_text())
    assert prepare["status"] == "launch-plan-ready"
    assert prepare["ready"] is True
    assert prepare["profile_ready"] is True
    assert prepare["launcher_validation_ready"] is True
    assert prepare["boundary"]["launcher_validation_performed"] is True
    assert prepare["boundary"]["launcher_validation_still_required"] is False
    assert launch_plan["format"] == "SHIFT.NativeVerticalSliceLaunchPlan/1"
    assert calls["profile"] == str(profile)
    assert calls["runtime"] == "native_runtime/build/shift_runtime"
    assert calls["validation"] is True


def test_launcher_validation_error_blocks_without_inventing_replacement(
    monkeypatch,
    tmp_path,
):
    cli = _load_cli()
    requirements, profile, args = _base_args(tmp_path)
    monkeypatch.setattr(
        cli,
        "build_vertical_slice_profile_prepare",
        lambda *a, **kw: _prepare_report(profile),
    )

    def fail(*args, **kwargs):
        raise cli.ProfileError("solver frame must have magic SBFR")

    monkeypatch.setattr(cli, "build_launch_plan", fail)
    rc = cli.main(args + ["--validate-launch-plan"])

    assert rc == 2
    assert profile.is_file()
    prepare = json.loads(
        profile.with_suffix(profile.suffix + ".prepare.json").read_text()
    )
    assert prepare["status"] == "launcher-validation-blocked"
    assert prepare["ready"] is False
    assert prepare["profile_ready"] is True
    assert prepare["launcher_validation_ready"] is False
    assert any(
        "solver frame must have magic SBFR" in reason
        for reason in prepare["blocking_reasons"]
    )
    assert not profile.with_suffix(profile.suffix + ".launch_plan.json").exists()


def test_cli_does_not_validate_launcher_unless_requested(monkeypatch, tmp_path):
    cli = _load_cli()
    requirements, profile, args = _base_args(tmp_path)
    monkeypatch.setattr(
        cli,
        "build_vertical_slice_profile_prepare",
        lambda *a, **kw: _prepare_report(profile),
    )

    def unexpected(*args, **kwargs):
        raise AssertionError("launcher validation must be opt-in")

    monkeypatch.setattr(cli, "build_launch_plan", unexpected)
    rc = cli.main(args)

    assert rc == 0
    prepare = json.loads(
        profile.with_suffix(profile.suffix + ".prepare.json").read_text()
    )
    assert prepare["status"] == "profile-complete"
    assert prepare["ready"] is True
    assert prepare["profile_ready"] is True
    assert prepare["launcher_validation_requested"] is False
    assert prepare["launcher_validation_ready"] is False
    assert prepare["boundary"]["launcher_validation_performed"] is False
