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
    "run_native_vertical_slice_pipeline_participant",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_packet(path: Path, magic: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(magic + struct.pack("<I", 1) + b"fixture")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "workspace"
    root.mkdir(parents=True)

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
    participant = handoff_dir / "native_physics_participant_runtime_evidence.json"
    _write_json(
        physics,
        {
            "format": "SHIFT.BMWM3VehiclePhysicsResourceManifest/1",
            "ready": True,
        },
    )
    _write_json(
        participant,
        {
            "format": "SHIFT.NativePhysicsParticipantRuntimeEvidence/1",
            "version": 1,
            "status": "ready",
            "ready": True,
            "blocking_reasons": [],
            "registry_selector_identity_join_proven": True,
            "participant_instance_ready": True,
        },
    )
    _write_json(
        handoff_dir / "native_resource_handoff.json",
        {
            "format": "SHIFT.OfflineNativeResourceHandoff/1",
            "version": 1,
            "status": "ready",
            "ready": True,
            "resource_inputs_ready": True,
            "participant_runtime_identity_evaluated": True,
            "participant_runtime_identity_ready": True,
            "artifacts": {
                "native_physics_manifest": {
                    "path": "out/offline-pipeline/native-handoff/native_physics_manifest.json",
                    "sha256": _sha(physics),
                },
                "participant_runtime_evidence": {
                    "path": (
                        "out/offline-pipeline/native-handoff/"
                        "native_physics_participant_runtime_evidence.json"
                    ),
                    "sha256": _sha(participant),
                    "source_sha256": _sha(participant),
                    "bytes_preserved": True,
                },
            },
        },
    )
    _write_json(
        pipeline / "pipeline_run.json",
        {
            "format": "SHIFT.OfflineResourcePipelineRun/1",
            "native_resource_handoff_ready": True,
            "native_resource_handoff_blocking_reasons": [],
            "participant_runtime_identity_evaluated": True,
            "participant_runtime_identity_ready": True,
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
    return profile_path, pipeline, participant


def test_resource_pipeline_supplies_exact_participant_runtime_evidence(tmp_path):
    profile, pipeline, participant = _fixture(tmp_path)
    plan = MODULE.build_launch_plan(profile)

    participant_index = plan["argv"].index("--participant-boundary")
    assert plan["argv"][participant_index + 1] == str(participant.resolve())
    assert plan["checks"]["resource_pipeline"]["participant_source"] == (
        "exact-native-handoff-runtime-evidence"
    )
    assert (
        plan["checks"]["resource_pipeline"]["participant_runtime_identity_ready"]
        is True
    )
    assert plan["boundary"]["participant_runtime_evidence_from_resource_pipeline"] is True
    assert plan["boundary"]["resource_pipeline_replaces_runtime_evidence"] is False
    assert plan["boundary"]["camera_or_body_feedback_from_resource_pipeline"] is False
    assert plan["resource_pipeline"] == str(pipeline.resolve())


def test_pipeline_participant_artifact_rejects_explicit_profile_override(tmp_path):
    profile, _, _ = _fixture(tmp_path)
    value = json.loads(profile.read_text(encoding="utf-8"))
    value["participant_boundary"] = "out/other-participant.json"
    _write_json(profile, value)

    with pytest.raises(MODULE.ProfileError, match="explicit participant_boundary"):
        MODULE.build_launch_plan(profile)


def test_pipeline_participant_artifact_sha_mismatch_fails_closed(tmp_path):
    profile, _, participant = _fixture(tmp_path)
    value = json.loads(participant.read_text(encoding="utf-8"))
    value["tampered"] = True
    _write_json(participant, value)

    with pytest.raises(
        MODULE.ProfileError,
        match="participant runtime evidence artifact SHA-256 mismatch",
    ):
        MODULE.build_launch_plan(profile)


def test_pipeline_participant_ready_without_artifact_fails_closed(tmp_path):
    profile, pipeline, _ = _fixture(tmp_path)
    handoff_path = pipeline / "native-handoff" / "native_resource_handoff.json"
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    handoff["artifacts"].pop("participant_runtime_evidence")
    _write_json(handoff_path, handoff)

    with pytest.raises(
        MODULE.ProfileError,
        match="marks participant identity ready without artifact",
    ):
        MODULE.build_launch_plan(profile)


def test_pipeline_participant_artifact_requires_ready_handoff_identity(tmp_path):
    profile, pipeline, _ = _fixture(tmp_path)
    handoff_path = pipeline / "native-handoff" / "native_resource_handoff.json"
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    handoff["participant_runtime_identity_ready"] = False
    _write_json(handoff_path, handoff)

    with pytest.raises(
        MODULE.ProfileError,
        match="participant readiness disagrees with native handoff",
    ):
        MODULE.build_launch_plan(profile)


def test_pipeline_participant_does_not_replace_camera_or_body_feedback(tmp_path):
    profile, _, _ = _fixture(tmp_path)
    value = json.loads(profile.read_text(encoding="utf-8"))
    value.pop("camera_state")
    _write_json(profile, value)
    with pytest.raises(MODULE.ProfileError, match="camera_state"):
        MODULE.build_launch_plan(profile)

    profile, _, _ = _fixture(tmp_path / "feedback")
    value = json.loads(profile.read_text(encoding="utf-8"))
    value.pop("solver_frame")
    _write_json(profile, value)
    with pytest.raises(MODULE.ProfileError, match="solver_frame"):
        MODULE.build_launch_plan(profile)
