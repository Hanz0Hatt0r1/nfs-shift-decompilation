from __future__ import annotations

import json
from pathlib import Path

import offline_vertical_slice_bootstrap as vertical


def _runtime_bootstrap(*, ready: bool) -> dict:
    return {
        "format": "SHIFT.OfflineRuntimeBootstrap/1",
        "version": 1,
        "status": (
            "offline-native-build-ready-runtime-gated"
            if ready else "resource-blocked"
        ),
        "offline_build_ready": ready,
        "runtime_ready": False,
        "track": "Silverstone_Era3_GrandPrix",
        "vehicle": "BMW_M3_E36",
        "blocking_reasons": [] if ready else ["track-load:root-blocked"],
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
        "blocking_reasons": ["runtime-requirement-missing:scene_set"],
    }


def test_ready_offline_bootstrap_composes_requirements_and_profile(monkeypatch, tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    out = workspace / "vertical"
    calls = {}

    def fake_bootstrap(inputs, output_dir, **kwargs):
        calls["bootstrap"] = {
            "inputs": list(inputs),
            "output": str(output_dir),
            **kwargs,
        }
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        (output / "runtime_bootstrap.json").write_text("{}\n", encoding="utf-8")
        return _runtime_bootstrap(ready=True)

    def fake_validate(**kwargs):
        calls["validated"] = kwargs
        return {
            "input_binding": {
                "format": "SHIFT.OfflineValidatedRuntimeInput/1",
                "name": "input_binding",
                "ready": True,
                "artifact": None,
            }
        }

    def fake_requirements(bootstrap, **kwargs):
        calls["requirements_bootstrap"] = bootstrap
        calls["requirements_kwargs"] = kwargs
        return _requirements()

    def fake_profile(requirements, **kwargs):
        calls["profile"] = {"requirements": requirements, **kwargs}
        return {
            "format": "SHIFT.OfflineNativeVerticalSliceProfilePrepare/1",
            "version": 1,
            "status": "profile-complete",
            "ready": True,
            "profile": {
                "format": "SHIFT.NativeVerticalSliceProfile/1",
                "version": 1,
                "workspace_root": "..",
                "persist_post_solve_body_state": True,
                "frames": 120,
            },
            "blocking_reasons": [],
            "auto_filled_inputs": ["physics_manifest"],
            "explicit_filled_inputs": ["scene_set"],
            "boundary": {},
        }

    monkeypatch.setattr(vertical, "build_offline_runtime_bootstrap", fake_bootstrap)
    monkeypatch.setattr(vertical, "validate_explicit_runtime_inputs", fake_validate)
    monkeypatch.setattr(vertical, "build_runtime_requirements", fake_requirements)
    monkeypatch.setattr(vertical, "build_vertical_slice_profile_prepare", fake_profile)

    report = vertical.build_offline_vertical_slice_bootstrap(
        ["Vehicles.zip", "Silverstone_Era3_.zip"],
        out,
        track="Silverstone_Era3_GrandPrix",
        vehicle="BMW_M3_E36",
        workspace_root=workspace,
        explicit_runtime_inputs={"scene_set": "runtime/scene"},
        keyboard=True,
        frames=120,
        decode_limit_per_archive=7,
        participant_observation_path="evidence/participant.json",
    )

    assert report["format"] == vertical.FORMAT
    assert report["status"] == "profile-ready"
    assert report["ready"] is True
    assert report["offline_bootstrap_ready"] is True
    assert report["profile_ready"] is True
    assert report["launch_plan_ready"] is False
    assert calls["bootstrap"]["decode_limit_per_archive"] == 7
    assert calls["bootstrap"]["participant_observation_path"] == "evidence/participant.json"
    assert calls["validated"]["workspace_root"] == workspace.resolve()
    assert calls["validated"]["explicit_inputs"] == {"scene_set": "runtime/scene"}
    assert calls["validated"]["keyboard"] is True
    assert calls["requirements_kwargs"]["validated_runtime_inputs"] == report["stages"]["validated_runtime_inputs"]
    assert calls["profile"]["workspace_root"] == workspace.resolve()
    assert calls["profile"]["explicit_inputs"] == {"scene_set": "runtime/scene"}
    assert calls["profile"]["keyboard"] is True
    assert calls["profile"]["frames"] == 120
    assert (out / "runtime_requirements.json").is_file()
    assert (out / "vertical_slice_profile.prepare.json").is_file()
    assert (out / "vertical_slice_profile.json").is_file()
    persisted = json.loads((out / "vertical_slice_bootstrap.json").read_text())
    assert persisted["artifacts"]["launch_plan"] is None
    assert persisted["boundary"]["runtime_execution_claimed"] is False
    assert persisted["boundary"]["explicit_runtime_inputs_launcher_validated_before_requirement_admission"] is True


def test_blocked_offline_bootstrap_cannot_be_bypassed_by_explicit_runtime_inputs(
    monkeypatch,
    tmp_path,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    out = workspace / "vertical"
    out.mkdir()
    stale_profile = out / "vertical_slice_profile.json"
    stale_profile.write_text('{"stale": true}\n', encoding="utf-8")

    def fake_bootstrap(*args, **kwargs):
        return _runtime_bootstrap(ready=False)

    monkeypatch.setattr(vertical, "build_offline_runtime_bootstrap", fake_bootstrap)
    monkeypatch.setattr(
        vertical,
        "validate_explicit_runtime_inputs",
        lambda **kwargs: {
            "scene_set": {
                "format": "SHIFT.OfflineValidatedRuntimeInput/1",
                "name": "scene_set",
                "ready": True,
                "artifact": "/tmp/scene",
            },
            "input_binding": {
                "format": "SHIFT.OfflineValidatedRuntimeInput/1",
                "name": "input_binding",
                "ready": True,
                "artifact": None,
            },
        },
    )
    monkeypatch.setattr(
        vertical,
        "build_runtime_requirements",
        lambda report, **kwargs: _requirements(),
    )

    def unexpected_profile(*args, **kwargs):
        raise AssertionError("profile builder must not run for blocked offline bootstrap")

    monkeypatch.setattr(vertical, "build_vertical_slice_profile_prepare", unexpected_profile)

    report = vertical.build_offline_vertical_slice_bootstrap(
        ["Vehicles.zip"],
        out,
        track="Silverstone_Era3_GrandPrix",
        vehicle="BMW_M3_E36",
        workspace_root=workspace,
        explicit_runtime_inputs={
            "scene_set": "runtime/scene",
            "physics_manifest": "runtime/physics.json",
        },
        keyboard=True,
        frames=120,
    )

    assert report["status"] == "offline-bootstrap-blocked"
    assert report["ready"] is False
    assert report["profile_ready"] is False
    assert not stale_profile.exists()
    assert "offline-bootstrap:track-load:root-blocked" in report["blocking_reasons"]
    prepare = json.loads((out / "vertical_slice_profile.prepare.json").read_text())
    assert prepare["ready"] is False
    assert prepare["boundary"]["offline_bootstrap_gate_bypassed"] is False


def test_profile_blocker_removes_stale_profile_and_propagates_reason(monkeypatch, tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    out = workspace / "vertical"
    out.mkdir()
    stale_profile = out / "vertical_slice_profile.json"
    stale_profile.write_text('{"stale": true}\n', encoding="utf-8")

    monkeypatch.setattr(
        vertical,
        "build_offline_runtime_bootstrap",
        lambda *args, **kwargs: _runtime_bootstrap(ready=True),
    )
    monkeypatch.setattr(vertical, "validate_explicit_runtime_inputs", lambda **kwargs: {})
    monkeypatch.setattr(
        vertical,
        "build_runtime_requirements",
        lambda report, **kwargs: _requirements(),
    )
    monkeypatch.setattr(
        vertical,
        "build_vertical_slice_profile_prepare",
        lambda *args, **kwargs: {
            "format": "SHIFT.OfflineNativeVerticalSliceProfilePrepare/1",
            "version": 1,
            "status": "blocked",
            "ready": False,
            "profile": None,
            "blocking_reasons": ["scene_set:explicit-input-required"],
            "auto_filled_inputs": [],
            "explicit_filled_inputs": [],
            "boundary": {},
        },
    )

    report = vertical.build_offline_vertical_slice_bootstrap(
        ["Vehicles.zip"],
        out,
        track="Silverstone_Era3_GrandPrix",
        vehicle="BMW_M3_E36",
        workspace_root=workspace,
        keyboard=True,
        frames=120,
    )

    assert report["status"] == "profile-blocked"
    assert report["ready"] is False
    assert "profile:scene_set:explicit-input-required" in report["blocking_reasons"]
    assert not stale_profile.exists()
    assert report["artifacts"]["profile"] is None
