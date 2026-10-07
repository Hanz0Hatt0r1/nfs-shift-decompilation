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
    "run_native_vertical_slice_pipeline_target_binding",
    MODULE_PATH,
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

TRACK = "Silverstone_Era3_GrandPrix"
VEHICLE = "BMW_M3_E36"


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


def _fixture(tmp_path: Path, *, include_profile_target: bool = True) -> tuple[Path, Path]:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True)

    runtime = workspace / "native_runtime" / "build" / "shift_runtime"
    runtime.parent.mkdir(parents=True)
    runtime.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    runtime.chmod(0o755)

    scene = workspace / "out" / "native-scene-vulkan"
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
        workspace / "out" / "camera.json",
        {"format": "SHIFT.NativeCameraStateBridge/1", "ready": True},
    )
    _write_json(
        workspace / "out" / "participant.json",
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
        _write_packet(workspace / "out" / name, magic)

    pipeline = workspace / "out" / "offline-pipeline"
    handoff_dir = pipeline / "native-handoff"
    physics = handoff_dir / "native_physics_manifest.json"
    _write_json(
        physics,
        {
            "format": "SHIFT.BMWM3VehiclePhysicsResourceManifest/1",
            "ready": True,
        },
    )
    _write_json(
        handoff_dir / "native_resource_handoff.json",
        {
            "format": "SHIFT.OfflineNativeResourceHandoff/1",
            "ready": True,
            "resource_inputs_ready": True,
            "scene_catalog_join": {
                "format": "SHIFT.OfflineSceneCatalogJoin/1",
                "ready": True,
                "track": TRACK,
            },
            "vehicle_physics_manifest": {
                "format": "SHIFT.VehiclePhysicsResourceManifest/1",
                "ready": True,
                "vehicle": VEHICLE,
            },
            "artifacts": {
                "native_physics_manifest": {
                    "path": "out/offline-pipeline/native-handoff/native_physics_manifest.json",
                    "sha256": _sha(physics),
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
            "inputs": {"runtime_proven_scene_set": str(scene.resolve())},
        },
    )

    profile: dict = {
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
    if include_profile_target:
        admission = workspace / "out" / "retail_archive_identity_admission.json"
        _write_json(
            admission,
            {
                "format": "SHIFT.RetailArchiveIdentityAdmission/1",
                "ready": True,
                "track": TRACK,
                "vehicle": VEHICLE,
            },
        )
        profile.update({
            "track": TRACK,
            "vehicle": VEHICLE,
            "retail_archive_identity_admission": (
                "out/retail_archive_identity_admission.json"
            ),
        })

    profile_path = workspace / "vertical_slice.json"
    _write_json(profile_path, profile)
    return profile_path, pipeline


def _handoff(pipeline: Path) -> tuple[Path, dict]:
    path = pipeline / "native-handoff" / "native_resource_handoff.json"
    return path, json.loads(path.read_text(encoding="utf-8"))


def test_resource_pipeline_target_matches_retail_profile_target(tmp_path: Path):
    profile, _ = _fixture(tmp_path)
    plan = MODULE.build_launch_plan(profile)

    target = plan["checks"]["resource_pipeline"]["target_identity"]
    assert target == {
        "checked": True,
        "track": TRACK,
        "vehicle": VEHICLE,
        "expected_track": TRACK,
        "expected_vehicle": VEHICLE,
        "ready": True,
    }
    assert plan["boundary"]["resource_pipeline_target_identity_checked"] is True
    assert plan["boundary"]["retail_archive_identity_revalidated"] is True


def test_resource_pipeline_rejects_scene_target_from_other_track(tmp_path: Path):
    profile, pipeline = _fixture(tmp_path)
    handoff_path, handoff = _handoff(pipeline)
    handoff["scene_catalog_join"]["track"] = "BrandsHatch"
    _write_json(handoff_path, handoff)

    with pytest.raises(
        MODULE.ProfileError,
        match="resource pipeline track does not match profile target",
    ):
        MODULE.build_launch_plan(profile)


def test_resource_pipeline_rejects_physics_target_from_other_vehicle(tmp_path: Path):
    profile, pipeline = _fixture(tmp_path)
    handoff_path, handoff = _handoff(pipeline)
    handoff["vehicle_physics_manifest"]["vehicle"] = "Audi_R8"
    _write_json(handoff_path, handoff)

    with pytest.raises(
        MODULE.ProfileError,
        match="resource pipeline vehicle does not match profile target",
    ):
        MODULE.build_launch_plan(profile)


def test_targeted_profile_requires_handoff_scene_target_identity(tmp_path: Path):
    profile, pipeline = _fixture(tmp_path)
    handoff_path, handoff = _handoff(pipeline)
    handoff.pop("scene_catalog_join")
    _write_json(handoff_path, handoff)

    with pytest.raises(
        MODULE.ProfileError,
        match="no scene catalog join for profile track",
    ):
        MODULE.build_launch_plan(profile)


def test_targeted_profile_requires_handoff_vehicle_target_identity(tmp_path: Path):
    profile, pipeline = _fixture(tmp_path)
    handoff_path, handoff = _handoff(pipeline)
    handoff.pop("vehicle_physics_manifest")
    _write_json(handoff_path, handoff)

    with pytest.raises(
        MODULE.ProfileError,
        match="no vehicle physics manifest for profile vehicle",
    ):
        MODULE.build_launch_plan(profile)


def test_legacy_unlabelled_profile_remains_compatible(tmp_path: Path):
    profile, pipeline = _fixture(tmp_path, include_profile_target=False)
    handoff_path, handoff = _handoff(pipeline)
    handoff.pop("scene_catalog_join")
    handoff.pop("vehicle_physics_manifest")
    _write_json(handoff_path, handoff)

    plan = MODULE.build_launch_plan(profile)
    target = plan["checks"]["resource_pipeline"]["target_identity"]
    assert target["checked"] is False
    assert target["track"] is None
    assert target["vehicle"] is None
    assert plan["boundary"]["resource_pipeline_target_identity_checked"] is False
