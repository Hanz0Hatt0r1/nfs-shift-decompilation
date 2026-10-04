from __future__ import annotations

import importlib.util
import json
import struct
from pathlib import Path

import pytest

from offline_vertical_slice_profile import build_vertical_slice_profile_prepare


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "tools" / "run_native_vertical_slice.py"
SPEC = importlib.util.spec_from_file_location("phase711_runner", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)

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


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")


def _fixture(tmp_path: Path) -> tuple[Path, dict, dict[str, str], Path]:
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
        root / "out" / "physics.json",
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
        path = root / "out" / name
        path.write_bytes(magic + struct.pack("<I", 1) + b"fixture")

    track = "Silverstone_Era3_GrandPrix"
    vehicle = "BMW_M3_E36"
    admission = root / "out" / "retail_archive_identity_admission.json"
    _write_json(
        admission,
        {
            "format": "SHIFT.RetailArchiveIdentityAdmission/1",
            "version": 1,
            "ready": True,
            "track": track,
            "vehicle": vehicle,
        },
    )

    paths = {
        "scene_set": "out/scene",
        "camera_state": "out/camera.json",
        "physics_manifest": "out/physics.json",
        "participant_boundary": "out/participant.json",
        "solver_frame": "out/solver.sbfr",
        "generated_body_constraint_frame": "out/generated.gbcf",
        "constraint_sample_relation_frame": "out/relations.csrf",
        "constraint_relation_reset_frame": "out/reset.crrf",
        "post_solve_projection": "out/post.sbps",
    }
    rows = [
        {
            "name": name,
            "satisfied": False,
            "artifact": None,
            "artifact_origin": None,
        }
        for name in PROFILE_INPUTS
    ]
    rows.append(
        {
            "name": "input_binding",
            "satisfied": False,
            "artifact": None,
            "artifact_origin": None,
        }
    )
    requirements = {
        "format": "SHIFT.OfflineNativeRuntimeRequirements/1",
        "version": 1,
        "ready": False,
        "track": track,
        "vehicle": vehicle,
        "retail_archive_identity_required": True,
        "retail_archive_identity_ready": True,
        "retail_archive_identity_admission": admission.relative_to(root).as_posix(),
        "requirements": rows,
    }
    return root, requirements, paths, admission


def test_generated_profile_propagates_identity_and_launcher_revalidates(tmp_path: Path):
    root, requirements, explicit, admission = _fixture(tmp_path)
    profile_path = root / "vertical_slice_profile.json"

    prepare = build_vertical_slice_profile_prepare(
        requirements,
        workspace_root=root,
        profile_path=profile_path,
        explicit_inputs=explicit,
        keyboard=True,
        frames=3,
    )

    assert prepare["ready"] is True
    profile = prepare["profile"]
    assert profile["track"] == requirements["track"]
    assert profile["vehicle"] == requirements["vehicle"]
    assert profile["retail_archive_identity_admission"] == (
        admission.relative_to(root).as_posix()
    )
    assert prepare["boundary"]["retail_archive_identity_propagated"] is True

    _write_json(profile_path, profile)
    plan = RUNNER.build_launch_plan(profile_path)
    check = plan["checks"]["retail_archive_identity_admission"]
    assert check["ready"] is True
    assert check["track"] == requirements["track"]
    assert check["vehicle"] == requirements["vehicle"]
    assert plan["boundary"]["retail_archive_identity_revalidated"] is True
    assert plan["boundary"]["retail_archive_identity_rederived_by_process2"] is False


def test_profile_prepare_rejects_failed_identity_even_with_explicit_paths(tmp_path: Path):
    root, requirements, explicit, _ = _fixture(tmp_path)
    requirements["retail_archive_identity_ready"] = False

    prepare = build_vertical_slice_profile_prepare(
        requirements,
        workspace_root=root,
        profile_path=root / "profile.json",
        explicit_inputs=explicit,
        keyboard=True,
        frames=3,
    )

    assert prepare["ready"] is False
    assert "retail-archive-identity:not-ready" in prepare["blocking_reasons"]


def test_launcher_rejects_identity_that_becomes_not_ready_after_profile_creation(
    tmp_path: Path,
):
    root, requirements, explicit, admission = _fixture(tmp_path)
    profile_path = root / "profile.json"
    prepare = build_vertical_slice_profile_prepare(
        requirements,
        workspace_root=root,
        profile_path=profile_path,
        explicit_inputs=explicit,
        keyboard=True,
        frames=3,
    )
    assert prepare["ready"] is True
    _write_json(profile_path, prepare["profile"])

    value = json.loads(admission.read_text(encoding="utf-8"))
    value["ready"] = False
    _write_json(admission, value)

    with pytest.raises(RUNNER.ProfileError, match="identity admission is not ready"):
        RUNNER.build_launch_plan(profile_path)


def test_launcher_rejects_identity_target_mismatch(tmp_path: Path):
    root, requirements, explicit, admission = _fixture(tmp_path)
    profile_path = root / "profile.json"
    prepare = build_vertical_slice_profile_prepare(
        requirements,
        workspace_root=root,
        profile_path=profile_path,
        explicit_inputs=explicit,
        keyboard=True,
        frames=3,
    )
    assert prepare["ready"] is True
    _write_json(profile_path, prepare["profile"])

    value = json.loads(admission.read_text(encoding="utf-8"))
    value["vehicle"] = "OTHER"
    _write_json(admission, value)

    with pytest.raises(RUNNER.ProfileError, match="vehicle does not match"):
        RUNNER.build_launch_plan(profile_path)
