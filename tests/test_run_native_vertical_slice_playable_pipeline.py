from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


WRAPPER = _load_module(
    "run_native_vertical_slice_playable_pipeline_tested",
    ROOT / "tools" / "run_native_vertical_slice_playable_pipeline.py",
)
PARTICIPANT_FIXTURE = _load_module(
    "run_native_vertical_slice_pipeline_participant_fixture",
    ROOT / "tests" / "test_run_native_vertical_slice_pipeline_participant.py",
)


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    profile, pipeline, participant = PARTICIPANT_FIXTURE._fixture(tmp_path)
    root = profile.parent
    pipeline_run = json.loads((pipeline / "pipeline_run.json").read_text())
    source_scene = Path(pipeline_run["inputs"]["runtime_proven_scene_set"])
    source_manifest = source_scene / "bundle_set_manifest.json"

    playable_root = root / "out" / "playable-scene"
    composite = playable_root / "native-playable-scene"
    composite.mkdir(parents=True)
    composite_manifest = composite / "bundle_set_manifest.json"
    _write_json(
        composite_manifest,
        {
            "format": "SHIFT.NativeSceneVulkanSet/1",
            "ready": True,
            "source": {
                "track_scene_set": str(source_scene.resolve()),
                "track_manifest_sha256": _sha(source_manifest),
            },
        },
    )
    _write_json(
        composite / "bundle_set_prepare.json",
        {"format": "SHIFT.NativeSceneVulkanSetPrepare/1", "ready": True},
    )
    composition = composite / "playable_scene_composition.json"
    _write_json(
        composition,
        {
            "format": "SHIFT.NativePlayableSceneVulkanSet/1",
            "ready": True,
            "scene_set": {
                "path": str(composite.resolve()),
                "manifest_sha256": _sha(composite_manifest),
            },
        },
    )
    bootstrap = playable_root / "playable_scene_bootstrap.json"
    _write_json(
        bootstrap,
        {
            "format": "SHIFT.NativePlayableSceneBootstrap/1",
            "ready": True,
            "scene_set_ready": True,
            "vehicle": "BMW_M3_E36",
            "track_scene_set": str(source_scene.resolve()),
            "artifacts": {
                "scene_set_dir": str(composite.resolve()),
                "scene_composition": str(composition.resolve()),
            },
        },
    )

    profile_value = json.loads(profile.read_text())
    profile_value["playable_scene_bootstrap"] = (
        bootstrap.resolve().relative_to(root.resolve()).as_posix()
    )
    _write_json(profile, profile_value)
    return profile, pipeline, participant, composite


def test_playable_pipeline_plan_submits_only_proven_composite_scene(tmp_path):
    profile, pipeline, participant, composite = _fixture(tmp_path)
    plan = WRAPPER.build_playable_pipeline_launch_plan(profile)

    scene_index = plan["argv"].index("--scene-set")
    participant_index = plan["argv"].index("--participant-boundary")
    physics_index = plan["argv"].index("--physics-manifest")

    assert plan["argv"][scene_index + 1] == str(composite.resolve())
    assert plan["argv"][participant_index + 1] == str(participant.resolve())
    assert plan["argv"][physics_index + 1] == str(
        (pipeline / "native-handoff" / "native_physics_manifest.json").resolve()
    )
    assert plan["checks"]["resource_pipeline_playable_scene_join"]["ready"] is True
    assert plan["checks"]["scene_set"]["source"] == (
        "proven-resource-pipeline-playable-composite"
    )
    assert plan["boundary"]["scene_and_physics_from_resource_pipeline"] is False
    assert plan["boundary"]["physics_and_participant_from_resource_pipeline"] is True
    assert plan["boundary"]["resource_pipeline_source_scene_directly_submitted"] is False
    assert plan["boundary"]["playable_composite_scene_provenance_revalidated"] is True
    assert plan["boundary"]["resource_pipeline_playable_scene_join_is_runtime_execution_proof"] is False


def test_playable_pipeline_plan_rejects_composite_manifest_tamper(tmp_path):
    profile, _, _, composite = _fixture(tmp_path)
    manifest = json.loads((composite / "bundle_set_manifest.json").read_text())
    manifest["tampered"] = True
    _write_json(composite / "bundle_set_manifest.json", manifest)

    with pytest.raises(
        WRAPPER.native.ProfileError,
        match="playable composite scene manifest SHA-256 mismatch",
    ):
        WRAPPER.build_playable_pipeline_launch_plan(profile)


def test_playable_pipeline_plan_rejects_source_scene_substitution(tmp_path):
    profile, _, _, _ = _fixture(tmp_path)
    root = profile.parent
    bootstrap_path = root / json.loads(profile.read_text())["playable_scene_bootstrap"]
    bootstrap = json.loads(bootstrap_path.read_text())
    other = root / "out" / "other-scene"
    other.mkdir()
    _write_json(
        other / "bundle_set_manifest.json",
        {"format": "SHIFT.NativeSceneVulkanSet/1", "ready": True},
    )
    bootstrap["track_scene_set"] = str(other.resolve())
    _write_json(bootstrap_path, bootstrap)

    with pytest.raises(
        WRAPPER.native.ProfileError,
        match="track scene does not match resource pipeline",
    ):
        WRAPPER.build_playable_pipeline_launch_plan(profile)


def test_playable_pipeline_plan_requires_both_profile_authorities(tmp_path):
    profile, _, _, _ = _fixture(tmp_path)
    value = json.loads(profile.read_text())
    value.pop("playable_scene_bootstrap")
    _write_json(profile, value)
    with pytest.raises(
        WRAPPER.native.ProfileError,
        match="requires playable_scene_bootstrap",
    ):
        WRAPPER.build_playable_pipeline_launch_plan(profile)

    profile, _, _, _ = _fixture(tmp_path / "pipeline")
    value = json.loads(profile.read_text())
    value.pop("resource_pipeline")
    _write_json(profile, value)
    with pytest.raises(
        WRAPPER.native.ProfileError,
        match="requires resource_pipeline",
    ):
        WRAPPER.build_playable_pipeline_launch_plan(profile)
