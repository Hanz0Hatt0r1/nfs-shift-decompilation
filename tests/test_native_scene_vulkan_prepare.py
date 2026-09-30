import hashlib
import json
from pathlib import Path

import native_scene_vulkan_prepare as prepare


def _write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _set(root: Path, *, native_blockers=None, path="draw_0000"):
    child = root / "draw_0000"
    child.mkdir(parents=True, exist_ok=True)
    child_manifest = child / "bundle_manifest.json"
    _write_json(child_manifest, {
        "format": "SHIFT.VulkanDrawBundle/1",
        "ready": True,
        "blocking_reasons": [],
    })
    manifest_sha = hashlib.sha256(child_manifest.read_bytes()).hexdigest()
    manifest = {
        "format": "SHIFT.NativeSceneVulkanSet/1",
        "ready": True,
        "blocking_reasons": [],
        "draw_count": 1,
        "ready_draw_count": 1,
        "draws": [{
            "draw_order": 0,
            "binding_index": 42,
            "scene_draw_identity_sha256": "a" * 64,
            "ready": True,
            "bundle": {
                "manifest_path": "draw_0000/bundle_manifest.json",
                "manifest_sha256": manifest_sha,
            },
        }],
        "native_scene_submission": {
            "ready": False,
            "blocking_reasons": (
                native_blockers
                if native_blockers is not None
                else ["draw-0:scene-world-transform-not-executed"]
            ),
        },
    }
    _write_json(root / "bundle_set_manifest.json", manifest)
    (root / "bundle_set.paths").write_text(path + "\n", encoding="utf-8")
    return child


def _ready_child(child: Path, **kwargs):
    output = child / "vulkan_draw_prepare.json"
    _write_json(output, {
        "format": "SHIFT.VulkanDrawBundlePrepare/1",
        "ready": True,
    })
    return {
        "format": "SHIFT.VulkanDrawBundlePrepare/1",
        "ready": True,
        "blocking_reasons": [],
        "world_transform": {
            "format": "SHIFT.VulkanWorldTransformPacket/1",
            "path": "world_transform.svwt",
            "sha256": "b" * 64,
            "ready": True,
        },
    }


def test_prepare_native_scene_set_resolves_phase584_transform_blocker(
    tmp_path, monkeypatch
):
    _set(tmp_path)
    calls = []

    def child_prepare(child, **kwargs):
        calls.append((Path(child), kwargs))
        return _ready_child(Path(child), **kwargs)

    monkeypatch.setattr(
        prepare,
        "prepare_vulkan_draw_bundle",
        child_prepare,
    )

    result = prepare.prepare_native_scene_vulkan_set(
        tmp_path,
        validator="fake-validator",
    )

    assert result["format"] == "SHIFT.NativeSceneVulkanSetPrepare/1"
    assert result["ready"] is True
    assert result["draw_count"] == 1
    assert result["resolved_native_blockers"] == [
        "draw-0:scene-world-transform-not-executed"
    ]
    assert result["remaining_native_blockers"] == []
    assert result["draws"][0]["bundle_path"] == "draw_0000"
    assert result["draws"][0]["ready"] is True
    assert calls[0][0] == tmp_path / "draw_0000"
    assert calls[0][1]["validator"] == "fake-validator"
    assert result["boundary"]["relabels_scene_as_bmw"] is False
    assert result["boundary"]["native_runtime_scene_set_loader_available"] is True
    assert (tmp_path / "bundle_set_prepare.json").is_file()


def test_prepare_native_scene_set_keeps_external_resource_blocker(
    tmp_path, monkeypatch
):
    _set(
        tmp_path,
        native_blockers=[
            "draw-0:scene-world-transform-not-executed",
            "draw-0:external-sampler:runtime-resource-unresolved:s7:sampler2D",
        ],
    )
    called = False

    def child_prepare(*args, **kwargs):
        nonlocal called
        called = True
        return _ready_child(Path(args[0]))

    monkeypatch.setattr(prepare, "prepare_vulkan_draw_bundle", child_prepare)
    result = prepare.prepare_native_scene_vulkan_set(tmp_path)

    assert result["ready"] is False
    assert result["remaining_native_blockers"] == [
        "draw-0:external-sampler:runtime-resource-unresolved:s7:sampler2D"
    ]
    assert any(
        "external-sampler:runtime-resource-unresolved:s7:sampler2D" in reason
        for reason in result["blocking_reasons"]
    )
    assert called is False


def test_prepare_native_scene_set_rejects_non_relative_order_path(
    tmp_path, monkeypatch
):
    _set(tmp_path, path="out/scene/draw_0000")
    monkeypatch.setattr(
        prepare,
        "prepare_vulkan_draw_bundle",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("mismatched order path must block before child prepare")
        ),
    )

    result = prepare.prepare_native_scene_vulkan_set(tmp_path)

    assert result["ready"] is False
    assert (
        "native-scene-prepare:draw-order-path-mismatch:0"
        in result["blocking_reasons"]
    )


def test_prepare_native_scene_set_rejects_child_manifest_tamper(
    tmp_path, monkeypatch
):
    child = _set(tmp_path)
    (child / "bundle_manifest.json").write_text(
        '{"format":"SHIFT.VulkanDrawBundle/1","ready":false}',
        encoding="utf-8",
    )
    called = False

    def child_prepare(*args, **kwargs):
        nonlocal called
        called = True
        return _ready_child(Path(args[0]))

    monkeypatch.setattr(prepare, "prepare_vulkan_draw_bundle", child_prepare)
    result = prepare.prepare_native_scene_vulkan_set(tmp_path)

    assert result["ready"] is False
    assert any(
        "child-manifest-sha256-mismatch" in reason
        for reason in result["blocking_reasons"]
    )
    assert called is False
