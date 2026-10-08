from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


def _load_cli():
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "bootstrap_native_vertical_slice_resource_pipeline_cli",
        root / "tools" / "bootstrap_native_vertical_slice.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def _report(out: Path, *, resource_pipeline: str = "out/offline-pipeline") -> dict:
    out.mkdir(parents=True, exist_ok=True)
    profile = out / "vertical_slice_profile.json"
    profile.write_text(
        json.dumps({
            "format": "SHIFT.NativeVerticalSliceProfile/1",
            "version": 1,
            "resource_pipeline": resource_pipeline,
        }),
        encoding="utf-8",
    )
    return {
        "format": "SHIFT.OfflineNativeVerticalSliceBootstrap/1",
        "version": 1,
        "status": "profile-ready",
        "ready": True,
        "offline_bootstrap_ready": True,
        "profile_ready": True,
        "launch_plan_ready": False,
        "track": "Silverstone_Era3_GrandPrix",
        "vehicle": "BMW_M3_E36",
        "resource_pipeline": resource_pipeline,
        "blocking_reasons": [],
        "stages": {},
        "artifacts": {
            "runtime_bootstrap": str(out / "runtime-bootstrap" / "runtime_bootstrap.json"),
            "runtime_requirements": str(out / "runtime_requirements.json"),
            "profile_prepare": str(out / "vertical_slice_profile.prepare.json"),
            "profile": str(profile),
            "launch_plan": None,
        },
        "boundary": {
            "resource_pipeline_profile_source_requested": True,
            "launcher_validation_performed": False,
            "runtime_execution_claimed": False,
        },
    }


def test_high_level_cli_forwards_resource_pipeline(monkeypatch, tmp_path):
    cli = _load_cli()
    out = tmp_path / "out"
    captured = {}

    def fake_bootstrap(*args, **kwargs):
        captured.update(kwargs)
        return _report(out)

    monkeypatch.setattr(cli, "build_offline_vertical_slice_bootstrap", fake_bootstrap)

    rc = cli.main(_args(tmp_path) + ["--resource-pipeline", "out/offline-pipeline"])

    assert rc == 0
    assert captured["resource_pipeline"] == "out/offline-pipeline"
    persisted = json.loads((out / "vertical_slice_bootstrap.json").read_text())
    assert persisted["resource_pipeline"] == "out/offline-pipeline"
    assert persisted["boundary"]["resource_pipeline_selected"] is True
    assert persisted["boundary"]["resource_pipeline_has_scene_authority"] is True


@pytest.mark.parametrize(
    ("flag", "value"),
    [
        ("--scene-set", "out/native-scene"),
        ("--physics-manifest", "out/physics.json"),
        ("--participant-boundary", "out/participant.json"),
    ],
)
def test_resource_pipeline_rejects_parallel_resource_bound_cli_inputs(
    monkeypatch,
    tmp_path,
    flag,
    value,
):
    cli = _load_cli()

    def unexpected(*args, **kwargs):
        raise AssertionError("overlap must fail before bootstrap")

    monkeypatch.setattr(cli, "build_offline_vertical_slice_bootstrap", unexpected)
    with pytest.raises(SystemExit) as exc:
        cli.main(
            _args(tmp_path)
            + ["--resource-pipeline", "out/offline-pipeline", flag, value]
        )
    assert exc.value.code == 2


def test_resource_pipeline_keeps_renderer_evidence_diagnostic_only(monkeypatch, tmp_path):
    cli = _load_cli()
    out = tmp_path / "out"

    monkeypatch.setattr(
        cli,
        "build_offline_vertical_slice_bootstrap",
        lambda *args, **kwargs: _report(out),
    )
    monkeypatch.setattr(
        cli,
        "run_source_bootstrap_production",
        lambda **kwargs: {
            "format": "SHIFT.SilverstoneRendererSourceBootstrapProductionRun/1",
            "ready": True,
            "blocking_reasons": [],
        },
    )

    def unexpected_scene_handoff(*args, **kwargs):
        raise AssertionError("resource pipeline must retain scene authority")

    monkeypatch.setattr(
        cli,
        "materialize_renderer_native_scene_handoff",
        unexpected_scene_handoff,
    )

    rc = cli.main(
        _args(tmp_path)
        + [
            "--resource-pipeline",
            "out/offline-pipeline",
            "--renderer-capture-jsonl",
            "capture.jsonl",
            "--renderer-pe-image",
            "shift.exe",
        ]
    )

    assert rc == 0
    persisted = json.loads((out / "vertical_slice_bootstrap.json").read_text())
    assert persisted["renderer_evidence_requested"] is True
    assert persisted["renderer_evidence_ready"] is True
    assert persisted["renderer_native_scene_requested"] is False
    assert persisted["renderer_native_scene_ready"] is True
    assert persisted["boundary"]["resource_pipeline_has_scene_authority"] is True
    assert persisted["boundary"]["renderer_scene_handoff_suppressed_by_resource_pipeline"] is True
