import importlib.util
import json
import struct
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "run_native_vertical_slice.py"
SPEC = importlib.util.spec_from_file_location("run_native_vertical_slice", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")


def _write_packet(path: Path, magic: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(magic + struct.pack("<I", 1) + b"fixture")


def _fixture(
    tmp_path: Path,
    *,
    with_script: bool = False,
    interactive: bool = False,
) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()

    runtime = root / "native_runtime" / "build" / "shift_runtime"
    runtime.parent.mkdir(parents=True)
    runtime.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    runtime.chmod(0o755)

    scene = root / "out" / "scene"
    scene.mkdir(parents=True)
    _write_json(
        scene / "bundle_set_manifest.json",
        {"format": "SHIFT.NativeSceneVulkanSet/1"},
    )
    _write_json(
        scene / "bundle_set_prepare.json",
        {"format": "SHIFT.NativeSceneVulkanSetPrepare/1", "ready": True},
    )

    _write_json(
        root / "out" / "camera.json",
        {"format": "SHIFT.NativeCameraStateBridge/1", "ready": True},
    )
    _write_json(
        root / "evidence" / "physics.json",
        {"format": "SHIFT.BMWM3VehiclePhysicsResourceManifest/1"},
    )
    _write_json(
        root / "out" / "participant.json",
        {
            "format": "SHIFT.NativePhysicsParticipantRuntimeEvidence/1",
            "ready": True,
            "registry_selector_identity_join_proven": True,
            "participant_instance_ready": True,
        },
    )

    packets = {
        "solver.sbfr": b"SBFR",
        "generated.gbcf": b"GBCF",
        "relations.csrf": b"CSRF",
        "reset.crrf": b"CRRF",
        "post.sbps": b"SBPS",
    }
    for name, magic in packets.items():
        _write_packet(root / "out" / name, magic)

    profile = {
        "format": "SHIFT.NativeVerticalSliceProfile/1",
        "version": 1,
        "workspace_root": ".",
        "scene_set": "out/scene",
        "camera_state": "out/camera.json",
        "physics_manifest": "evidence/physics.json",
        "participant_boundary": "out/participant.json",
        "solver_frame": "out/solver.sbfr",
        "generated_body_constraint_frame": "out/generated.gbcf",
        "constraint_sample_relation_frame": "out/relations.csrf",
        "constraint_relation_reset_frame": "out/reset.crrf",
        "post_solve_projection": "out/post.sbps",
        "persist_post_solve_body_state": True,
    }
    if interactive:
        profile["interactive"] = True
    else:
        profile["frames"] = 3 if with_script else 120

    if with_script:
        script = root / "out" / "input.script"
        script.write_text(
            "SHIFT.NativeRuntimeInputScript/1\n"
            "0 1 0 0 0\n"
            "1 1 0 0 1\n"
            "2 0 1 1 0\n",
            encoding="utf-8",
        )
        profile["input_script"] = "out/input.script"

    profile_path = root / "vertical_slice.json"
    _write_json(profile_path, profile)
    return profile_path


def test_build_launch_plan_composes_full_native_chain(tmp_path):
    profile = _fixture(tmp_path)
    plan = MODULE.build_launch_plan(profile, validation=True)

    assert plan["format"] == "SHIFT.NativeVerticalSliceLaunchPlan/1"
    assert plan["ready"] is True
    assert plan["resource_pipeline"] is None
    assert plan["mode"] == "keyboard"
    assert plan["interactive"] is False
    assert plan["frames"] == 120
    assert plan["frame_limit_policy"] == "explicit-bounded-frame-count"
    assert "--scene-set" in plan["argv"]
    assert "--camera-state" in plan["argv"]
    assert "--physics-manifest" in plan["argv"]
    assert "--participant-boundary" in plan["argv"]
    assert "--solver-frame" not in plan["argv"]
    assert "--generated-body-constraint-frame" not in plan["argv"]
    assert "--constraint-sample-relation-frame" not in plan["argv"]
    assert "--constraint-relation-reset-frame" not in plan["argv"]
    assert "--post-solve-projection" not in plan["argv"]
    assert "--persist-post-solve-body-state" not in plan["argv"]
    assert "--validation" in plan["argv"]
    assert plan["checks"]["solver_frame"]["magic"] == "SBFR"
    assert plan["checks"]["generated_body_constraint_frame"]["magic"] == "GBCF"
    assert plan["environment"]["SHIFT_NATIVE_BODY_FEEDBACK"] == "1"
    assert plan["environment"]["SHIFT_NATIVE_BODY_FEEDBACK_SOLVER_FRAME"].endswith(
        "out/solver.sbfr"
    )
    assert plan["environment"]["SHIFT_NATIVE_BODY_FEEDBACK_GBCF"].endswith(
        "out/generated.gbcf"
    )
    assert plan["boundary"]["dynamic_body_feedback_scheduler_admitted"] is True
    assert plan["boundary"]["legacy_solver_replay_cli_disabled"] is True
    assert plan["boundary"]["scene_and_physics_from_resource_pipeline"] is False
    assert plan["boundary"]["resource_pipeline_replaces_runtime_evidence"] is False
    assert plan["boundary"]["window_quit_drives_session_end"] is False
    assert plan["boundary"]["native_continuous_runtime_loop_admitted"] is False
    assert plan["boundary"]["persistent_vehicle_transform_motion_claimed"] is False
    assert plan["boundary"]["provider_present_dispatch_claimed"] is False
    assert plan["boundary"]["retail_game_loop_claimed"] is False


def test_input_script_controls_frame_count_and_mode(tmp_path):
    profile = _fixture(tmp_path, with_script=True)
    plan = MODULE.build_launch_plan(profile)

    assert plan["mode"] == "script"
    assert plan["interactive"] is False
    assert plan["frames"] == 3
    assert plan["checks"]["input_script"]["steps"] == 3
    index = plan["argv"].index("--input-script")
    assert plan["argv"][index + 1].endswith("out/input.script")


def test_interactive_keyboard_uses_window_quit_session(tmp_path):
    profile = _fixture(tmp_path, interactive=True)
    plan = MODULE.build_launch_plan(profile)

    assert plan["mode"] == "interactive-keyboard"
    assert plan["interactive"] is True
    assert plan["frames"] is None
    assert plan["frame_limit_policy"] == "native-continuous-until-window-quit"
    assert plan["boundary"]["window_quit_drives_session_end"] is True
    assert plan["boundary"]["native_continuous_runtime_loop_admitted"] is True
    assert "--continuous" in plan["argv"]
    assert "--frames" not in plan["argv"]


def test_interactive_mode_rejects_input_script(tmp_path):
    profile = _fixture(tmp_path, with_script=True)
    value = json.loads(profile.read_text(encoding="utf-8"))
    value["interactive"] = True
    value.pop("frames")
    _write_json(profile, value)

    with pytest.raises(MODULE.ProfileError, match="cannot be combined"):
        MODULE.build_launch_plan(profile)


def test_interactive_mode_rejects_explicit_frames(tmp_path):
    profile = _fixture(tmp_path)
    value = json.loads(profile.read_text(encoding="utf-8"))
    value["interactive"] = True
    _write_json(profile, value)

    with pytest.raises(MODULE.ProfileError, match="must not specify frames"):
        MODULE.build_launch_plan(profile)


def test_rejects_unproven_participant_identity(tmp_path):
    profile = _fixture(tmp_path)
    participant_path = profile.parent / "out" / "participant.json"
    participant = json.loads(participant_path.read_text(encoding="utf-8"))
    participant["registry_selector_identity_join_proven"] = False
    _write_json(participant_path, participant)

    with pytest.raises(MODULE.ProfileError, match="identity join"):
        MODULE.build_launch_plan(profile)


def test_rejects_packet_magic_mismatch(tmp_path):
    profile = _fixture(tmp_path)
    (profile.parent / "out" / "relations.csrf").write_bytes(
        b"NOPE" + struct.pack("<I", 1) + b"fixture"
    )

    with pytest.raises(MODULE.ProfileError, match="magic CSRF"):
        MODULE.build_launch_plan(profile)


def test_rejects_profile_path_escape(tmp_path):
    profile = _fixture(tmp_path)
    value = json.loads(profile.read_text(encoding="utf-8"))
    value["camera_state"] = "../camera.json"
    _write_json(profile, value)

    with pytest.raises(MODULE.ProfileError, match="escapes workspace_root"):
        MODULE.build_launch_plan(profile)


def test_launch_injects_scheduler_environment(tmp_path, monkeypatch):
    profile = _fixture(tmp_path)
    observed = {}

    class Completed:
        returncode = 0

    def capture_run(argv, *, env, check):
        observed["argv"] = argv
        observed["env"] = env
        observed["check"] = check
        return Completed()

    monkeypatch.setattr(MODULE.subprocess, "run", capture_run)
    result = MODULE.main([str(profile)])

    assert result == 0
    assert observed["check"] is False
    assert observed["env"]["SHIFT_NATIVE_BODY_FEEDBACK"] == "1"
    assert observed["env"]["SHIFT_NATIVE_BODY_FEEDBACK_SBPS"].endswith("out/post.sbps")
    assert "--solver-frame" not in observed["argv"]


def test_dry_run_writes_plan_without_launching(tmp_path, monkeypatch, capsys):
    profile = _fixture(tmp_path)
    output = tmp_path / "plan.json"

    def fail_run(*args, **kwargs):
        raise AssertionError("subprocess.run must not execute in --dry-run mode")

    monkeypatch.setattr(MODULE.subprocess, "run", fail_run)
    result = MODULE.main(
        [str(profile), "--dry-run", "--json-out", str(output)]
    )

    assert result == 0
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved["ready"] is True
    assert saved["environment"]["SHIFT_NATIVE_BODY_FEEDBACK"] == "1"
    printed = json.loads(capsys.readouterr().out)
    assert printed["format"] == "SHIFT.NativeVerticalSliceLaunchPlan/1"
