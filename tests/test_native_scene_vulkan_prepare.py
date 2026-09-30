import json

import native_scene_vulkan_prepare as prepare


def _scene_set(tmp_path):
    child = tmp_path / "draw_0000"
    child.mkdir()
    (child / "bundle_manifest.json").write_text(
        json.dumps({
            "format": "SHIFT.VulkanDrawBundle/1",
            "ready": True,
            "blocking_reasons": [],
            "scene_transform": {
                "world_matrix": [
                    1.0, 0.0, 0.0, 0.0,
                    0.0, 1.0, 0.0, 0.0,
                    0.0, 0.0, 1.0, 0.0,
                    1.0, 2.0, 3.0, 1.0,
                ],
            },
        }),
        encoding="utf-8",
    )
    (child / "world_transform.svwt").write_bytes(b"SVWT-test")
    manifest = {
        "format": "SHIFT.NativeSceneVulkanSet/1",
        "ready": True,
        "blocking_reasons": [],
        "draw_count": 1,
        "native_scene_submission": {
            "ready": True,
            "blocking_reasons": [],
        },
        "draws": [{
            "draw_order": 0,
            "binding_index": 17,
            "ready": True,
            "bundle": {
                "manifest_path": "draw_0000/bundle_manifest.json",
            },
            "scene_draw_identity_sha256": "a" * 64,
        }],
    }
    (tmp_path / "bundle_set_manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    (tmp_path / "bundle_set.paths").write_text(
        "draw_0000\n",
        encoding="utf-8",
    )
    return child


def test_scene_prepare_reuses_child_compile_and_interface_gates(
    monkeypatch,
    tmp_path,
):
    child = _scene_set(tmp_path)

    def run(root, validator=None, prepare_only=False):
        assert root == child
        assert prepare_only is True
        (child / "spirv_report.json").write_text(
            json.dumps({
                "format": "SHIFT.VulkanBundleSPIRV/1",
                "ready": True,
            }),
            encoding="utf-8",
        )
        (child / "vulkan_interface.json").write_text(
            json.dumps({
                "format": "SHIFT.BMWVulkanInterfaceGate/1",
                "ready": True,
            }),
            encoding="utf-8",
        )
        return {
            "status": "ready",
            "ready": True,
            "blocking_reasons": [],
        }

    monkeypatch.setattr(
        prepare,
        "run_bmw_vulkan_bundle",
        run,
    )
    report = prepare.prepare_native_scene_vulkan_set(tmp_path)

    assert report["format"] == "SHIFT.NativeSceneVulkanSetPrepare/1"
    assert report["ready"] is True
    assert report["draw_count"] == 1
    assert report["draws"][0]["bundle_path"] == "draw_0000"
    assert report["draws"][0]["world_transform"]["sha256"]
    assert report["boundary"]["child_bundle_format"] == (
        "SHIFT.VulkanDrawBundle/1"
    )
    assert report["boundary"]["bmw_bundle_set_equivalence"] is False
    persisted = json.loads(
        (tmp_path / "native_scene_set_prepare.json").read_text(
            encoding="utf-8"
        )
    )
    assert persisted["ready"] is True


def test_scene_prepare_rejects_absolute_child_path(monkeypatch, tmp_path):
    _scene_set(tmp_path)
    (tmp_path / "bundle_set.paths").write_text(
        "/tmp/draw_0000\n",
        encoding="utf-8",
    )
    report = prepare.prepare_native_scene_vulkan_set(tmp_path)

    assert report["ready"] is False
    assert (
        "native-scene-prepare:unsafe-bundle-path:0"
        in report["blocking_reasons"]
    )


def test_scene_prepare_rejects_unresolved_external_runtime_gate(
    tmp_path,
):
    _scene_set(tmp_path)
    manifest_path = tmp_path / "bundle_set_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["native_scene_submission"] = {
        "ready": False,
        "blocking_reasons": [
            "draw-0:external-sampler:runtime-resource-unresolved:s7:sampler2D"
        ],
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = prepare.prepare_native_scene_vulkan_set(tmp_path)
    assert report["ready"] is False
    assert any(
        "external-sampler:runtime-resource-unresolved" in reason
        for reason in report["blocking_reasons"]
    )


def test_scene_prepare_requires_neutral_child_bundle(monkeypatch, tmp_path):
    child = _scene_set(tmp_path)
    child_manifest = json.loads(
        (child / "bundle_manifest.json").read_text(encoding="utf-8")
    )
    child_manifest["format"] = "SHIFT.BMWVulkanBundle/1"
    (child / "bundle_manifest.json").write_text(
        json.dumps(child_manifest),
        encoding="utf-8",
    )
    report = prepare.prepare_native_scene_vulkan_set(tmp_path)

    assert report["ready"] is False
    assert (
        "native-scene-prepare:draw-0:child-manifest-not-neutral-vulkan-draw"
        in report["blocking_reasons"]
    )
