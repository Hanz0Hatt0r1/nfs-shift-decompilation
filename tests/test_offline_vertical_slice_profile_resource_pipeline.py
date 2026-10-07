from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from offline_vertical_slice_profile import build_vertical_slice_profile_prepare


PIPELINE_INPUTS = {
    "scene_set",
    "physics_manifest",
    "participant_boundary",
}
PROFILE_INPUTS = (
    "scene_set",
    "camera_state",
    "physics_manifest",
    "participant_boundary",
    "solver_frame",
    "generated_body_constraint_frame",
    "constraint_sample_relation_frame",
    "constraint_relation_reset_frame",
    "post_solve_projection",
)


def _fixture(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    pipeline = root / "out" / "offline-pipeline"
    pipeline.mkdir(parents=True)

    paths = {
        "camera_state": root / "runtime" / "camera.json",
        "solver_frame": root / "runtime" / "solver.sbfr",
        "generated_body_constraint_frame": root / "runtime" / "generated.gbcf",
        "constraint_sample_relation_frame": root / "runtime" / "relations.csrf",
        "constraint_relation_reset_frame": root / "runtime" / "reset.crrf",
        "post_solve_projection": root / "runtime" / "post.sbps",
    }
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture")

    requirements = {
        "format": "SHIFT.OfflineNativeRuntimeRequirements/1",
        "version": 1,
        "ready": False,
        "track": "Silverstone_Era3_GrandPrix",
        "vehicle": "BMW_M3_E36",
        "requirements": [
            {
                "name": name,
                "satisfied": False,
                "artifact": None,
            }
            for name in PROFILE_INPUTS
        ],
    }
    explicit = {
        name: path.relative_to(root).as_posix()
        for name, path in paths.items()
    }
    return root, pipeline, requirements, explicit


def test_resource_pipeline_replaces_only_scene_physics_participant_profile_paths(tmp_path):
    root, pipeline, requirements, explicit = _fixture(tmp_path)

    report = build_vertical_slice_profile_prepare(
        requirements,
        workspace_root=root,
        profile_path=root / "profiles" / "vertical.json",
        explicit_inputs=explicit,
        resource_pipeline=pipeline.relative_to(root),
        keyboard=True,
        frames=120,
    )

    assert report["ready"] is True
    assert report["resource_pipeline"] == "out/offline-pipeline"
    profile = report["profile"]
    assert profile["resource_pipeline"] == "out/offline-pipeline"
    for name in PIPELINE_INPUTS:
        assert name not in profile
    assert profile["camera_state"] == "runtime/camera.json"
    assert profile["solver_frame"] == "runtime/solver.sbfr"
    assert set(report["explicit_filled_inputs"]) == set(PROFILE_INPUTS) - PIPELINE_INPUTS
    assert report["auto_filled_inputs"] == []
    boundary = report["boundary"]
    assert boundary["resource_pipeline_profile_source_requested"] is True
    assert boundary["resource_pipeline_profile_source_resolved"] is True
    assert boundary["resource_pipeline_supplies_scene_physics_participant"] is True
    assert boundary["resource_pipeline_path_presence_is_runtime_evidence"] is False
    assert boundary["resource_pipeline_deferred_to_launcher_validation"] is True
    assert boundary["camera_or_body_feedback_from_resource_pipeline"] is False
    assert boundary["launcher_validation_still_required"] is True


def test_resource_pipeline_rejects_parallel_explicit_resource_bound_inputs(tmp_path):
    root, pipeline, requirements, explicit = _fixture(tmp_path)
    explicit["participant_boundary"] = "runtime/participant.json"
    (root / "runtime" / "participant.json").write_text("{}", encoding="utf-8")

    report = build_vertical_slice_profile_prepare(
        requirements,
        workspace_root=root,
        profile_path=root / "profile.json",
        explicit_inputs=explicit,
        resource_pipeline="out/offline-pipeline",
        keyboard=True,
        frames=120,
    )

    assert report["ready"] is False
    assert report["profile"] is None
    assert (
        "participant_boundary:explicit-conflicts-with-resource-pipeline"
        in report["blocking_reasons"]
    )
    assert report["boundary"]["resource_pipeline_explicit_overlap_allowed"] is False


def test_resource_pipeline_must_be_workspace_local_existing_directory(tmp_path):
    root, _pipeline, requirements, explicit = _fixture(tmp_path)

    missing = build_vertical_slice_profile_prepare(
        requirements,
        workspace_root=root,
        profile_path=root / "missing.json",
        explicit_inputs=explicit,
        resource_pipeline="out/missing-pipeline",
        keyboard=True,
        frames=120,
    )
    assert missing["ready"] is False
    assert "resource-pipeline:directory-not-found:out/missing-pipeline" in missing[
        "blocking_reasons"
    ]

    outside = tmp_path / "outside-pipeline"
    outside.mkdir()
    escaped = build_vertical_slice_profile_prepare(
        requirements,
        workspace_root=root,
        profile_path=root / "escaped.json",
        explicit_inputs=explicit,
        resource_pipeline="../outside-pipeline",
        keyboard=True,
        frames=120,
    )
    assert escaped["ready"] is False
    assert any(
        reason.startswith("resource-pipeline:path-escapes-workspace:")
        for reason in escaped["blocking_reasons"]
    )


def test_prepare_cli_emits_resource_pipeline_profile_without_duplicate_paths(tmp_path):
    root, pipeline, requirements, explicit = _fixture(tmp_path)
    requirements_path = root / "runtime_requirements.json"
    requirements_path.write_text(json.dumps(requirements), encoding="utf-8")
    profile_path = root / "profiles" / "vertical.json"

    repo = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "prepare_native_vertical_slice_profile_resource_pipeline_cli",
        repo / "tools" / "prepare_native_vertical_slice_profile.py",
    )
    assert spec is not None and spec.loader is not None
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    argv = [
        str(requirements_path),
        "--workspace-root",
        str(root),
        "-o",
        str(profile_path),
        "--resource-pipeline",
        str(pipeline.relative_to(root)),
        "--keyboard",
        "--frames",
        "120",
    ]
    flag_by_name = {
        "camera_state": "--camera-state",
        "solver_frame": "--solver-frame",
        "generated_body_constraint_frame": "--generated-body-constraint-frame",
        "constraint_sample_relation_frame": "--constraint-sample-relation-frame",
        "constraint_relation_reset_frame": "--constraint-relation-reset-frame",
        "post_solve_projection": "--post-solve-projection",
    }
    for name, flag in flag_by_name.items():
        argv.extend([flag, explicit[name]])

    assert cli.main(argv) == 0
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    assert profile["resource_pipeline"] == "out/offline-pipeline"
    for name in PIPELINE_INPUTS:
        assert name not in profile
    report = json.loads(
        profile_path.with_suffix(profile_path.suffix + ".prepare.json").read_text(
            encoding="utf-8"
        )
    )
    assert report["profile_ready"] is True
    assert report["resource_pipeline"] == "out/offline-pipeline"
