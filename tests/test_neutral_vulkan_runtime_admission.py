import json

from vulkan_bundle_interface_gate import validate_vulkan_interface
from vulkan_bundle_run import run_vulkan_bundle
from vulkan_bundle_spirv import compile_vulkan_bundle


def _neutral_manifest(tmp_path):
    (tmp_path / "bundle_manifest.json").write_text(
        json.dumps({
            "format": "SHIFT.VulkanDrawBundle/1",
            "ready": True,
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
    (tmp_path / "runtime_provenance_gate.json").write_text(
        json.dumps({
            "format": "SHIFT.VulkanDrawRuntimeProvenanceGate/1",
            "required": True,
            "ready": True,
            "blocking_reasons": [],
        }),
        encoding="utf-8",
    )


def test_spirv_compiler_admits_neutral_bundle_format(monkeypatch, tmp_path):
    _neutral_manifest(tmp_path)
    monkeypatch.setattr(
        "vulkan_bundle_spirv.shutil.which",
        lambda name: None,
    )
    result = compile_vulkan_bundle(tmp_path)

    assert result["format"] == "SHIFT.VulkanBundleSPIRV/1"
    assert result["source_bundle_format"] == "SHIFT.VulkanDrawBundle/1"
    assert result["status"] == "unavailable"
    assert result["blocking_reasons"] == [
        "vulkan-bundle-spirv:validator-unavailable"
    ]


def test_interface_gate_emits_neutral_format_for_neutral_bundle(tmp_path):
    _neutral_manifest(tmp_path)
    report = {
        "format": "SHIFT.VulkanBundleSPIRV/1",
        "ready": True,
        "blocking_reasons": [],
        "shader_results": [],
    }
    result = validate_vulkan_interface(tmp_path, report)

    assert result["format"] == "SHIFT.VulkanInterfaceGate/1"
    assert result["source_bundle_format"] == "SHIFT.VulkanDrawBundle/1"
    assert result["ready"] is True


def test_neutral_runner_requires_runtime_provenance_gate(
    monkeypatch,
    tmp_path,
):
    _neutral_manifest(tmp_path)
    (tmp_path / "runtime_provenance_gate.json").unlink()

    monkeypatch.setattr(
        "vulkan_bundle_run.compile_bmw_vulkan_bundle",
        lambda root, validator=None: {
            "format": "SHIFT.VulkanBundleSPIRV/1",
            "ready": True,
            "blocking_reasons": [],
            "shader_results": [],
        },
    )
    monkeypatch.setattr(
        "vulkan_bundle_run.validate_bmw_vulkan_interface",
        lambda root, report: {
            "format": "SHIFT.VulkanInterfaceGate/1",
            "ready": True,
            "blocking_reasons": [],
        },
    )

    result = run_vulkan_bundle(tmp_path, prepare_only=True)

    assert result["format"] == "SHIFT.VulkanBundleRunner/1"
    assert result["ready"] is False
    assert result["gates"]["runtime_provenance"]["status"] == "blocked"
    assert (
        "vulkan-runner:runtime-provenance-gate-missing"
        in result["blocking_reasons"]
    )


def test_neutral_runner_prepares_when_all_neutral_gates_are_ready(
    monkeypatch,
    tmp_path,
):
    _neutral_manifest(tmp_path)

    monkeypatch.setattr(
        "vulkan_bundle_run.compile_bmw_vulkan_bundle",
        lambda root, validator=None: {
            "format": "SHIFT.VulkanBundleSPIRV/1",
            "ready": True,
            "blocking_reasons": [],
            "shader_results": [],
        },
    )
    monkeypatch.setattr(
        "vulkan_bundle_run.validate_bmw_vulkan_interface",
        lambda root, report: {
            "format": "SHIFT.VulkanInterfaceGate/1",
            "ready": True,
            "blocking_reasons": [],
        },
    )

    result = run_vulkan_bundle(tmp_path, prepare_only=True)

    assert result["format"] == "SHIFT.VulkanBundleRunner/1"
    assert result["source_bundle_format"] == "SHIFT.VulkanDrawBundle/1"
    assert result["ready"] is True
    assert result["status"] == "ready"
    assert result["gates"]["runtime_provenance"]["status"] == "ready"
