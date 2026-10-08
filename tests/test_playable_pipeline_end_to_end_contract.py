from __future__ import annotations

import hashlib
import importlib.util
import json
import struct
from pathlib import Path

import pytest

from offline_playable_pipeline_profile import build_playable_pipeline_profile_prepare
from offline_vertical_slice_profile import PROFILE_INPUTS


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "tools" / "run_native_vertical_slice_playable_pipeline.py"
SPEC = importlib.util.spec_from_file_location(
    "run_native_vertical_slice_playable_pipeline_integration",
    RUNNER_PATH,
)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_packet(path: Path, magic: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(magic + struct.pack("<I", 1) + b"integration-fixture")


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    root = tmp_path / "workspace"
    root.mkdir()

    runtime = root / "native_runtime" / "build" / "shift_runtime"
    runtime.parent.mkdir(parents=True)
    runtime.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    runtime.chmod(0o755)

    source_scene = root / "out" / "pipeline-scene"
    source_scene.mkdir(parents=True)
    source_manifest = source_scene / "bundle_set_manifest.json"
    _write_json(
        source_manifest,
        {
            "format": "SHIFT.NativeSceneVulkanSet/1",
            "version": 1,
            "ready": True,
            "draws": [],
        },
    )
    _write_json(
        source_scene / "bundle_set_prepare.json",
        {
            "format": "SHIFT.NativeSceneVulkanSetPrepare/1",
            "version": 1,
            "ready": True,
        },
    )

    pipeline = root / "out" / "offline-pipeline"
    handoff_dir = pipeline / "native-handoff"
    handoff_dir.mkdir(parents=True)
    physics = handoff_dir / "native_physics_manifest.json"
    participant = handoff_dir / "native_physics_participant_runtime_evidence.json"
    _write_json(
        physics,
        {
            "format": "SHIFT.BMWM3VehiclePhysicsResourceManifest/1",
            "version": 1,
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
                },
            },
        },
    )
    _write_json(
        pipeline / "pipeline_run.json",
        {
            "format": "SHIFT.OfflineResourcePipelineRun/1",
            "version": 1,
            "native_resource_handoff_ready": True,
            "native_resource_handoff_blocking_reasons": [],
            "participant_runtime_identity_ready": True,
            "inputs": {
                "runtime_proven_scene_set": str(source_scene.resolve()),
            },
        },
    )

    composite = root / "out" / "playable-scene" / "scene"
    composite.mkdir(parents=True)
    composite_manifest = composite / "bundle_set_manifest.json"
    _write_json(
        composite_manifest,
        {
            "format": "SHIFT.NativeSceneVulkanSet/1",
            "version": 1,
            "ready": True,
            "source": {
                "track_scene_set": str(source_scene.resolve()),
                "track_manifest_sha256": _sha(source_manifest),
            },
        },
    )
    _write_json(
        composite / "bundle_set_prepare.json",
        {
            "format": "SHIFT.NativeSceneVulkanSetPrepare/1",
            "version": 1,
            "ready": True,
        },
    )
    composition = root / "out" / "playable-scene" / "playable_scene_composition.json"
    _write_json(
        composition,
        {
            "format": "SHIFT.NativePlayableSceneVulkanSet/1",
            "version": 1,
            "ready": True,
            "scene_set": {
                "format": "SHIFT.NativeSceneVulkanSet/1",
                "path": str(composite.resolve()),
                "manifest_sha256": _sha(composite_manifest),
                "ready": True,
            },
        },
    )
    playable_bootstrap = root / "out" / "playable-scene" / "playable_scene_bootstrap.json"
    _write_json(
        playable_bootstrap,
        {
            "format": "SHIFT.NativePlayableSceneBootstrap/1",
            "version": 1,
            "status": "ready",
            "ready": True,
            "scene_set_ready": True,
            "track_scene_set": str(source_scene.resolve()),
            "artifacts": {
                "scene_set_dir": str(composite.resolve()),
                "scene_composition": str(composition.resolve()),
            },
        },
    )

    camera = root / "runtime" / "camera.json"
    _write_json(
        camera,
        {
            "format": "SHIFT.NativeCameraStateBridge/1",
            "version": 1,
            "ready": True,
        },
    )
    packet_paths = {
        "solver_frame": (root / "runtime" / "solver.sbfr", b"SBFR"),
        "generated_body_constraint_frame": (root / "runtime" / "generated.gbcf", b"GBCF"),
        "constraint_sample_relation_frame": (root / "runtime" / "relations.csrf", b"CSRF"),
        "constraint_relation_reset_frame": (root / "runtime" / "reset.crrf", b"CRRF"),
        "post_solve_projection": (root / "runtime" / "post.sbps", b"SBPS"),
    }
    for path, magic in packet_paths.values():
        _write_packet(path, magic)

    requirements = {
        "format": "SHIFT.OfflineNativeRuntimeRequirements/1",
        "version": 1,
        "requirements": [
            {"name": name, "satisfied": False, "artifact": None}
            for name in PROFILE_INPUTS
        ],
    }
    explicit = {
        "camera_state": camera.relative_to(root).as_posix(),
        **{
            name: path.relative_to(root).as_posix()
            for name, (path, _magic) in packet_paths.items()
        },
    }
    profile_path = root / "profiles" / "playable.json"
    prepared = build_playable_pipeline_profile_prepare(
        requirements,
        workspace_root=root,
        profile_path=profile_path,
        explicit_inputs=explicit,
        resource_pipeline=pipeline.relative_to(root),
        playable_scene_bootstrap=playable_bootstrap.relative_to(root),
        keyboard=True,
        frames=3,
    )
    assert prepared["ready"] is True
    assert prepared["profile"] is not None
    _write_json(profile_path, prepared["profile"])
    return profile_path, source_scene, composite, composite_manifest


def test_real_profile_pipeline_provenance_and_launcher_contract_join(tmp_path):
    profile, source_scene, composite, _manifest = _fixture(tmp_path)

    plan = RUNNER.build_playable_pipeline_launch_plan(profile)

    scene_index = plan["argv"].index("--scene-set")
    physics_index = plan["argv"].index("--physics-manifest")
    participant_index = plan["argv"].index("--participant-boundary")
    assert plan["argv"][scene_index + 1] == str(composite.resolve())
    assert "offline-pipeline/native-handoff/native_physics_manifest.json" in plan["argv"][
        physics_index + 1
    ]
    assert "native_physics_participant_runtime_evidence.json" in plan["argv"][
        participant_index + 1
    ]
    assert plan["checks"]["resource_pipeline_playable_scene_join"]["ready"] is True
    assert plan["checks"]["resource_pipeline_playable_scene_join"]["source_scene"][
        "path"
    ] == source_scene.relative_to(profile.parent.parent).as_posix()
    assert plan["boundary"]["physics_and_participant_from_resource_pipeline"] is True
    assert plan["boundary"]["resource_pipeline_source_scene_directly_submitted"] is False
    assert plan["boundary"]["playable_composite_scene_provenance_revalidated"] is True


def test_real_cross_module_contract_fails_closed_after_composite_manifest_tamper(tmp_path):
    profile, _source_scene, _composite, composite_manifest = _fixture(tmp_path)
    payload = json.loads(composite_manifest.read_text(encoding="utf-8"))
    payload["tampered"] = True
    _write_json(composite_manifest, payload)

    with pytest.raises(
        RUNNER.native.ProfileError,
        match="playable composite scene manifest SHA-256 mismatch",
    ):
        RUNNER.build_playable_pipeline_launch_plan(profile)
