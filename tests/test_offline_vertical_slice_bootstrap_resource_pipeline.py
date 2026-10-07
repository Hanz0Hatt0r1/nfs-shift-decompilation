from __future__ import annotations

import json
from pathlib import Path

import offline_vertical_slice_bootstrap as vertical


def _runtime_bootstrap(*, ready: bool) -> dict:
    return {
        "format": "SHIFT.OfflineRuntimeBootstrap/1",
        "version": 1,
        "offline_build_ready": ready,
        "runtime_ready": False,
        "track": "Silverstone_Era3_GrandPrix",
        "vehicle": "BMW_M3_E36",
        "blocking_reasons": [] if ready else ["track-load:blocked"],
        "readiness": {},
        "stages": {},
        "artifacts": {},
    }


def _requirements() -> dict:
    return {
        "format": "SHIFT.OfflineNativeRuntimeRequirements/1",
        "version": 1,
        "ready": False,
        "track": "Silverstone_Era3_GrandPrix",
        "vehicle": "BMW_M3_E36",
        "requirements": [],
        "blocking_reasons": [],
    }


def test_bootstrap_forwards_resource_pipeline_only_to_profile_prepare(monkeypatch, tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    pipeline = workspace / "out" / "offline-pipeline"
    pipeline.mkdir(parents=True)
    out = workspace / "vertical"
    captured = {}

    def fake_bootstrap(*args, **kwargs):
        output = Path(args[1])
        output.mkdir(parents=True, exist_ok=True)
        (output / "runtime_bootstrap.json").write_text("{}\n", encoding="utf-8")
        return _runtime_bootstrap(ready=True)

    def fake_requirements(bootstrap, **kwargs):
        captured["requirements_kwargs"] = kwargs
        return _requirements()

    def fake_profile(requirements, **kwargs):
        captured["profile_kwargs"] = kwargs
        return {
            "format": "SHIFT.OfflineNativeVerticalSliceProfilePrepare/1",
            "version": 1,
            "status": "profile-complete",
            "ready": True,
            "resource_pipeline": "out/offline-pipeline",
            "profile": {
                "format": "SHIFT.NativeVerticalSliceProfile/1",
                "version": 1,
                "workspace_root": "..",
                "resource_pipeline": "out/offline-pipeline",
                "camera_state": "runtime/camera.json",
                "persist_post_solve_body_state": True,
                "frames": 120,
            },
            "blocking_reasons": [],
            "auto_filled_inputs": [],
            "explicit_filled_inputs": ["camera_state"],
            "boundary": {},
        }

    monkeypatch.setattr(vertical, "build_offline_runtime_bootstrap", fake_bootstrap)
    monkeypatch.setattr(vertical, "validate_explicit_runtime_inputs", lambda **kwargs: {})
    monkeypatch.setattr(vertical, "build_runtime_requirements", fake_requirements)
    monkeypatch.setattr(vertical, "build_vertical_slice_profile_prepare", fake_profile)

    report = vertical.build_offline_vertical_slice_bootstrap(
        ["Vehicles.zip", "Silverstone_Era3_.zip"],
        out,
        track="Silverstone_Era3_GrandPrix",
        vehicle="BMW_M3_E36",
        workspace_root=workspace,
        explicit_runtime_inputs={"camera_state": "runtime/camera.json"},
        resource_pipeline="out/offline-pipeline",
        keyboard=True,
        frames=120,
    )

    assert captured["profile_kwargs"]["resource_pipeline"] == "out/offline-pipeline"
    assert "resource_pipeline" not in captured["requirements_kwargs"]
    assert report["ready"] is True
    assert report["resource_pipeline"] == "out/offline-pipeline"
    assert report["boundary"]["resource_pipeline_profile_source_requested"] is True
    assert (
        report["boundary"]["resource_pipeline_profile_source_validation_deferred_to_launcher"]
        is True
    )
    assert report["boundary"]["resource_pipeline_bypasses_offline_bootstrap"] is False
    assert report["boundary"]["resource_pipeline_replaces_camera_or_body_feedback"] is False
    persisted = json.loads((out / "vertical_slice_profile.json").read_text())
    assert persisted["resource_pipeline"] == "out/offline-pipeline"


def test_resource_pipeline_cannot_bypass_blocked_offline_bootstrap(monkeypatch, tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "out" / "offline-pipeline").mkdir(parents=True)
    out = workspace / "vertical"

    monkeypatch.setattr(
        vertical,
        "build_offline_runtime_bootstrap",
        lambda *args, **kwargs: _runtime_bootstrap(ready=False),
    )
    monkeypatch.setattr(vertical, "validate_explicit_runtime_inputs", lambda **kwargs: {})
    monkeypatch.setattr(
        vertical,
        "build_runtime_requirements",
        lambda *args, **kwargs: _requirements(),
    )

    def unexpected_profile(*args, **kwargs):
        raise AssertionError("resource pipeline must not bypass blocked offline bootstrap")

    monkeypatch.setattr(vertical, "build_vertical_slice_profile_prepare", unexpected_profile)

    report = vertical.build_offline_vertical_slice_bootstrap(
        ["Vehicles.zip"],
        out,
        track="Silverstone_Era3_GrandPrix",
        vehicle="BMW_M3_E36",
        workspace_root=workspace,
        resource_pipeline="out/offline-pipeline",
        keyboard=True,
        frames=120,
    )

    assert report["ready"] is False
    assert report["status"] == "offline-bootstrap-blocked"
    assert report["resource_pipeline"] is None
    assert "offline-bootstrap:track-load:blocked" in report["blocking_reasons"]
    assert report["boundary"]["resource_pipeline_profile_source_requested"] is True
    assert report["boundary"]["resource_pipeline_bypasses_offline_bootstrap"] is False
