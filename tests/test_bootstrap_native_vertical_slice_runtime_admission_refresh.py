from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    tools = str(root / "tools")
    if tools not in sys.path:
        sys.path.insert(0, tools)
    spec = importlib.util.spec_from_file_location(
        "bootstrap_native_vertical_slice_runtime_admission_refresh",
        root / "tools" / "bootstrap_native_vertical_slice.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_renderer_refresh_preserves_validated_runtime_input_admission(monkeypatch, tmp_path):
    mod = _load_module()
    captured = {}
    validated = {
        "camera_state": {
            "format": "SHIFT.OfflineValidatedRuntimeInput/1",
            "name": "camera_state",
            "ready": True,
            "artifact": str(tmp_path / "camera.json"),
        },
        "input_binding": {
            "format": "SHIFT.OfflineValidatedRuntimeInput/1",
            "name": "input_binding",
            "ready": True,
            "artifact": None,
        },
    }
    report = {
        "stages": {
            "runtime_bootstrap": {
                "format": "SHIFT.OfflineRuntimeBootstrap/1",
            },
            "validated_runtime_inputs": validated,
        },
        "artifacts": {
            "runtime_requirements": str(tmp_path / "runtime_requirements.json"),
            "profile_prepare": str(tmp_path / "prepare.json"),
        },
    }

    def fake_requirements(bootstrap, **kwargs):
        captured["bootstrap"] = bootstrap
        captured["kwargs"] = kwargs
        return {
            "format": "SHIFT.OfflineNativeRuntimeRequirements/1",
            "requirements": [],
        }

    monkeypatch.setattr(mod, "build_runtime_requirements", fake_requirements)
    monkeypatch.setattr(
        mod,
        "build_vertical_slice_profile_prepare",
        lambda *args, **kwargs: {
            "format": "SHIFT.OfflineNativeVerticalSliceProfilePrepare/1",
            "ready": False,
            "blocking_reasons": ["camera_state:explicit-input-required"],
        },
    )

    reasons = mod._refresh_runtime_profile(
        report,
        out=tmp_path,
        workspace_root=tmp_path,
        explicit={},
        runtime_scene_handoff={
            "format": "SHIFT.RendererNativeSceneHandoff/1",
            "ready": True,
            "scene_set_ready": True,
        },
        input_script=None,
        interactive=False,
        keyboard=True,
        frames=120,
    )

    assert captured["kwargs"]["validated_runtime_inputs"] == validated
    assert captured["kwargs"]["runtime_scene_handoff"]["scene_set_ready"] is True
    assert report["stages"]["validated_runtime_inputs"] == validated
    assert reasons == ["profile:camera_state:explicit-input-required"]


def test_renderer_refresh_without_validation_stage_remains_fail_closed(monkeypatch, tmp_path):
    mod = _load_module()
    captured = {}
    report = {
        "stages": {
            "runtime_bootstrap": {
                "format": "SHIFT.OfflineRuntimeBootstrap/1",
            },
        },
        "artifacts": {},
    }

    def fake_requirements(bootstrap, **kwargs):
        captured.update(kwargs)
        return {
            "format": "SHIFT.OfflineNativeRuntimeRequirements/1",
            "requirements": [],
        }

    monkeypatch.setattr(mod, "build_runtime_requirements", fake_requirements)
    monkeypatch.setattr(
        mod,
        "build_vertical_slice_profile_prepare",
        lambda *args, **kwargs: {
            "format": "SHIFT.OfflineNativeVerticalSliceProfilePrepare/1",
            "ready": False,
            "blocking_reasons": ["scene_set:explicit-input-required"],
        },
    )

    mod._refresh_runtime_profile(
        report,
        out=tmp_path,
        workspace_root=tmp_path,
        explicit={},
        runtime_scene_handoff=None,
        input_script=None,
        interactive=False,
        keyboard=True,
        frames=120,
    )

    assert captured["validated_runtime_inputs"] is None
