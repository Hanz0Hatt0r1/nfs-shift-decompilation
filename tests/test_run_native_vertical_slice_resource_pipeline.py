from __future__ import annotations

import hashlib
import importlib.util
import json
import struct
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "run_native_vertical_slice.py"
SPEC = importlib.util.spec_from_file_location(
    "run_native_vertical_slice_resource_pipeline",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_packet(path: Path, magic: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(magic + struct.pack("<I", 1) + b"fixture")


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "workspace"
    root.mkdir()

    runtime = root / "native_runtime" / "build" / "shift_runtime"
    runtime.parent.mkdir(parents=True)
    runtime.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    runtime.chmod(0o755)

    scene = root / "out" / "native-scene-vulkan"
    scene.mkdir(parents=True)
    _write_json(
        scene / "bundle_set_manifest.json",
        {"format": "SHIFT.NativeSceneVulkanSet/1", "ready": True},
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
        root / "out" / "participant.json",
        {
            "format": "SHIFT.NativePhysicsParticipantRuntimeEvidence/1",
            "ready": True,
            "registry_selector_identity_join_proven": True,
            "participant_instance_ready": True,
        },
    )

    for name, magic in {
        "solver.sbfr": b"SBFR",
        "generated.gbcf": b"GBCF",
        "relations.csrf": b"CSRF",
        "reset.crrf": b"CRRF",
        "post.sbps": b"SBPS",
    }.items():
        _write_packet(root / "out" / name, magic)

    pipeline = root / "out" / "offline-pipeline"
    handoff_dir = pipeline / "native-handoff"
    physics = handoff_dir / "native_physics_manifest.json"
    _write_json(
        physics,
        {
            "format": "SHIFT.BMWM3VehiclePhysicsResourceManifest/1",
            "ready": True,
        },
    )
    physics_sha = hashlib.sha256(physics.read_bytes()).hexdigest()
    _write_json(
        handoff_dir / "native_resource_handoff.json",
        {
            "format": "SHIFT.OfflineNativeResourceHandoff/1",
            "ready": True,
            "resource_inputs_ready": True,
            "artifacts": {
                "native_physics_manifest": {
                    "path": "out/offline-pipeline/native-handoff/native_physics_manifest.json",
                    "sha256": physics_sha,
                }
            },
        },
    )
    _write_json(
        pipeline / "pipeline_run.json",
        {
            "format": "SHIFT.OfflineResourcePipelineRun/1",
            "native_resource_handoff_ready": True,
            "native_resource_handoff_blocking_reasons": [],
            "inputs": {
                "runtime_proven_scene_set": str(scene.resolve()),
            },
        },
    )

    profile = {
        "format": "SHIFT.NativeVerticalSliceProfile/1",
        "version": 1,
        "workspace_root": ".",
        "resource_pipeline": "out/offline-pipeline",
        "camera_state": "out/camera.json",
        "participant_boundary": "out/participant.json",
        "solver_frame": "out/solver.sbfr",
        "generated_body_constraint_frame": "out/generated.gbcf",
        "constraint_sample_relation_frame": "out/relations.csrf",
        "constraint_relation_reset_frame": "out/reset.crrf",
        "post_solve_projection": "out/post.sbps",
        "persist_post_solve_body_state": True,
        "frames": 2,
    }
    profile_path = root / "vertical_slice.json"
    _write_json(profile_path, profile)
    return profile_path, pipeline, scene


def test_resource_pipeline_supplies_only_scene_and_physics(tmp_path):
    profile, pipeline, scene = _fixture(tmp_path)
    plan = MODULE.build_launch_plan(profile)

    assert plan["ready"] is True
    assert plan["resource_pipeline"] == str(pipeline.resolve())
    assert plan["checks"]["resource_pipeline"]["ready"] is True
    assert plan["checks"]["resource_pipeline"]["handoff_format"] == (
        "SHIFT.OfflineNativeResourceHandoff/1"
    )
    assert plan["boundary"]["scene_and_physics_from_resource_pipeline"] is True
    assert plan["boundary"]["resource_pipeline_replaces_runtime_evidence"] is False

    scene_index = plan["argv"].index("--scene-set")
    physics_index = plan["argv"].index("--physics-manifest")
    camera_index = plan["argv"].index("--camera-state")
    assert plan["argv"][scene_index + 1] == str(scene.resolve())
    assert plan["argv"][physics_index + 1] == str(
        (pipeline / "native-handoff" / "native_physics_manifest.json").resolve()
    )
    assert plan["argv"][camera_index + 1].endswith("out/camera.json")


def test_resource_pipeline_rejects_explicit_scene_or_physics_override(tmp_path):
    profile, _, _ = _fixture(tmp_path)
    value = json.loads(profile.read_text(encoding="utf-8"))
    value["scene_set"] = "out/other-scene"
    _write_json(profile, value)
    with pytest.raises(MODULE.ProfileError, match="explicit scene_set"):
        MODULE.build_launch_plan(profile)

    value.pop("scene_set")
    value["physics_manifest"] = "evidence/other-physics.json"
    _write_json(profile, value)
    with pytest.raises(MODULE.ProfileError, match="explicit physics_manifest"):
        MODULE.build_launch_plan(profile)


def test_resource_pipeline_rejects_blocked_handoff(tmp_path):
    profile, pipeline, _ = _fixture(tmp_path)
    run_path = pipeline / "pipeline_run.json"
    value = json.loads(run_path.read_text(encoding="utf-8"))
    value["native_resource_handoff_ready"] = False
    value["native_resource_handoff_blocking_reasons"] = ["scene:missing-proof"]
    _write_json(run_path, value)

    with pytest.raises(MODULE.ProfileError, match="scene:missing-proof"):
        MODULE.build_launch_plan(profile)


def test_resource_pipeline_rejects_tampered_native_physics_manifest(tmp_path):
    profile, pipeline, _ = _fixture(tmp_path)
    physics = pipeline / "native-handoff" / "native_physics_manifest.json"
    _write_json(
        physics,
        {
            "format": "SHIFT.BMWM3VehiclePhysicsResourceManifest/1",
            "ready": True,
            "tampered": True,
        },
    )

    with pytest.raises(MODULE.ProfileError, match="SHA-256 mismatch"):
        MODULE.build_launch_plan(profile)


def test_resource_pipeline_does_not_replace_camera_evidence(tmp_path):
    profile, _, _ = _fixture(tmp_path)
    value = json.loads(profile.read_text(encoding="utf-8"))
    value.pop("camera_state")
    _write_json(profile, value)

    with pytest.raises(MODULE.ProfileError, match="camera_state"):
        MODULE.build_launch_plan(profile)


def test_resource_pipeline_rejects_recorded_scene_outside_workspace(tmp_path):
    profile, pipeline, _ = _fixture(tmp_path)
    run_path = pipeline / "pipeline_run.json"
    value = json.loads(run_path.read_text(encoding="utf-8"))
    value["inputs"]["runtime_proven_scene_set"] = str(
        (tmp_path / "outside-scene").resolve()
    )
    _write_json(run_path, value)

    with pytest.raises(MODULE.ProfileError, match="escapes workspace_root"):
        MODULE.build_launch_plan(profile)
