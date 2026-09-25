import json
from pathlib import Path

from bmw_vulkan_bundle import TARGET_MEB
from vulkan_bundle_run import run_bmw_vulkan_bundle


def _bundle(tmp_path):
    (tmp_path / "bundle_manifest.json").write_text(
        json.dumps({
            "format": "SHIFT.BMWVulkanBundle/1",
            "source": {"mesh_ref": TARGET_MEB},
            "artifacts": {"shaders": []},
        }),
        encoding="utf-8",
    )
    return tmp_path


def _compiled_report():
    return {
        "format": "SHIFT.VulkanBundleSPIRV/1",
        "ready": True,
        "blocking_reasons": [],
        "shader_results": [],
    }


def test_runner_blocks_when_spirv_is_not_ready(monkeypatch, tmp_path):
    _bundle(tmp_path)
    monkeypatch.setattr(
        "vulkan_bundle_run.compile_bmw_vulkan_bundle",
        lambda root, validator=None: {
            "format": "SHIFT.VulkanBundleSPIRV/1",
            "ready": False,
            "blocking_reasons": ["vulkan-bundle-spirv:validator-unavailable"],
        },
    )
    result = run_bmw_vulkan_bundle(tmp_path, prepare_only=True)
    assert result["status"] == "blocked"
    assert "vulkan-bundle-spirv:validator-unavailable" in result["blocking_reasons"]


def test_runner_prepare_only_requires_both_gates(monkeypatch, tmp_path):
    _bundle(tmp_path)
    monkeypatch.setattr(
        "vulkan_bundle_run.compile_bmw_vulkan_bundle",
        lambda root, validator=None: _compiled_report(),
    )
    monkeypatch.setattr(
        "vulkan_bundle_run.validate_bmw_vulkan_interface",
        lambda root, report: {
            "format": "SHIFT.BMWVulkanInterfaceGate/1",
            "ready": True,
            "status": "ready",
            "blocking_reasons": [],
        },
    )
    result = run_bmw_vulkan_bundle(tmp_path, prepare_only=True)
    assert result["status"] == "ready"
    assert result["ready"] is True
    assert (tmp_path / "spirv_report.json").is_file()
    assert (tmp_path / "vulkan_interface.json").is_file()


def test_runner_blocks_missing_native_executable(monkeypatch, tmp_path):
    _bundle(tmp_path)
    monkeypatch.setattr(
        "vulkan_bundle_run.compile_bmw_vulkan_bundle",
        lambda root, validator=None: _compiled_report(),
    )
    monkeypatch.setattr(
        "vulkan_bundle_run.validate_bmw_vulkan_interface",
        lambda root, report: {
            "format": "SHIFT.BMWVulkanInterfaceGate/1",
            "ready": True,
            "status": "ready",
            "blocking_reasons": [],
        },
    )
    result = run_bmw_vulkan_bundle(
        tmp_path,
        executable=tmp_path / "missing",
    )
    assert result["status"] == "blocked"
    assert result["native"]["status"] == "executable-missing"
