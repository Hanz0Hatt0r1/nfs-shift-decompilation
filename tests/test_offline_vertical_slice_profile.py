from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from offline_vertical_slice_profile import (
    FORMAT,
    PROFILE_FORMAT,
    build_vertical_slice_profile_prepare,
)


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
    scene = root / "runtime" / "scene"
    scene.mkdir(parents=True)
    paths = {
        "scene_set": scene,
        "camera_state": root / "runtime" / "camera.json",
        "physics_manifest": root / "bootstrap" / "native_physics_manifest.json",
        "participant_boundary": root / "bootstrap" / "participant_runtime.json",
        "solver_frame": root / "runtime" / "solver.sbfr",
        "generated_body_constraint_frame": root / "runtime" / "generated.gbcf",
        "constraint_sample_relation_frame": root / "runtime" / "relations.csrf",
        "constraint_relation_reset_frame": root / "runtime" / "reset.crrf",
        "post_solve_projection": root / "runtime" / "post.sbps",
    }
    for name, path in paths.items():
        if name != "scene_set":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"fixture")

    rows = []
    for name in PROFILE_INPUTS:
        satisfied = name in {"physics_manifest", "participant_boundary"}
        rows.append({
            "name": name,
            "satisfied": satisfied,
            "artifact": (
                paths[name].relative_to(root).as_posix() if satisfied else None
            ),
        })
    rows.append({
        "name": "input_binding",
        "satisfied": False,
        "artifact": None,
    })
    requirements = {
        "format": "SHIFT.OfflineNativeRuntimeRequirements/1",
        "version": 1,
        "ready": False,
        "track": "Silverstone_Era3_GrandPrix",
        "vehicle": "BMW_M3_E36",
        "requirements": rows,
    }
    explicit = {
        name: paths[name].relative_to(root).as_posix()
        for name in PROFILE_INPUTS
        if name not in {"physics_manifest", "participant_boundary"}
    }
    return root, paths, requirements, explicit


def test_prepare_autofills_only_proven_artifacts(tmp_path):
    root, paths, requirements, explicit = _fixture(tmp_path)
    profile_path = root / "profiles" / "vertical_slice.json"

    report = build_vertical_slice_profile_prepare(
        requirements,
        workspace_root=root,
        profile_path=profile_path,
        explicit_inputs=explicit,
        keyboard=True,
        frames=120,
    )

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["auto_filled_inputs"] == [
        "physics_manifest",
        "participant_boundary",
    ]
    assert set(report["explicit_filled_inputs"]) == set(PROFILE_INPUTS) - {
        "physics_manifest",
        "participant_boundary",
    }
    profile = report["profile"]
    assert profile["format"] == PROFILE_FORMAT
    assert profile["workspace_root"] == ".."
    assert profile["physics_manifest"] == "bootstrap/native_physics_manifest.json"
    assert profile["participant_boundary"] == "bootstrap/participant_runtime.json"
    assert profile["scene_set"] == "runtime/scene"
    assert profile["frames"] == 120
    assert profile["persist_post_solve_body_state"] is True
    assert "interactive" not in profile
    assert "input_script" not in profile
    assert report["boundary"]["launcher_validation_performed"] is False


def test_missing_runtime_scene_requires_explicit_path(tmp_path):
    root, paths, requirements, explicit = _fixture(tmp_path)
    explicit.pop("scene_set")

    report = build_vertical_slice_profile_prepare(
        requirements,
        workspace_root=root,
        profile_path=root / "profile.json",
        explicit_inputs=explicit,
        keyboard=True,
        frames=120,
    )

    assert report["ready"] is False
    assert report["profile"] is None
    assert "scene_set:explicit-input-required" in report["blocking_reasons"]
    assert report["boundary"]["static_scene_promoted_to_runtime_scene"] is False


def test_explicit_override_cannot_replace_proven_physics_artifact(tmp_path):
    root, paths, requirements, explicit = _fixture(tmp_path)
    other = root / "runtime" / "other-physics.json"
    other.write_text("{}", encoding="utf-8")
    explicit["physics_manifest"] = other.relative_to(root).as_posix()

    report = build_vertical_slice_profile_prepare(
        requirements,
        workspace_root=root,
        profile_path=root / "profile.json",
        explicit_inputs=explicit,
        keyboard=True,
        frames=120,
    )

    assert report["ready"] is False
    assert (
        "physics_manifest:explicit-conflicts-with-proven-artifact"
        in report["blocking_reasons"]
    )
    assert report["boundary"]["explicit_override_of_proven_artifact_allowed"] is False


def test_path_escape_and_implicit_input_mode_fail_closed(tmp_path):
    root, paths, requirements, explicit = _fixture(tmp_path)
    outside = tmp_path / "outside-camera.json"
    outside.write_text("{}", encoding="utf-8")
    explicit["camera_state"] = "../outside-camera.json"

    report = build_vertical_slice_profile_prepare(
        requirements,
        workspace_root=root,
        profile_path=root / "profile.json",
        explicit_inputs=explicit,
    )

    assert report["ready"] is False
    assert any("camera_state:path-escapes-workspace" in item for item in report["blocking_reasons"])
    assert (
        "input-mode:choose-exactly-one-of-script-interactive-keyboard"
        in report["blocking_reasons"]
    )
    assert report["boundary"]["path_outside_workspace_allowed"] is False
    assert report["boundary"]["input_mode_invented"] is False


def test_script_mode_uses_explicit_script_without_guessing_frames(tmp_path):
    root, paths, requirements, explicit = _fixture(tmp_path)
    script = root / "runtime" / "input.script"
    script.write_text("SHIFT.NativeRuntimeInputScript/1\n0 1 0 0 0\n", encoding="utf-8")

    report = build_vertical_slice_profile_prepare(
        requirements,
        workspace_root=root,
        profile_path=root / "profiles" / "profile.json",
        explicit_inputs=explicit,
        input_script="runtime/input.script",
    )

    assert report["ready"] is True
    assert report["profile"]["input_script"] == "runtime/input.script"
    assert "frames" not in report["profile"]


def test_cli_removes_stale_profile_when_prepare_is_blocked(tmp_path):
    root, paths, requirements, explicit = _fixture(tmp_path)
    requirements_path = root / "runtime_requirements.json"
    requirements_path.write_text(json.dumps(requirements), encoding="utf-8")
    profile_path = root / "profiles" / "vertical_slice.json"
    profile_path.parent.mkdir(parents=True)
    profile_path.write_text('{"stale": true}\n', encoding="utf-8")

    repo = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "prepare_native_vertical_slice_profile_cli",
        repo / "tools" / "prepare_native_vertical_slice_profile.py",
    )
    assert spec is not None and spec.loader is not None
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    rc = cli.main([
        str(requirements_path),
        "--workspace-root",
        str(root),
        "-o",
        str(profile_path),
        "--keyboard",
        "--frames",
        "120",
    ])

    assert rc == 2
    assert not profile_path.exists()
    prepare_path = profile_path.with_suffix(profile_path.suffix + ".prepare.json")
    prepare = json.loads(prepare_path.read_text(encoding="utf-8"))
    assert prepare["ready"] is False
    assert "scene_set:explicit-input-required" in prepare["blocking_reasons"]
