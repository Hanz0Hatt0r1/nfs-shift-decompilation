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


def test_vulkan_runner_blocks_sampler_metadata_packet_hash_mismatch(tmp_path):
    from vulkan_bundle_run import run_bmw_vulkan_bundle
    _bundle(tmp_path)
    metadata = {
        "format": "SHIFT.VulkanSamplerMetadata/1",
        "version": 1,
        "packet": {"path": "textures.svtp", "sha256": "0" * 64},
        "sampler_contract": {
            "format": "SHIFT.VulkanSamplerContract/1",
            "ready": True,
            "blocking_reasons": [],
        },
    }
    (tmp_path / "sampler_contracts.meta.json").write_text(
        json.dumps(metadata), encoding="utf-8"
    )
    result = run_bmw_vulkan_bundle(
        tmp_path,
        executable=tmp_path / "missing-executable",
        validator=None,
        prepare_only=True,
    )
    assert result["status"] == "blocked"
    assert "vulkan-runner:sampler-metadata-packet-sha256-mismatch" in result["blocking_reasons"]


def test_vulkan_runner_allows_legacy_bundle_without_sampler_sidecar(tmp_path, monkeypatch):
    _bundle(tmp_path)
    monkeypatch.setattr(
        "vulkan_bundle_run.compile_bmw_vulkan_bundle",
        lambda root, validator=None: {
            "format": "SHIFT.VulkanBundleSPIRV/1",
            "ready": True,
            "blocking_reasons": [],
        },
    )
    monkeypatch.setattr(
        "vulkan_bundle_run.validate_bmw_vulkan_interface",
        lambda root, report: {"format": "SHIFT.BMWVulkanInterfaceGate/1", "ready": True, "blocking_reasons": []},
    )
    result = run_bmw_vulkan_bundle(
        tmp_path,
        executable=tmp_path / "missing-executable",
        prepare_only=True,
    )
    assert result["status"] == "ready"
