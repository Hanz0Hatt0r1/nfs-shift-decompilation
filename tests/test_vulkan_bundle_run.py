import json
import subprocess

import pytest
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
    (tmp_path / "native_submission_gate.json").write_text(
        json.dumps({
            "format": "SHIFT.NativeSubmissionGate/1",
            "ready": True,
            "blocking_reasons": [],
            "submesh_count": 1,
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
    assert "vulkan-runner:sampler-metadata-packet-missing" in result["blocking_reasons"]


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


def test_runner_blocks_native_execution_when_submission_gate_is_missing(
    monkeypatch, tmp_path
):
    _bundle(tmp_path)
    (tmp_path / "native_submission_gate.json").unlink()
    monkeypatch.setattr(
        "vulkan_bundle_run.compile_bmw_vulkan_bundle",
        lambda root, validator=None: _compiled_report(),
    )
    monkeypatch.setattr(
        "vulkan_bundle_run.validate_bmw_vulkan_interface",
        lambda root, report: {
            "format": "SHIFT.BMWVulkanInterfaceGate/1",
            "ready": True,
            "blocking_reasons": [],
        },
    )
    result = run_bmw_vulkan_bundle(
        tmp_path,
        executable=tmp_path / "missing-executable",
        prepare_only=False,
    )
    assert result["status"] == "blocked"
    assert "vulkan-runner:native-submission-gate-missing" in result["blocking_reasons"]


def test_runner_prepare_only_reports_gate_but_does_not_require_it(
    monkeypatch, tmp_path
):
    _bundle(tmp_path)
    (tmp_path / "native_submission_gate.json").unlink()
    monkeypatch.setattr(
        "vulkan_bundle_run.compile_bmw_vulkan_bundle",
        lambda root, validator=None: _compiled_report(),
    )
    monkeypatch.setattr(
        "vulkan_bundle_run.validate_bmw_vulkan_interface",
        lambda root, report: {
            "format": "SHIFT.BMWVulkanInterfaceGate/1",
            "ready": True,
            "blocking_reasons": [],
        },
    )
    result = run_bmw_vulkan_bundle(tmp_path, prepare_only=True)
    assert result["status"] == "ready"
    assert result["ready"] is True
    assert result["gates"]["native_submission"]["status"] == "blocked"


@pytest.mark.parametrize("validation", [False, True])
@pytest.mark.parametrize("returncode", [0, 1])
def test_runner_native_validation_failure_overrides_existing_output(
    monkeypatch, tmp_path, validation, returncode
):
    _bundle(tmp_path)
    monkeypatch.setattr(
        "vulkan_bundle_run.compile_bmw_vulkan_bundle",
        lambda root, validator=None: _compiled_report(),
    )
    monkeypatch.setattr(
        "vulkan_bundle_run.validate_bmw_vulkan_interface",
        lambda root, report: {"ready": True, "blocking_reasons": []},
    )
    executable = tmp_path / "executor"
    executable.touch()
    output = tmp_path / "render.ppm"
    output.write_bytes(b"P6\n1 1\n255\n\xff\x00\x00")
    commands = []

    def execute(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(
            command, returncode, stdout="", stderr="validation error" if returncode else ""
        )

    monkeypatch.setattr("vulkan_bundle_run.subprocess.run", execute)
    result = run_bmw_vulkan_bundle(
        tmp_path, executable=executable, output=output, validation=validation,
    )
    assert commands == [[str(executable), str(tmp_path), str(output)] + (
        ["--validation"] if validation else []
    )]
    assert result["native"]["validation_requested"] is validation
    assert result["status"] == ("failed" if returncode else "rendered")
    assert result["ready"] is (returncode == 0)
    if returncode:
        assert result["blocking_reasons"] == ["vulkan-runner:native-execution-failed"]
        assert "output_sha256" not in result["native"]


def test_runner_surfaces_structured_world_transform_execution(
    monkeypatch, tmp_path
):
    _bundle(tmp_path)
    monkeypatch.setattr(
        "vulkan_bundle_run.compile_bmw_vulkan_bundle",
        lambda root, validator=None: _compiled_report(),
    )
    monkeypatch.setattr(
        "vulkan_bundle_run.validate_bmw_vulkan_interface",
        lambda root, report: {"ready": True, "blocking_reasons": []},
    )
    executable = tmp_path / "executor"
    executable.touch()
    output = tmp_path / "render.ppm"
    output.write_bytes(b"P6\n1 1\n255\n\xff\x00\x00")

    native_report = {
        "format": "SHIFT.VulkanBundleExecution/1",
        "world_transform_present": True,
        "world_transform_executed": True,
        "world_translation_xyz": [0.1, 0.0, 0.0],
    }
    monkeypatch.setattr(
        "vulkan_bundle_run.subprocess.run",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps(native_report),
            stderr="",
        ),
    )

    result = run_bmw_vulkan_bundle(
        tmp_path,
        executable=executable,
        output=output,
    )
    assert result["status"] == "rendered"
    assert result["native"]["report"] == native_report
    assert result["native"]["world_transform_present"] is True
    assert result["native"]["world_transform_executed"] is True
    assert result["native"]["world_translation_xyz"] == [0.1, 0.0, 0.0]
