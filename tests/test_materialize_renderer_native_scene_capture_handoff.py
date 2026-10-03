from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    tools = root / "tools"
    if str(tools) not in sys.path:
        sys.path.insert(0, str(tools))
    spec = importlib.util.spec_from_file_location(
        "materialize_renderer_native_scene_capture_handoff_tested",
        tools / "materialize_renderer_native_scene_capture_handoff.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _base(tmp_path: Path, blockers=None):
    scene = _write(
        tmp_path / "phase640" / "native_scene_bundle.json",
        {"format": "SHIFT.NativeSceneBundle/1", "ready": True, "draws": []},
    )
    bridge = _write(
        tmp_path / "phase640" / "bridge.json",
        {"format": "SHIFT.SGBRenderBindingBridge/1", "ready": True},
    )
    capture = _write(
        tmp_path / "phase640" / "capture.json",
        {"format": "SHIFT.IMBRuntimeCapturePipeline/1", "pipeline_ready": True},
    )
    ir = tmp_path / "phase640" / "ir"
    _write(ir / "manifest.json", {})
    return {
        "format": "SHIFT.RendererNativeSceneHandoff/1",
        "status": "blocked",
        "ready": False,
        "scene_set_ready": False,
        "blocking_reasons": blockers or [
            "phase585:native-scene-prepare:native:draw-0:external-sampler:runtime-resource-unresolved:s3:samplerCube"
        ],
        "inputs": {
            "capture_pipeline": str(capture),
            "ir_root": str(ir),
        },
        "artifacts": {
            "native_scene_bundle": str(scene),
            "runtime_scene_bridge": str(bridge),
            "scene_set_dir": str(tmp_path / "phase640" / "old-set"),
        },
        "boundary": {
            "new_capture_required": False,
        },
    }


def test_existing_capture_completion_runs_591_590_then_retries_580_585(
    monkeypatch,
    tmp_path,
):
    mod = _load_module()
    capture_root = tmp_path / "capture"
    capture_root.mkdir()
    calls = []
    monkeypatch.setattr(
        mod,
        "materialize_renderer_native_scene_handoff",
        lambda **kwargs: _base(tmp_path),
    )

    def phase591(scene, capture):
        calls.append("591")
        return {
            "format": "SHIFT.NativeSceneInstanceTransformMatch/1",
            "status": "ready",
            "ready": True,
            "blocking_reasons": [],
            "rows": [],
        }

    def phase590(scene, bridge, capture, **kwargs):
        calls.append("590")
        assert Path(kwargs["capture_root"]) == capture_root.resolve()
        assert kwargs["instance_transform_match"]["ready"] is True
        return {
            "format": "SHIFT.NativeSceneExternalSamplerCaptureAdapter/1",
            "status": "ready",
            "ready": True,
            "blocking_reasons": [],
            "snapshot_contract": {
                "format": "SHIFT.NativeSceneExternalSamplerSnapshots/1",
                "version": 1,
                "snapshots": [],
            },
            "cube_snapshot_contract": {
                "format": "SHIFT.NativeSceneExternalSamplerCubeSnapshots/1",
                "version": 1,
                "snapshots": [{"proven": True}],
            },
        }

    def phase580(scene, bridge, ir_root, output_dir, **kwargs):
        calls.append("580")
        assert kwargs["external_sampler_snapshots"]["format"].endswith("Snapshots/1")
        assert kwargs["external_sampler_cube_snapshots"]["snapshots"] == [{"proven": True}]
        output = Path(output_dir)
        _write(
            output / "bundle_set_manifest.json",
            {
                "format": "SHIFT.NativeSceneVulkanSet/1",
                "ready": True,
                "native_scene_submission": {"ready": True, "blocking_reasons": []},
            },
        )
        (output / "bundle_set.paths").write_text("draw_0000\n", encoding="utf-8")
        return {
            "format": "SHIFT.NativeSceneVulkanSet/1",
            "ready": True,
            "blocking_reasons": [],
            "native_scene_submission": {"ready": True, "blocking_reasons": []},
        }

    def phase585(path, **kwargs):
        calls.append("585")
        _write(
            Path(path) / "bundle_set_prepare.json",
            {"format": "SHIFT.NativeSceneVulkanSetPrepare/1", "ready": True},
        )
        return {
            "format": "SHIFT.NativeSceneVulkanSetPrepare/1",
            "ready": True,
            "blocking_reasons": [],
        }

    monkeypatch.setattr(mod, "build_scene_instance_transform_match", phase591)
    monkeypatch.setattr(mod, "build_scene_external_sampler_capture_adapter", phase590)
    monkeypatch.setattr(mod, "build_native_scene_vulkan_set", phase580)
    monkeypatch.setattr(mod, "prepare_native_scene_vulkan_set", phase585)

    report = mod.materialize_renderer_native_scene_capture_handoff(
        runtime_bootstrap="runtime.json",
        renderer_source_bootstrap="renderer.json",
        output_dir=tmp_path / "out",
        capture_root=capture_root,
    )

    assert calls == ["591", "590", "580", "585"]
    assert report["ready"] is True
    assert report["scene_set_ready"] is True
    assert report["blocking_reasons"] == []
    assert report["boundary"]["phase641_existing_capture_completion_ready"] is True
    assert report["boundary"]["new_capture_required"] is False
    assert report["existing_capture_completion"]["retry_performed"] is True
    assert Path(report["artifacts"]["scene_set_prepare"]).is_file()


def test_capture_adapter_blocker_is_reported_without_recapture_claim(
    monkeypatch,
    tmp_path,
):
    mod = _load_module()
    capture_root = tmp_path / "capture"
    capture_root.mkdir()
    monkeypatch.setattr(
        mod,
        "materialize_renderer_native_scene_handoff",
        lambda **kwargs: _base(tmp_path),
    )
    monkeypatch.setattr(
        mod,
        "build_scene_instance_transform_match",
        lambda *args, **kwargs: {
            "format": "SHIFT.NativeSceneInstanceTransformMatch/1",
            "ready": False,
            "blocking_reasons": [
                "scene-instance-match:binding-7:world-matrix-constant-window-not-found"
            ],
            "rows": [],
        },
    )
    monkeypatch.setattr(
        mod,
        "build_scene_external_sampler_capture_adapter",
        lambda *args, **kwargs: {
            "format": "SHIFT.NativeSceneExternalSamplerCaptureAdapter/1",
            "ready": False,
            "blocking_reasons": [
                "scene-external-capture:binding-7:scene-draw-ambiguous:2",
                "scene-external-capture:binding-7:s3:snapshot-path-not-found",
            ],
        },
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("Phase 580 retry must not run without exact snapshots")

    monkeypatch.setattr(mod, "build_native_scene_vulkan_set", forbidden)
    report = mod.materialize_renderer_native_scene_capture_handoff(
        runtime_bootstrap="runtime.json",
        renderer_source_bootstrap="renderer.json",
        output_dir=tmp_path / "out",
        capture_root=capture_root,
    )

    assert report["ready"] is False
    assert report["scene_set_ready"] is False
    assert any("snapshot-path-not-found" in row for row in report["blocking_reasons"])
    assert any("world-matrix-constant-window-not-found" in row for row in report["blocking_reasons"])
    assert report["boundary"]["new_capture_required"] is False
    assert report["existing_capture_completion"]["retry_performed"] is False


def test_non_renderer_resource_blocker_is_not_bypassed(monkeypatch, tmp_path):
    mod = _load_module()
    base = _base(tmp_path, blockers=["phase576:runtime-shader-join:not-ready"])
    monkeypatch.setattr(
        mod,
        "materialize_renderer_native_scene_handoff",
        lambda **kwargs: base,
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("Phase 641 must not bypass an earlier proof gate")

    monkeypatch.setattr(mod, "build_scene_instance_transform_match", forbidden)
    report = mod.materialize_renderer_native_scene_capture_handoff(
        runtime_bootstrap="runtime.json",
        renderer_source_bootstrap="renderer.json",
        output_dir=tmp_path / "out",
        capture_root=tmp_path,
    )
    assert report["ready"] is False
    assert report["blocking_reasons"] == ["phase576:runtime-shader-join:not-ready"]
    assert report["boundary"]["phase641_retry_requires_phase580_or_phase585_boundary"] is True
