"""Describe remaining native-runtime evidence gates after offline bootstrap.

This module is diagnostic only. It translates already-produced Process 3
bootstrap artifacts into explicit runtime requirements without creating,
selecting, or substituting any missing evidence.
"""
from __future__ import annotations

from typing import Any, Mapping

FORMAT = "SHIFT.OfflineNativeRuntimeRequirements/1"
BOOTSTRAP_FORMAT = "SHIFT.OfflineRuntimeBootstrap/1"


def _artifact_path(bootstrap: Mapping[str, Any], name: str) -> str | None:
    artifacts = bootstrap.get("artifacts") or {}
    if not isinstance(artifacts, Mapping):
        return None
    text = str(artifacts.get(name) or "").strip()
    return text or None


def _vehicle_artifact_path(bootstrap: Mapping[str, Any], name: str) -> str | None:
    stages = bootstrap.get("stages") or {}
    vehicle = stages.get("native_vehicle") if isinstance(stages, Mapping) else None
    if not isinstance(vehicle, Mapping):
        return None
    artifacts = vehicle.get("artifacts") or {}
    row = artifacts.get(name) if isinstance(artifacts, Mapping) else None
    if not isinstance(row, Mapping):
        return None
    text = str(row.get("path") or "").strip()
    return text or None


def build_runtime_requirements(bootstrap: Mapping[str, Any]) -> dict[str, Any]:
    """Return exact satisfied/missing runtime inputs without promoting evidence."""
    if bootstrap.get("format") != BOOTSTRAP_FORMAT:
        raise ValueError(f"bootstrap must be {BOOTSTRAP_FORMAT}")

    readiness = bootstrap.get("readiness") or {}
    if not isinstance(readiness, Mapping):
        readiness = {}

    physics_ready = readiness.get("vehicle_runtime_physics_contract_ready") is True
    participant_ready = (
        readiness.get("vehicle_participant_runtime_identity_ready") is True
    )
    scene_ready = readiness.get("runtime_scene_ready") is True

    rows: list[dict[str, Any]] = [
        {
            "name": "scene_set",
            "expected_format": "SHIFT.NativeSceneVulkanSet/1",
            "satisfied": scene_ready,
            "artifact": None,
            "source": "runtime-proven draw admission",
        },
        {
            "name": "physics_manifest",
            "expected_format": "SHIFT.BMWM3VehiclePhysicsResourceManifest/1",
            "satisfied": physics_ready,
            "artifact": (
                _vehicle_artifact_path(bootstrap, "native_physics_manifest")
                if physics_ready else None
            ),
            "source": "exact offline vehicle physics compatibility manifest",
        },
        {
            "name": "participant_boundary",
            "expected_format": "SHIFT.NativePhysicsParticipantRuntimeEvidence/1",
            "satisfied": participant_ready,
            "artifact": (
                _artifact_path(bootstrap, "participant_runtime_evidence")
                if participant_ready else None
            ),
            "source": "exact runtime participant observation join",
        },
        {
            "name": "camera_state",
            "expected_format": "SHIFT.NativeCameraStateBridge/1",
            "satisfied": False,
            "artifact": None,
            "source": "external proven runtime evidence",
        },
        {
            "name": "solver_frame",
            "expected_format": "SHIFT.NativeBuiltinSolverFramePacket/1",
            "packet_magic": "SBFR",
            "satisfied": False,
            "artifact": None,
            "source": "external proven runtime evidence",
        },
        {
            "name": "generated_body_constraint_frame",
            "expected_format": "SHIFT.NativeGeneratedBodyConstraintFramePacket/1",
            "packet_magic": "GBCF",
            "satisfied": False,
            "artifact": None,
            "source": "external proven runtime evidence",
        },
        {
            "name": "constraint_sample_relation_frame",
            "expected_format": "SHIFT.NativeConstraintSampleRelationFramePacket/1",
            "packet_magic": "CSRF",
            "satisfied": False,
            "artifact": None,
            "source": "external proven runtime evidence",
        },
        {
            "name": "constraint_relation_reset_frame",
            "expected_format": "SHIFT.NativeConstraintRelationResetFramePacket/1",
            "packet_magic": "CRRF",
            "satisfied": False,
            "artifact": None,
            "source": "external proven runtime evidence",
        },
        {
            "name": "post_solve_projection",
            "expected_format": "SHIFT.NativePostSolveBodyProjectionPacket/1",
            "packet_magic": "SBPS",
            "satisfied": False,
            "artifact": None,
            "source": "external proven runtime evidence",
        },
        {
            "name": "input_binding",
            "expected_format": "SHIFT.NativeRuntimeInputScript/1 or interactive input",
            "satisfied": False,
            "artifact": None,
            "source": "external runtime choice/evidence",
        },
    ]

    missing = [str(row["name"]) for row in rows if row.get("satisfied") is not True]
    satisfied = [str(row["name"]) for row in rows if row.get("satisfied") is True]
    ready = not missing
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "offline_build_ready": bootstrap.get("offline_build_ready") is True,
        "runtime_ready_claimed_by_bootstrap": bootstrap.get("runtime_ready") is True,
        "track": bootstrap.get("track"),
        "vehicle": bootstrap.get("vehicle"),
        "requirements": rows,
        "summary": {
            "requirement_count": len(rows),
            "satisfied_count": len(satisfied),
            "missing_count": len(missing),
            "satisfied": satisfied,
            "missing": missing,
        },
        "blocking_reasons": [
            f"runtime-requirement-missing:{name}" for name in missing
        ],
        "boundary": {
            "diagnostic_only": True,
            "missing_evidence_synthesized": False,
            "artifact_substitution_allowed": False,
            "static_scene_promoted_to_runtime_scene": False,
            "structural_participant_promoted_to_runtime_identity": False,
            "vertical_slice_launcher_validation_still_required": True,
            "original_game_execution_required": False,
        },
    }
