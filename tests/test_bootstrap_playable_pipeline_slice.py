from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "bootstrap_playable_pipeline_slice_tested",
    ROOT / "tools" / "bootstrap_playable_pipeline_slice.py",
)
assert SPEC is not None and SPEC.loader is not None
CLI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLI)


def _argv(tmp_path: Path) -> list[str]:
    return [
        "Vehicles.zip",
        "Silverstone.zip",
        "-o",
        str(tmp_path / "out"),
        "--track",
        "Silverstone_Era3_GrandPrix",
        "--vehicle",
        "BMW_M3_E36",
        "--workspace-root",
        str(tmp_path),
        "--resource-pipeline",
        "out/offline-pipeline",
        "--camera-state",
        "runtime/camera.json",
        "--solver-frame",
        "runtime/solver.sbfr",
        "--generated-body-constraint-frame",
        "runtime/generated.gbcf",
        "--constraint-sample-relation-frame",
        "runtime/relations.csrf",
        "--constraint-relation-reset-frame",
        "runtime/reset.crrf",
        "--post-solve-projection",
        "runtime/post.sbps",
        "--keyboard",
        "--frames",
        "120",
    ]


def _requirements() -> dict:
    return {
        "format": "SHIFT.OfflineNativeRuntimeRequirements/1",
        "version": 1,
        "requirements": [],
    }


def _ready_provenance(**kwargs) -> dict:
    return {
        "format": "SHIFT.ResourcePipelinePlayableSceneJoin/1",
        "version": 1,
        "ready": True,
        "source_scene": {"path": "out/pipeline-scene"},
        "composite_scene": {"path": "out/playable-scene/scene"},
    }


def test_cli_composes_pipeline_scene_into_playable_profile_and_launch_plan(
    monkeypatch,
    tmp_path,
):
    source_scene = tmp_path / "out" / "pipeline-scene"
    source_scene.mkdir(parents=True)
    participant = tmp_path / "out" / "participant.json"
    participant.parent.mkdir(parents=True, exist_ok=True)
    participant.write_text("{}", encoding="utf-8")
    calls = {}

    def fake_resolve(workspace, pipeline, **kwargs):
        calls["resolve"] = (Path(workspace), pipeline, kwargs)
        return (
            {
                "scene_set": source_scene,
                "participant_boundary": participant,
                "physics_manifest": tmp_path / "out" / "physics.json",
                "resource_pipeline": tmp_path / "out" / "offline-pipeline",
            },
            {"ready": True, "format": "SHIFT.OfflineResourcePipelineRun/1"},
        )

    def fake_offline(*args, **kwargs):
        calls["offline"] = kwargs
        return {
            "offline_bootstrap_ready": True,
            "blocking_reasons": [],
            "stages": {"runtime_requirements": _requirements()},
        }

    def fake_playable(inputs, track_scene_set, output_dir, **kwargs):
        calls["playable"] = (list(inputs), Path(track_scene_set), Path(output_dir), kwargs)
        path = Path(output_dir) / "playable_scene_bootstrap.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
        return {"format": "SHIFT.NativePlayableSceneBootstrap/1", "ready": True}

    def fake_provenance(**kwargs):
        calls["provenance"] = kwargs
        return _ready_provenance(**kwargs)

    def fake_profile(requirements, **kwargs):
        calls["profile"] = kwargs
        return {
            "ready": True,
            "blocking_reasons": [],
            "profile": {
                "format": "SHIFT.NativeVerticalSliceProfile/1",
                "version": 1,
                "workspace_root": ".",
                "resource_pipeline": "out/offline-pipeline",
                "playable_scene_bootstrap": "out/playable-scene/playable_scene_bootstrap.json",
            },
        }

    def fake_launch(profile_path, **kwargs):
        calls["launch"] = (Path(profile_path), kwargs)
        return {"format": "SHIFT.NativeVerticalSliceLaunchPlan/1", "ready": True}

    monkeypatch.setattr(CLI.native, "_resolve_resource_pipeline_inputs", fake_resolve)
    monkeypatch.setattr(CLI, "build_offline_vertical_slice_bootstrap", fake_offline)
    monkeypatch.setattr(CLI, "load_bmw_vehicle_render_model_resource_join", lambda path: {"ready": True})
    monkeypatch.setattr(CLI, "build_native_playable_scene_bootstrap", fake_playable)
    monkeypatch.setattr(CLI, "build_resource_pipeline_playable_scene_join", fake_provenance)
    monkeypatch.setattr(CLI, "build_playable_pipeline_profile_prepare", fake_profile)
    monkeypatch.setattr(CLI, "build_playable_pipeline_launch_plan", fake_launch)

    assert CLI.main(_argv(tmp_path) + ["--validate-launch-plan"]) == 0
    assert calls["playable"][1] == source_scene
    assert calls["offline"]["resource_pipeline"] == "out/offline-pipeline"
    assert calls["provenance"]["workspace_root"] == tmp_path.resolve()
    assert calls["provenance"]["resource_pipeline"] == "out/offline-pipeline"
    assert Path(calls["provenance"]["playable_scene_bootstrap"]).name == (
        "playable_scene_bootstrap.json"
    )
    assert calls["profile"]["resource_pipeline"] == "out/offline-pipeline"
    assert Path(calls["profile"]["playable_scene_bootstrap"]).name == (
        "playable_scene_bootstrap.json"
    )
    assert calls["launch"][0] == tmp_path / "out" / "vertical_slice_profile.json"

    report = json.loads(
        (tmp_path / "out" / "playable_pipeline_bootstrap.json").read_text()
    )
    assert report["ready"] is True
    assert report["profile_ready"] is True
    assert report["playable_scene_provenance_ready"] is True
    assert report["launch_plan_ready"] is True
    assert report["boundary"]["playable_scene_provenance_required_before_profile"] is True
    assert report["boundary"]["playable_scene_provenance_revalidated_before_profile"] is True
    assert report["boundary"]["resource_pipeline_physics_or_participant_replaced"] is False
    assert report["boundary"]["runtime_execution_claimed"] is False


def test_cli_requires_pipeline_participant_before_playable_composition(monkeypatch, tmp_path):
    source_scene = tmp_path / "out" / "pipeline-scene"
    source_scene.mkdir(parents=True)
    monkeypatch.setattr(
        CLI.native,
        "_resolve_resource_pipeline_inputs",
        lambda *args, **kwargs: (
            {
                "scene_set": source_scene,
                "physics_manifest": tmp_path / "out" / "physics.json",
                "resource_pipeline": tmp_path / "out" / "offline-pipeline",
            },
            {"ready": True},
        ),
    )

    def unexpected(*args, **kwargs):
        raise AssertionError("playable composition must not run without participant evidence")

    monkeypatch.setattr(CLI, "build_offline_vertical_slice_bootstrap", unexpected)
    monkeypatch.setattr(CLI, "build_native_playable_scene_bootstrap", unexpected)
    monkeypatch.setattr(CLI, "build_resource_pipeline_playable_scene_join", unexpected)

    assert CLI.main(_argv(tmp_path)) == 2
    report = json.loads(
        (tmp_path / "out" / "playable_pipeline_bootstrap.json").read_text()
    )
    assert report["ready"] is False
    assert report["playable_scene_provenance_ready"] is False
    assert "resource-pipeline:participant-runtime-evidence-required" in report[
        "blocking_reasons"
    ]


def test_cli_provenance_failure_blocks_profile_without_launch_plan(monkeypatch, tmp_path):
    source_scene = tmp_path / "out" / "pipeline-scene"
    source_scene.mkdir(parents=True)
    participant = tmp_path / "out" / "participant.json"
    participant.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        CLI.native,
        "_resolve_resource_pipeline_inputs",
        lambda *args, **kwargs: (
            {
                "scene_set": source_scene,
                "participant_boundary": participant,
                "physics_manifest": tmp_path / "out" / "physics.json",
                "resource_pipeline": tmp_path / "out" / "offline-pipeline",
            },
            {"ready": True},
        ),
    )
    monkeypatch.setattr(
        CLI,
        "build_offline_vertical_slice_bootstrap",
        lambda *args, **kwargs: {
            "offline_bootstrap_ready": True,
            "blocking_reasons": [],
            "stages": {"runtime_requirements": _requirements()},
        },
    )
    monkeypatch.setattr(CLI, "load_bmw_vehicle_render_model_resource_join", lambda path: {"ready": True})

    def fake_playable(inputs, scene, output, **kwargs):
        path = Path(output) / "playable_scene_bootstrap.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
        return {"ready": True}

    monkeypatch.setattr(CLI, "build_native_playable_scene_bootstrap", fake_playable)

    def fail_provenance(**kwargs):
        raise ValueError("composite manifest SHA mismatch")

    monkeypatch.setattr(CLI, "build_resource_pipeline_playable_scene_join", fail_provenance)

    def unexpected_profile(*args, **kwargs):
        raise AssertionError("profile must not be prepared before provenance is ready")

    monkeypatch.setattr(CLI, "build_playable_pipeline_profile_prepare", unexpected_profile)

    assert CLI.main(_argv(tmp_path)) == 2
    report = json.loads(
        (tmp_path / "out" / "playable_pipeline_bootstrap.json").read_text()
    )
    assert report["ready"] is False
    assert report["profile_ready"] is False
    assert report["playable_scene_provenance_ready"] is False
    assert any("composite manifest SHA mismatch" in row for row in report["blocking_reasons"])


def test_cli_launch_plan_failure_remains_fail_closed(monkeypatch, tmp_path):
    source_scene = tmp_path / "out" / "pipeline-scene"
    source_scene.mkdir(parents=True)
    participant = tmp_path / "out" / "participant.json"
    participant.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        CLI.native,
        "_resolve_resource_pipeline_inputs",
        lambda *args, **kwargs: (
            {
                "scene_set": source_scene,
                "participant_boundary": participant,
                "physics_manifest": tmp_path / "out" / "physics.json",
                "resource_pipeline": tmp_path / "out" / "offline-pipeline",
            },
            {"ready": True},
        ),
    )
    monkeypatch.setattr(
        CLI,
        "build_offline_vertical_slice_bootstrap",
        lambda *args, **kwargs: {
            "offline_bootstrap_ready": True,
            "blocking_reasons": [],
            "stages": {"runtime_requirements": _requirements()},
        },
    )
    monkeypatch.setattr(CLI, "load_bmw_vehicle_render_model_resource_join", lambda path: {"ready": True})

    def fake_playable(inputs, scene, output, **kwargs):
        path = Path(output) / "playable_scene_bootstrap.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
        return {"ready": True}

    monkeypatch.setattr(CLI, "build_native_playable_scene_bootstrap", fake_playable)
    monkeypatch.setattr(CLI, "build_resource_pipeline_playable_scene_join", _ready_provenance)
    monkeypatch.setattr(
        CLI,
        "build_playable_pipeline_profile_prepare",
        lambda *args, **kwargs: {
            "ready": True,
            "blocking_reasons": [],
            "profile": {
                "format": "SHIFT.NativeVerticalSliceProfile/1",
                "version": 1,
            },
        },
    )

    def fail_launch(*args, **kwargs):
        raise CLI.native.ProfileError("composite provenance mismatch")

    monkeypatch.setattr(CLI, "build_playable_pipeline_launch_plan", fail_launch)

    assert CLI.main(_argv(tmp_path) + ["--validate-launch-plan"]) == 2
    report = json.loads(
        (tmp_path / "out" / "playable_pipeline_bootstrap.json").read_text()
    )
    assert report["ready"] is False
    assert report["profile_ready"] is True
    assert report["playable_scene_provenance_ready"] is True
    assert report["launch_plan_ready"] is False
    assert any("composite provenance mismatch" in row for row in report["blocking_reasons"])
