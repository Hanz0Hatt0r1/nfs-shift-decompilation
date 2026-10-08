"""Prove that a playable composite scene derives from a resource-pipeline scene.

This is a provenance join only.  It does not admit runtime execution, create
participant evidence, or replace validation in tools/run_native_vertical_slice.py.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.ResourcePipelinePlayableSceneJoin/1"
PIPELINE_FORMAT = "SHIFT.OfflineResourcePipelineRun/1"
PLAYABLE_BOOTSTRAP_FORMAT = "SHIFT.NativePlayableSceneBootstrap/1"
PLAYABLE_COMPOSITION_FORMAT = "SHIFT.NativePlayableSceneVulkanSet/1"
SCENE_SET_FORMAT = "SHIFT.NativeSceneVulkanSet/1"


def _load(path: Path, *, label: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve(root: Path, raw: Any, *, label: str, expect_dir: bool = False) -> Path:
    text = str(raw or "").strip()
    if not text:
        raise ValueError(f"{label} path is missing")
    path = Path(text)
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} escapes workspace: {text}") from exc
    if expect_dir:
        if not resolved.is_dir():
            raise ValueError(f"{label} directory not found: {resolved}")
    elif not resolved.is_file():
        raise ValueError(f"{label} file not found: {resolved}")
    return resolved


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root).as_posix()


def build_resource_pipeline_playable_scene_join(
    *,
    workspace_root: str | Path,
    resource_pipeline: str | Path,
    playable_scene_bootstrap: str | Path,
) -> dict[str, Any]:
    """Return a fail-closed provenance join for one ready composite scene."""
    root = Path(workspace_root).resolve()
    if not root.is_dir():
        raise ValueError(f"workspace_root directory not found: {root}")

    pipeline_root = _resolve(
        root,
        resource_pipeline,
        label="resource pipeline",
        expect_dir=True,
    )
    pipeline_path = pipeline_root / "pipeline_run.json"
    pipeline = _load(pipeline_path, label="resource pipeline run")
    if pipeline.get("format") != PIPELINE_FORMAT:
        raise ValueError(f"resource pipeline run must be {PIPELINE_FORMAT}")
    if pipeline.get("native_resource_handoff_ready") is not True:
        raise ValueError("resource pipeline native resource handoff is not ready")
    inputs = pipeline.get("inputs")
    if not isinstance(inputs, Mapping):
        raise ValueError("resource pipeline inputs must be an object")
    track_scene = _resolve(
        root,
        inputs.get("runtime_proven_scene_set"),
        label="resource pipeline runtime-proven scene set",
        expect_dir=True,
    )
    track_manifest = track_scene / "bundle_set_manifest.json"
    if not track_manifest.is_file():
        raise ValueError("resource pipeline scene bundle_set_manifest.json is missing")
    track_manifest_value = _load(track_manifest, label="resource pipeline scene manifest")
    if track_manifest_value.get("format") != SCENE_SET_FORMAT:
        raise ValueError(f"resource pipeline scene must be {SCENE_SET_FORMAT}")
    if track_manifest_value.get("ready") is not True:
        raise ValueError("resource pipeline scene is not ready")
    track_manifest_sha = _sha256(track_manifest)

    playable_path = _resolve(
        root,
        playable_scene_bootstrap,
        label="playable scene bootstrap",
    )
    playable = _load(playable_path, label="playable scene bootstrap")
    if playable.get("format") != PLAYABLE_BOOTSTRAP_FORMAT:
        raise ValueError(f"playable scene bootstrap must be {PLAYABLE_BOOTSTRAP_FORMAT}")
    if playable.get("ready") is not True or playable.get("scene_set_ready") is not True:
        raise ValueError("playable scene bootstrap is not ready")

    recorded_track = _resolve(
        root,
        playable.get("track_scene_set"),
        label="playable scene bootstrap track scene set",
        expect_dir=True,
    )
    if recorded_track != track_scene:
        raise ValueError("playable scene bootstrap track scene does not match resource pipeline")

    artifacts = playable.get("artifacts")
    if not isinstance(artifacts, Mapping):
        raise ValueError("playable scene bootstrap artifacts must be an object")
    composite_scene = _resolve(
        root,
        artifacts.get("scene_set_dir"),
        label="playable composite scene set",
        expect_dir=True,
    )
    composition_path = _resolve(
        root,
        artifacts.get("scene_composition"),
        label="playable scene composition",
    )
    composition = _load(composition_path, label="playable scene composition")
    if composition.get("format") != PLAYABLE_COMPOSITION_FORMAT:
        raise ValueError(f"playable scene composition must be {PLAYABLE_COMPOSITION_FORMAT}")
    if composition.get("ready") is not True:
        raise ValueError("playable scene composition is not ready")

    composition_scene = composition.get("scene_set")
    if not isinstance(composition_scene, Mapping):
        raise ValueError("playable scene composition scene_set must be an object")
    composition_scene_path = _resolve(
        root,
        composition_scene.get("path"),
        label="playable scene composition scene set",
        expect_dir=True,
    )
    if composition_scene_path != composite_scene:
        raise ValueError("playable scene composition path disagrees with bootstrap artifact")

    composite_manifest = composite_scene / "bundle_set_manifest.json"
    if not composite_manifest.is_file():
        raise ValueError("playable composite scene bundle_set_manifest.json is missing")
    composite_manifest_sha = _sha256(composite_manifest)
    recorded_composite_sha = str(composition_scene.get("manifest_sha256") or "").lower()
    if recorded_composite_sha != composite_manifest_sha:
        raise ValueError("playable composite scene manifest SHA-256 mismatch")

    composite_manifest_value = _load(
        composite_manifest,
        label="playable composite scene manifest",
    )
    if composite_manifest_value.get("format") != SCENE_SET_FORMAT:
        raise ValueError(f"playable composite scene must be {SCENE_SET_FORMAT}")
    if composite_manifest_value.get("ready") is not True:
        raise ValueError("playable composite scene is not ready")
    source = composite_manifest_value.get("source")
    if not isinstance(source, Mapping):
        raise ValueError("playable composite scene source must be an object")
    source_track = _resolve(
        root,
        source.get("track_scene_set"),
        label="playable composite source track scene set",
        expect_dir=True,
    )
    if source_track != track_scene:
        raise ValueError("playable composite source track scene does not match resource pipeline")
    source_track_sha = str(source.get("track_manifest_sha256") or "").lower()
    if source_track_sha != track_manifest_sha:
        raise ValueError("playable composite source track manifest SHA-256 mismatch")

    pipeline_track = str(pipeline.get("track") or "").strip() or None
    pipeline_vehicle = str(pipeline.get("vehicle") or "").strip() or None
    playable_vehicle = str(playable.get("vehicle") or "").strip() or None
    if pipeline_vehicle and playable_vehicle and pipeline_vehicle != playable_vehicle:
        raise ValueError("playable scene vehicle does not match resource pipeline target")

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "workspace_root": str(root),
        "resource_pipeline": _relative(root, pipeline_root),
        "playable_scene_bootstrap": _relative(root, playable_path),
        "track": pipeline_track,
        "vehicle": pipeline_vehicle or playable_vehicle,
        "source_scene": {
            "path": _relative(root, track_scene),
            "manifest_sha256": track_manifest_sha,
        },
        "composite_scene": {
            "path": _relative(root, composite_scene),
            "manifest_sha256": composite_manifest_sha,
            "composition_path": _relative(root, composition_path),
            "composition_sha256": _sha256(composition_path),
        },
        "boundary": {
            "resource_pipeline_scene_path_matched": True,
            "resource_pipeline_scene_manifest_sha256_matched": True,
            "playable_bootstrap_track_scene_matched": True,
            "playable_composition_source_scene_matched": True,
            "playable_composite_manifest_sha256_matched": True,
            "resource_pipeline_physics_or_participant_revalidated": False,
            "launcher_admission_performed": False,
            "runtime_execution_claimed": False,
        },
    }
