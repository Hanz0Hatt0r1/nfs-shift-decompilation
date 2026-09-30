import hashlib
import json
from pathlib import Path

import pytest

import vulkan_draw_bundle_prepare as prepare
from vulkan_bundle_interface_gate import (
    validate_bmw_vulkan_interface,
    validate_vulkan_bundle_interface,
)
from vulkan_bundle_spirv import (
    compile_bmw_vulkan_bundle,
    compile_vulkan_bundle,
)


def _write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _neutral_bundle(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    transform = root / "world_transform.svwt"
    transform.write_bytes(b"SVWT-phase585")
    transform_sha = hashlib.sha256(transform.read_bytes()).hexdigest()
    _write_json(root / "bundle_manifest.json", {
        "format": "SHIFT.VulkanDrawBundle/1",
        "ready": True,
        "blocking_reasons": [],
        "artifacts": {"shaders": []},
        "scene_transform": {
            "world_matrix": [
                1, 0, 0, 0,
                0, 1, 0, 0,
                0, 0, 1, 0,
                10, 20, 30, 1,
            ],
            "packet": {
                "format": "SHIFT.VulkanWorldTransformPacket/1",
                "path": "world_transform.svwt",
                "sha256": transform_sha,
            },
        },
    })
    _write_json(root / "native_submission_gate.json", {
        "format": "SHIFT.NativeSubmissionGate/1",
        "ready": True,
        "blocking_reasons": [],
    })
    _write_json(root / "runtime_provenance_gate.json", {
        "format": "SHIFT.VulkanDrawRuntimeProvenanceGate/1",
        "ready": True,
        "blocking_reasons": [],
    })
    return transform_sha


def _compiled():
    return {
        "format": "SHIFT.VulkanBundleSPIRV/1",
        "bundle_format": "SHIFT.VulkanDrawBundle/1",
        "ready": True,
        "status": "ready",
        "blocking_reasons": [],
        "shader_results": [],
    }


def _interface():
    return {
        "format": "SHIFT.VulkanInterfaceGate/1",
        "bundle_format": "SHIFT.VulkanDrawBundle/1",
        "ready": True,
        "status": "ready",
        "blocking_reasons": [],
        "descriptors": [],
    }


def test_neutral_bundle_compile_and_interface_apis_accept_draw_bundle(
    tmp_path, monkeypatch
):
    _neutral_bundle(tmp_path)
    monkeypatch.setattr("vulkan_bundle_spirv.shutil.which", lambda name: None)

    result = compile_vulkan_bundle(tmp_path)
    assert result["bundle_format"] == "SHIFT.VulkanDrawBundle/1"
    assert result["status"] == "unavailable"

    with pytest.raises(ValueError, match="BMWVulkanBundle"):
        compile_bmw_vulkan_bundle(tmp_path)

    interface = validate_vulkan_bundle_interface(
        tmp_path,
        {
            "format": "SHIFT.VulkanBundleSPIRV/1",
            "ready": True,
            "blocking_reasons": [],
            "shader_results": [],
        },
    )
    assert interface["format"] == "SHIFT.VulkanInterfaceGate/1"
    assert interface["bundle_format"] == "SHIFT.VulkanDrawBundle/1"
    assert interface["ready"] is True

    legacy = validate_bmw_vulkan_interface(
        tmp_path,
        {
            "format": "SHIFT.VulkanBundleSPIRV/1",
            "ready": True,
            "blocking_reasons": [],
            "shader_results": [],
        },
    )
    assert legacy["ready"] is False
    assert "vulkan-interface:invalid-bundle-format" in legacy["blocking_reasons"]


def test_prepare_neutral_draw_bundle_persists_gates_and_transform(
    tmp_path, monkeypatch
):
    transform_sha = _neutral_bundle(tmp_path)
    monkeypatch.setattr(prepare, "compile_vulkan_bundle", lambda *a, **k: _compiled())
    monkeypatch.setattr(
        prepare,
        "validate_vulkan_bundle_interface",
        lambda *a, **k: _interface(),
    )

    result = prepare.prepare_vulkan_draw_bundle(tmp_path)

    assert result["format"] == "SHIFT.VulkanDrawBundlePrepare/1"
    assert result["ready"] is True
    assert result["bundle_format"] == "SHIFT.VulkanDrawBundle/1"
    assert result["native_submission_gate_ready"] is True
    assert result["runtime_provenance_gate_ready"] is True
    assert result["world_transform"]["sha256"] == transform_sha
    assert result["boundary"]["world_transform_execution_supported"] is True
    assert result["boundary"]["executes_native_runtime"] is False
    assert (tmp_path / "spirv_report.json").is_file()
    assert (tmp_path / "vulkan_interface.json").is_file()
    assert (tmp_path / "vulkan_draw_prepare.json").is_file()


def test_prepare_neutral_draw_bundle_rejects_transform_hash_tamper(
    tmp_path, monkeypatch
):
    _neutral_bundle(tmp_path)
    manifest_path = tmp_path / "bundle_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["scene_transform"]["packet"]["sha256"] = "0" * 64
    _write_json(manifest_path, manifest)

    called = False

    def compiler(*args, **kwargs):
        nonlocal called
        called = True
        return _compiled()

    monkeypatch.setattr(prepare, "compile_vulkan_bundle", compiler)
    result = prepare.prepare_vulkan_draw_bundle(tmp_path)

    assert result["ready"] is False
    assert (
        "vulkan-draw-prepare:world-transform-sha256-mismatch"
        in result["blocking_reasons"]
    )
    assert called is False


def test_prepare_neutral_draw_bundle_requires_runtime_provenance_gate(
    tmp_path, monkeypatch
):
    _neutral_bundle(tmp_path)
    (tmp_path / "runtime_provenance_gate.json").unlink()
    monkeypatch.setattr(prepare, "compile_vulkan_bundle", lambda *a, **k: _compiled())

    result = prepare.prepare_vulkan_draw_bundle(tmp_path)

    assert result["ready"] is False
    assert (
        "vulkan-draw-prepare:runtime_provenance_gate.json:missing"
        in result["blocking_reasons"]
    )
