from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from offline_playable_pipeline_profile import build_playable_pipeline_profile_prepare


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_SPEC = importlib.util.spec_from_file_location(
    "offline_vertical_slice_profile_resource_pipeline_fixture",
    ROOT / "tests" / "test_offline_vertical_slice_profile_resource_pipeline.py",
)
assert FIXTURE_SPEC is not None and FIXTURE_SPEC.loader is not None
FIXTURE = importlib.util.module_from_spec(FIXTURE_SPEC)
FIXTURE_SPEC.loader.exec_module(FIXTURE)


def test_playable_pipeline_profile_adds_only_workspace_local_bootstrap_path(tmp_path):
    root, pipeline, requirements, explicit = FIXTURE._fixture(tmp_path)
    playable = root / "out" / "playable-scene" / "playable_scene_bootstrap.json"
    playable.parent.mkdir(parents=True)
    playable.write_text(json.dumps({"placeholder": True}), encoding="utf-8")

    report = build_playable_pipeline_profile_prepare(
        requirements,
        workspace_root=root,
        profile_path=root / "profiles" / "vertical.json",
        explicit_inputs=explicit,
        resource_pipeline=pipeline.relative_to(root),
        playable_scene_bootstrap=playable.relative_to(root),
        keyboard=True,
        frames=120,
    )

    assert report["ready"] is True
    profile = report["profile"]
    assert profile["resource_pipeline"] == "out/offline-pipeline"
    assert profile["playable_scene_bootstrap"] == (
        "out/playable-scene/playable_scene_bootstrap.json"
    )
    for name in FIXTURE.PIPELINE_INPUTS:
        assert name not in profile
    assert report["boundary"]["playable_scene_bootstrap_path_presence_is_provenance"] is False
    assert report["boundary"]["playable_scene_provenance_validation_deferred_to_launcher"] is True


def test_playable_pipeline_profile_rejects_missing_or_escaped_bootstrap(tmp_path):
    root, pipeline, requirements, explicit = FIXTURE._fixture(tmp_path)

    missing = build_playable_pipeline_profile_prepare(
        requirements,
        workspace_root=root,
        profile_path=root / "profile.json",
        explicit_inputs=explicit,
        resource_pipeline=pipeline.relative_to(root),
        playable_scene_bootstrap="out/missing.json",
        keyboard=True,
        frames=120,
    )
    assert missing["ready"] is False
    assert "playable-scene-bootstrap:file-not-found:out/missing.json" in missing[
        "blocking_reasons"
    ]

    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    escaped = build_playable_pipeline_profile_prepare(
        requirements,
        workspace_root=root,
        profile_path=root / "profile.json",
        explicit_inputs=explicit,
        resource_pipeline=pipeline.relative_to(root),
        playable_scene_bootstrap="../outside.json",
        keyboard=True,
        frames=120,
    )
    assert escaped["ready"] is False
    assert any(
        reason.startswith("playable-scene-bootstrap:path-escapes-workspace:")
        for reason in escaped["blocking_reasons"]
    )


def test_playable_pipeline_profile_requires_resource_pipeline(tmp_path):
    root, _pipeline, requirements, explicit = FIXTURE._fixture(tmp_path)
    playable = root / "out" / "playable-scene" / "playable_scene_bootstrap.json"
    playable.parent.mkdir(parents=True)
    playable.write_text("{}", encoding="utf-8")

    report = build_playable_pipeline_profile_prepare(
        requirements,
        workspace_root=root,
        profile_path=root / "profile.json",
        explicit_inputs=explicit,
        resource_pipeline="",
        playable_scene_bootstrap=playable.relative_to(root),
        keyboard=True,
        frames=120,
    )

    assert report["ready"] is False
    assert "playable-pipeline-profile:resource-pipeline-required" in report[
        "blocking_reasons"
    ]
    assert report["profile"] is None
