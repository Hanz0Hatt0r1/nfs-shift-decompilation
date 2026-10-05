from __future__ import annotations

import hashlib
import json
from pathlib import Path

import vulkan_draw_bundle_prepare as prepare


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


def _compiled() -> dict:
    return {
        "format": "SHIFT.VulkanBundleSPIRV/1",
        "bundle_format": "SHIFT.VulkanDrawBundle/1",
        "ready": True,
        "status": "ready",
        "blocking_reasons": [],
        "shader_results": [],
    }


def _interface() -> dict:
    return {
        "format": "SHIFT.VulkanInterfaceGate/1",
        "bundle_format": "SHIFT.VulkanDrawBundle/1",
        "ready": True,
        "status": "ready",
        "blocking_reasons": [],
        "descriptors": [],
    }


def _bundle(root: Path) -> None:
    geometry = root / "geometry.svpk"
    geometry.write_bytes(b"SVPK-phase660-geometry")

    shader = root / "shaders/submesh_0.vertex.glsl"
    shader.parent.mkdir(parents=True, exist_ok=True)
    shader.write_text("#version 450\nvoid main(){}\n", encoding="utf-8")

    native_gate = root / "native_submission_gate.json"
    _write_json(native_gate, {
        "format": "SHIFT.NativeSubmissionGate/1",
        "ready": True,
        "blocking_reasons": [],
    })
    provenance_gate = root / "runtime_provenance_gate.json"
    _write_json(provenance_gate, {
        "format": "SHIFT.VulkanDrawRuntimeProvenanceGate/1",
        "ready": True,
        "blocking_reasons": [],
    })

    _write_json(root / "bundle_manifest.json", {
        "format": "SHIFT.VulkanDrawBundle/1",
        "ready": True,
        "blocking_reasons": [],
        "artifacts": {
            "geometry": {
                "path": "geometry.svpk",
                "sha256": _sha(geometry),
            },
            "native_submission_gate": {
                "path": "native_submission_gate.json",
                "sha256": _sha(native_gate),
            },
            "runtime_provenance_gate": {
                "path": "runtime_provenance_gate.json",
                "sha256": _sha(provenance_gate),
            },
            "shaders": [{
                "path": "shaders/submesh_0.vertex.glsl",
                "sha256": _sha(shader),
            }],
        },
        "scene_transform": {
            "world_matrix": None,
            "packet": None,
        },
    })


def _patch_prepare(monkeypatch) -> None:
    monkeypatch.setattr(
        prepare,
        "compile_vulkan_bundle",
        lambda *a, **k: _compiled(),
    )
    monkeypatch.setattr(
        prepare,
        "validate_vulkan_bundle_interface",
        lambda *a, **k: _interface(),
    )


def test_phase660_accepts_unchanged_manifest_declared_artifacts(
    tmp_path: Path,
    monkeypatch,
):
    _bundle(tmp_path)
    _patch_prepare(monkeypatch)

    result = prepare.prepare_vulkan_draw_bundle(tmp_path)

    assert result["ready"] is True, result["blocking_reasons"]
    integrity = result["manifest_artifact_integrity"]
    assert integrity["ready"] is True
    assert integrity["verified_count"] == 4
    assert all(row["sha256_match"] is True for row in integrity["artifacts"])
    assert (
        result["boundary"]["manifest_declared_artifacts_sha256_revalidated"]
        is True
    )
    assert result["boundary"]["artifact_integrity_checked_before_compile"] is True


def test_phase660_rejects_geometry_tamper_before_compile(
    tmp_path: Path,
    monkeypatch,
):
    _bundle(tmp_path)
    (tmp_path / "geometry.svpk").write_bytes(b"tampered-geometry")
    called = False

    def compiler(*args, **kwargs):
        nonlocal called
        called = True
        return _compiled()

    monkeypatch.setattr(prepare, "compile_vulkan_bundle", compiler)

    result = prepare.prepare_vulkan_draw_bundle(tmp_path)

    assert result["ready"] is False
    assert (
        "vulkan-draw-prepare:artifact:geometry:sha256-mismatch"
        in result["blocking_reasons"]
    )
    assert result["manifest_artifact_integrity"]["ready"] is False
    assert called is False


def test_phase660_rejects_ready_gate_tamper_before_semantic_gate_use(
    tmp_path: Path,
    monkeypatch,
):
    _bundle(tmp_path)
    gate = tmp_path / "native_submission_gate.json"
    payload = json.loads(gate.read_text(encoding="utf-8"))
    payload["tampered_but_still_ready"] = True
    _write_json(gate, payload)
    _patch_prepare(monkeypatch)

    result = prepare.prepare_vulkan_draw_bundle(tmp_path)

    assert result["ready"] is False
    assert (
        "vulkan-draw-prepare:artifact:native_submission_gate:sha256-mismatch"
        in result["blocking_reasons"]
    )
    assert result["native_submission_gate_ready"] is True
    assert result["manifest_artifact_integrity"]["ready"] is False


def test_phase660_rejects_unsafe_declared_shader_path(
    tmp_path: Path,
    monkeypatch,
):
    _bundle(tmp_path)
    manifest_path = tmp_path / "bundle_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"]["shaders"][0]["path"] = "../outside.glsl"
    _write_json(manifest_path, manifest)
    _patch_prepare(monkeypatch)

    result = prepare.prepare_vulkan_draw_bundle(tmp_path)

    assert result["ready"] is False
    assert (
        "vulkan-draw-prepare:artifact:shaders[0]:path-unsafe"
        in result["blocking_reasons"]
    )
