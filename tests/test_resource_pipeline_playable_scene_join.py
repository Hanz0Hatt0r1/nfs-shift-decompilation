from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "resources" / "resource_pipeline_playable_scene_join.py"
SPEC = importlib.util.spec_from_file_location(
    "resource_pipeline_playable_scene_join_tested",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

TRACK = "Silverstone_Era3_GrandPrix"
VEHICLE = "BMW_M3_E36"


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    track_scene = workspace / "out" / "track-scene"
    track_scene.mkdir(parents=True)
    track_manifest = track_scene / "bundle_set_manifest.json"
    _write(
        track_manifest,
        {
            "format": "SHIFT.NativeSceneVulkanSet/1",
            "version": 1,
            "ready": True,
            "draws": [{"draw_order": 0}],
        },
    )

    pipeline = workspace / "out" / "offline-pipeline"
    pipeline.mkdir(parents=True)
    _write(
        pipeline / "pipeline_run.json",
        {
            "format": "SHIFT.OfflineResourcePipelineRun/1",
            "version": 1,
            "native_resource_handoff_ready": True,
            "track": TRACK,
            "vehicle": VEHICLE,
            "inputs": {
                "runtime_proven_scene_set": "out/track-scene",
            },
        },
    )

    composite = workspace / "out" / "playable-scene" / "native-playable-scene"
    composite.mkdir(parents=True)
    composite_manifest = composite / "bundle_set_manifest.json"
    _write(
        composite_manifest,
        {
            "format": "SHIFT.NativeSceneVulkanSet/1",
            "version": 1,
            "ready": True,
            "draws": [
                {"draw_order": 0, "source_group": "track"},
                {"draw_order": 1, "source_group": "vehicle"},
            ],
            "source": {
                "composition_format": "SHIFT.NativePlayableSceneVulkanSet/1",
                "track_scene_set": str(track_scene),
                "track_manifest_sha256": _sha(track_manifest),
                "vehicle": {"mesh_ref": "BMW_M3_E36"},
            },
        },
    )

    composition = workspace / "out" / "playable-scene" / "playable_scene_composition.json"
    _write(
        composition,
        {
            "format": "SHIFT.NativePlayableSceneVulkanSet/1",
            "version": 1,
            "ready": True,
            "scene_set": {
                "format": "SHIFT.NativeSceneVulkanSet/1",
                "path": str(composite),
                "manifest_sha256": _sha(composite_manifest),
                "ready": True,
            },
        },
    )

    bootstrap = workspace / "out" / "playable-scene" / "playable_scene_bootstrap.json"
    _write(
        bootstrap,
        {
            "format": "SHIFT.NativePlayableSceneBootstrap/1",
            "version": 1,
            "ready": True,
            "scene_set_ready": True,
            "vehicle": VEHICLE,
            "track_scene_set": str(track_scene),
            "artifacts": {
                "scene_set_dir": str(composite),
                "scene_composition": str(composition),
            },
        },
    )
    return workspace, pipeline, bootstrap, composite_manifest


def _join(workspace: Path, pipeline: Path, bootstrap: Path) -> dict:
    return MODULE.build_resource_pipeline_playable_scene_join(
        workspace_root=workspace,
        resource_pipeline=pipeline,
        playable_scene_bootstrap=bootstrap,
    )


def test_join_proves_pipeline_scene_to_playable_composite(tmp_path: Path):
    workspace, pipeline, bootstrap, composite_manifest = _fixture(tmp_path)

    result = _join(workspace, pipeline, bootstrap)

    assert result["format"] == "SHIFT.ResourcePipelinePlayableSceneJoin/1"
    assert result["ready"] is True
    assert result["track"] == TRACK
    assert result["vehicle"] == VEHICLE
    assert result["source_scene"] == {
        "path": "out/track-scene",
        "manifest_sha256": _sha(workspace / "out" / "track-scene" / "bundle_set_manifest.json"),
    }
    assert result["composite_scene"]["path"] == (
        "out/playable-scene/native-playable-scene"
    )
    assert result["composite_scene"]["manifest_sha256"] == _sha(composite_manifest)
    assert result["boundary"]["resource_pipeline_scene_manifest_sha256_matched"] is True
    assert result["boundary"]["playable_composition_source_scene_matched"] is True
    assert result["boundary"]["resource_pipeline_physics_or_participant_revalidated"] is False
    assert result["boundary"]["launcher_admission_performed"] is False
    assert result["boundary"]["runtime_execution_claimed"] is False


def test_join_rejects_bootstrap_track_scene_from_other_path(tmp_path: Path):
    workspace, pipeline, bootstrap, _ = _fixture(tmp_path)
    other = workspace / "out" / "other-track"
    other.mkdir()
    _write(
        other / "bundle_set_manifest.json",
        {"format": "SHIFT.NativeSceneVulkanSet/1", "ready": True},
    )
    payload = json.loads(bootstrap.read_text(encoding="utf-8"))
    payload["track_scene_set"] = str(other)
    _write(bootstrap, payload)

    with pytest.raises(
        ValueError,
        match="track scene does not match resource pipeline",
    ):
        _join(workspace, pipeline, bootstrap)


def test_join_rejects_composite_source_manifest_sha_drift(tmp_path: Path):
    workspace, pipeline, bootstrap, composite_manifest = _fixture(tmp_path)
    payload = json.loads(composite_manifest.read_text(encoding="utf-8"))
    payload["source"]["track_manifest_sha256"] = "0" * 64
    _write(composite_manifest, payload)

    composition = workspace / "out" / "playable-scene" / "playable_scene_composition.json"
    composition_payload = json.loads(composition.read_text(encoding="utf-8"))
    composition_payload["scene_set"]["manifest_sha256"] = _sha(composite_manifest)
    _write(composition, composition_payload)

    with pytest.raises(ValueError, match="source track manifest SHA-256 mismatch"):
        _join(workspace, pipeline, bootstrap)


def test_join_rejects_composite_manifest_tamper(tmp_path: Path):
    workspace, pipeline, bootstrap, composite_manifest = _fixture(tmp_path)
    payload = json.loads(composite_manifest.read_text(encoding="utf-8"))
    payload["tampered"] = True
    _write(composite_manifest, payload)

    with pytest.raises(ValueError, match="composite scene manifest SHA-256 mismatch"):
        _join(workspace, pipeline, bootstrap)


def test_join_rejects_vehicle_target_mismatch(tmp_path: Path):
    workspace, pipeline, bootstrap, _ = _fixture(tmp_path)
    payload = json.loads(bootstrap.read_text(encoding="utf-8"))
    payload["vehicle"] = "Audi_R8"
    _write(bootstrap, payload)

    with pytest.raises(ValueError, match="vehicle does not match resource pipeline target"):
        _join(workspace, pipeline, bootstrap)
