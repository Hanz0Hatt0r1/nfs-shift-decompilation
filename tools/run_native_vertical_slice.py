#!/usr/bin/env python3
"""Validate and launch a complete native SHIFT vertical-slice runtime profile.

The runner does not invent retail semantics. It composes already-proven
native_runtime inputs into one fail-closed launch contract. A Process D offline
resource pipeline may replace the explicit scene-set and physics-manifest paths,
and may transport already-proven participant runtime identity evidence. Camera
and BODY-feedback evidence remain mandatory profile inputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

PROFILE_FORMAT = "SHIFT.NativeVerticalSliceProfile/1"
PLAN_FORMAT = "SHIFT.NativeVerticalSliceLaunchPlan/1"
PIPELINE_FORMAT = "SHIFT.OfflineResourcePipelineRun/1"
RESOURCE_HANDOFF_FORMAT = "SHIFT.OfflineNativeResourceHandoff/1"
RETAIL_ARCHIVE_ADMISSION_FORMAT = "SHIFT.RetailArchiveIdentityAdmission/1"
PARTICIPANT_FORMAT = "SHIFT.NativePhysicsParticipantRuntimeEvidence/1"
JSON_INPUTS: dict[str, tuple[str, bool]] = {
    "camera_state": ("SHIFT.NativeCameraStateBridge/1", True),
    "physics_manifest": ("SHIFT.BMWM3VehiclePhysicsResourceManifest/1", False),
    "participant_boundary": (PARTICIPANT_FORMAT, True),
}

BINARY_INPUTS: dict[str, tuple[bytes, str]] = {
    "solver_frame": (b"SBFR", "SHIFT.NativeBuiltinSolverFramePacket/1"),
    "generated_body_constraint_frame": (
        b"GBCF",
        "SHIFT.NativeGeneratedBodyConstraintFramePacket/1",
    ),
    "constraint_sample_relation_frame": (
        b"CSRF",
        "SHIFT.NativeConstraintSampleRelationFramePacket/1",
    ),
    "constraint_relation_reset_frame": (
        b"CRRF",
        "SHIFT.NativeConstraintRelationResetFramePacket/1",
    ),
    "post_solve_projection": (
        b"SBPS",
        "SHIFT.NativePostSolveBodyProjectionPacket/1",
    ),
}

BODY_FEEDBACK_ENV: dict[str, str] = {
    "SHIFT_NATIVE_BODY_FEEDBACK_SOLVER_FRAME": "solver_frame",
    "SHIFT_NATIVE_BODY_FEEDBACK_GBCF": "generated_body_constraint_frame",
    "SHIFT_NATIVE_BODY_FEEDBACK_CSRF": "constraint_sample_relation_frame",
    "SHIFT_NATIVE_BODY_FEEDBACK_CRRF": "constraint_relation_reset_frame",
    "SHIFT_NATIVE_BODY_FEEDBACK_SBPS": "post_solve_projection",
}

SCENE_FORMAT = "SHIFT.NativeSceneVulkanSet/1"
SCENE_PREPARE_FORMAT = "SHIFT.NativeSceneVulkanSetPrepare/1"
INPUT_SCRIPT_FORMAT = "SHIFT.NativeRuntimeInputScript/1"


class ProfileError(ValueError):
    """Raised when a vertical-slice profile is unsafe or internally incomplete."""


def _load_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ProfileError(f"{label} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ProfileError(f"{label} is not valid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ProfileError(f"{label} JSON must be an object: {path}")
    return value


def _resolve_workspace(profile_path: Path, raw: Any) -> Path:
    text = str(raw if raw is not None else ".").strip() or "."
    root = Path(text)
    if root.is_absolute():
        raise ProfileError("workspace_root must be relative to the profile")
    return (profile_path.parent / root).resolve()


def _resolve_member(root: Path, raw: Any, *, label: str) -> Path:
    text = str(raw or "").strip()
    if not text:
        raise ProfileError(f"profile field {label!r} is required")
    relative = Path(text)
    if relative.is_absolute():
        raise ProfileError(f"profile field {label!r} must be workspace-relative")
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ProfileError(
            f"profile field {label!r} escapes workspace_root: {text}"
        ) from exc
    return candidate


def _resolve_recorded_member(root: Path, raw: Any, *, label: str) -> Path:
    """Resolve a generated artifact path while still confining it to workspace."""
    text = str(raw or "").strip()
    if not text:
        raise ProfileError(f"{label} is missing")
    value = Path(text)
    candidate = value.resolve() if value.is_absolute() else (root / value).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ProfileError(f"{label} escapes workspace_root: {text}") from exc
    return candidate


def _require_json_contract(
    path: Path,
    *,
    expected_format: str,
    require_ready: bool,
    label: str,
) -> dict[str, Any]:
    value = _load_json(path, label=label)
    if value.get("format") != expected_format:
        raise ProfileError(f"{label} must be {expected_format}: {path}")
    if require_ready and value.get("ready") is not True:
        raise ProfileError(f"{label} is not ready: {path}")
    return value


def _validate_retail_archive_identity_profile(
    profile: Mapping[str, Any],
    workspace_root: Path,
) -> dict[str, Any] | None:
    raw = profile.get("retail_archive_identity_admission")
    if raw in (None, ""):
        return None

    track = str(profile.get("track") or "").strip()
    vehicle = str(profile.get("vehicle") or "").strip()
    if not track or not vehicle:
        raise ProfileError(
            "retail archive identity profile requires non-empty track and vehicle"
        )

    path = _resolve_member(
        workspace_root,
        raw,
        label="retail_archive_identity_admission",
    )
    admission = _require_json_contract(
        path,
        expected_format=RETAIL_ARCHIVE_ADMISSION_FORMAT,
        require_ready=True,
        label="retail archive identity admission",
    )
    if str(admission.get("track") or "") != track:
        raise ProfileError(
            "retail archive identity admission track does not match profile target"
        )
    if str(admission.get("vehicle") or "") != vehicle:
        raise ProfileError(
            "retail archive identity admission vehicle does not match profile target"
        )
    return {
        "format": RETAIL_ARCHIVE_ADMISSION_FORMAT,
        "ready": True,
        "track": track,
        "vehicle": vehicle,
        "artifact": str(path),
    }


def _require_binary_packet(
    path: Path,
    *,
    magic: bytes,
    packet_format: str,
    label: str,
) -> dict[str, Any]:
    try:
        with path.open("rb") as stream:
            prefix = stream.read(8)
    except FileNotFoundError as exc:
        raise ProfileError(f"{label} not found: {path}") from exc
    if len(prefix) < 8:
        raise ProfileError(f"{label} packet is truncated: {path}")
    if prefix[:4] != magic:
        raise ProfileError(
            f"{label} must be {packet_format} with magic {magic.decode('ascii')}: {path}"
        )
    version = struct.unpack_from("<I", prefix, 4)[0]
    if version != 1:
        raise ProfileError(
            f"{label} packet version must be 1, got {version}: {path}"
        )
    return {
        "format": packet_format,
        "magic": magic.decode("ascii"),
        "version": version,
    }


def _validate_scene_set(path: Path) -> dict[str, Any]:
    if not path.is_dir():
        raise ProfileError(f"scene_set directory not found: {path}")
    manifest = _require_json_contract(
        path / "bundle_set_manifest.json",
        expected_format=SCENE_FORMAT,
        require_ready=False,
        label="scene set manifest",
    )
    prepare = _require_json_contract(
        path / "bundle_set_prepare.json",
        expected_format=SCENE_PREPARE_FORMAT,
        require_ready=True,
        label="scene set prepare report",
    )
    return {
        "format": manifest["format"],
        "prepare_format": prepare["format"],
        "ready": True,
    }


def _sha256_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError as exc:
        raise ProfileError(f"resource pipeline artifact not found: {path}") from exc


def _validated_artifact_path(
    *,
    workspace_root: Path,
    expected_path: Path,
    artifact: Mapping[str, Any],
    label: str,
) -> Path:
    recorded = _resolve_recorded_member(
        workspace_root,
        artifact.get("path"),
        label=f"{label} artifact path",
    )
    if recorded != expected_path.resolve():
        raise ProfileError(f"{label} artifact path disagrees with pipeline layout")
    expected_sha = str(artifact.get("sha256") or "").strip().lower()
    if len(expected_sha) != 64:
        raise ProfileError(f"{label} artifact SHA-256 is missing or invalid")
    try:
        int(expected_sha, 16)
    except ValueError as exc:
        raise ProfileError(f"{label} artifact SHA-256 is invalid") from exc
    if _sha256_file(expected_path) != expected_sha:
        raise ProfileError(f"{label} artifact SHA-256 mismatch")
    return expected_path


def _resolve_resource_pipeline_inputs(
    workspace_root: Path,
    raw: Any,
) -> tuple[dict[str, Path], dict[str, Any]]:
    pipeline_root = _resolve_member(
        workspace_root,
        raw,
        label="resource_pipeline",
    )
    if not pipeline_root.is_dir():
        raise ProfileError(f"resource_pipeline directory not found: {pipeline_root}")

    pipeline = _require_json_contract(
        pipeline_root / "pipeline_run.json",
        expected_format=PIPELINE_FORMAT,
        require_ready=False,
        label="resource pipeline run",
    )
    if pipeline.get("native_resource_handoff_ready") is not True:
        reasons = pipeline.get("native_resource_handoff_blocking_reasons") or []
        raise ProfileError(
            "resource pipeline native resource handoff is not ready: "
            + ", ".join(str(item) for item in reasons)
        )

    handoff_path = pipeline_root / "native-handoff" / "native_resource_handoff.json"
    handoff = _require_json_contract(
        handoff_path,
        expected_format=RESOURCE_HANDOFF_FORMAT,
        require_ready=True,
        label="native resource handoff",
    )
    if handoff.get("resource_inputs_ready") is not True:
        raise ProfileError("native resource handoff resource inputs are not ready")

    inputs = pipeline.get("inputs") or {}
    if not isinstance(inputs, Mapping):
        raise ProfileError("resource pipeline inputs must be an object")
    scene_set = _resolve_recorded_member(
        workspace_root,
        inputs.get("runtime_proven_scene_set"),
        label="resource pipeline runtime-proven scene set",
    )

    artifacts = handoff.get("artifacts") or {}
    if not isinstance(artifacts, Mapping):
        raise ProfileError("native resource handoff artifacts must be an object")

    physics_manifest = pipeline_root / "native-handoff" / "native_physics_manifest.json"
    physics_artifact = artifacts.get("native_physics_manifest")
    if not isinstance(physics_artifact, Mapping):
        raise ProfileError("native resource handoff has no native physics manifest artifact")
    _validated_artifact_path(
        workspace_root=workspace_root,
        expected_path=physics_manifest,
        artifact=physics_artifact,
        label="native physics manifest",
    )

    resolved: dict[str, Path] = {
        "resource_pipeline": pipeline_root,
        "scene_set": scene_set,
        "physics_manifest": physics_manifest,
    }
    check: dict[str, Any] = {
        "format": pipeline["format"],
        "handoff_format": handoff["format"],
        "ready": True,
        "scene_source": "runtime-proven-process-d-input",
        "physics_source": "exact-process-d-native-compatibility-manifest",
        "participant_source": "explicit-profile-runtime-evidence",
        "participant_runtime_identity_ready": False,
    }

    pipeline_participant_ready = pipeline.get("participant_runtime_identity_ready") is True
    handoff_participant_ready = handoff.get("participant_runtime_identity_ready") is True
    if pipeline_participant_ready != handoff_participant_ready:
        raise ProfileError(
            "resource pipeline participant readiness disagrees with native handoff"
        )

    participant_artifact = artifacts.get("participant_runtime_evidence")
    if participant_artifact is None:
        if handoff_participant_ready:
            raise ProfileError(
                "native resource handoff marks participant identity ready without artifact"
            )
    else:
        if not isinstance(participant_artifact, Mapping):
            raise ProfileError("participant runtime evidence artifact record is invalid")
        if not handoff_participant_ready:
            raise ProfileError(
                "native resource handoff participant artifact is present but identity is not ready"
            )
        participant_path = (
            pipeline_root
            / "native-handoff"
            / "native_physics_participant_runtime_evidence.json"
        )
        _validated_artifact_path(
            workspace_root=workspace_root,
            expected_path=participant_path,
            artifact=participant_artifact,
            label="participant runtime evidence",
        )
        participant_value = _require_json_contract(
            participant_path,
            expected_format=PARTICIPANT_FORMAT,
            require_ready=True,
            label="participant runtime evidence",
        )
        if participant_value.get("registry_selector_identity_join_proven") is not True:
            raise ProfileError(
                "participant runtime evidence has no proven registry/selector identity join"
            )
        if participant_value.get("participant_instance_ready") is not True:
            raise ProfileError(
                "participant runtime evidence has no ready participant instance"
            )
        resolved["participant_boundary"] = participant_path
        check["participant_source"] = "exact-native-handoff-runtime-evidence"
        check["participant_runtime_identity_ready"] = True

    return resolved, check


def _validate_input_script(path: Path) -> int:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise ProfileError(f"input script not found: {path}") from exc
    data = [
        line.strip()
        for line in lines
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not data or data[0] != INPUT_SCRIPT_FORMAT:
        raise ProfileError(
            f"input script must begin with {INPUT_SCRIPT_FORMAT}: {path}"
        )
    expected = 0
    for line in data[1:]:
        parts = line.split()
        if len(parts) != 5:
            raise ProfileError(f"input script row must have 5 columns: {line!r}")
        try:
            step = int(parts[0])
            states = [int(item) for item in parts[1:]]
        except ValueError as exc:
            raise ProfileError(f"input script row is not numeric: {line!r}") from exc
        if step != expected:
            raise ProfileError(
                "input script steps must be contiguous from zero: "
                f"expected {expected}, got {step}"
            )
        if any(state not in (0, 1) for state in states):
            raise ProfileError(
                f"input script control states must be 0 or 1: {line!r}"
            )
        expected += 1
    if expected == 0:
        raise ProfileError("input script must contain at least one fixed-step row")
    return expected


def build_launch_plan(
    profile_path: str | Path,
    *,
    runtime: str | Path = "native_runtime/build/shift_runtime",
    validation: bool = False,
) -> dict[str, Any]:
    profile_path = Path(profile_path).resolve()
    profile = _load_json(profile_path, label="vertical-slice profile")
    if profile.get("format") != PROFILE_FORMAT:
        raise ProfileError(f"profile must be {PROFILE_FORMAT}")
    if int(profile.get("version", 0)) != 1:
        raise ProfileError("profile version must be 1")

    workspace_root = _resolve_workspace(profile_path, profile.get("workspace_root", "."))
    if not workspace_root.is_dir():
        raise ProfileError(f"workspace_root directory not found: {workspace_root}")

    resolved: dict[str, Path] = {}
    checks: dict[str, Any] = {}
    retail_identity_check = _validate_retail_archive_identity_profile(
        profile,
        workspace_root,
    )
    if retail_identity_check is not None:
        checks["retail_archive_identity_admission"] = retail_identity_check

    resource_pipeline_raw = profile.get("resource_pipeline")
    use_resource_pipeline = resource_pipeline_raw not in (None, "")
    participant_from_resource_pipeline = False
    if use_resource_pipeline:
        if profile.get("scene_set") not in (None, ""):
            raise ProfileError(
                "resource_pipeline cannot be combined with explicit scene_set"
            )
        if profile.get("physics_manifest") not in (None, ""):
            raise ProfileError(
                "resource_pipeline cannot be combined with explicit physics_manifest"
            )
        pipeline_paths, pipeline_check = _resolve_resource_pipeline_inputs(
            workspace_root,
            resource_pipeline_raw,
        )
        if "participant_boundary" in pipeline_paths:
            if profile.get("participant_boundary") not in (None, ""):
                raise ProfileError(
                    "resource_pipeline participant artifact cannot be combined with "
                    "explicit participant_boundary"
                )
            participant_from_resource_pipeline = True
        resolved.update(pipeline_paths)
        checks["resource_pipeline"] = pipeline_check
    else:
        resolved["scene_set"] = _resolve_member(
            workspace_root, profile.get("scene_set"), label="scene_set"
        )

    checks["scene_set"] = _validate_scene_set(resolved["scene_set"])

    json_values: dict[str, dict[str, Any]] = {}
    for key, (expected_format, require_ready) in JSON_INPUTS.items():
        if key not in resolved:
            resolved[key] = _resolve_member(workspace_root, profile.get(key), label=key)
        value = _require_json_contract(
            resolved[key],
            expected_format=expected_format,
            require_ready=require_ready,
            label=key.replace("_", " "),
        )
        json_values[key] = value
        checks[key] = {
            "format": value["format"],
            "ready": True,
        }

    participant = json_values["participant_boundary"]
    if participant.get("registry_selector_identity_join_proven") is not True:
        raise ProfileError(
            "participant runtime evidence has no proven registry/selector identity join"
        )
    if participant.get("participant_instance_ready") is not True:
        raise ProfileError(
            "participant runtime evidence has no ready participant instance"
        )

    for key, (magic, packet_format) in BINARY_INPUTS.items():
        resolved[key] = _resolve_member(workspace_root, profile.get(key), label=key)
        checks[key] = _require_binary_packet(
            resolved[key],
            magic=magic,
            packet_format=packet_format,
            label=key.replace("_", " "),
        )

    if profile.get("persist_post_solve_body_state") is not True:
        raise ProfileError(
            "persist_post_solve_body_state must be true for the vertical-slice profile"
        )

    input_script_raw = profile.get("input_script")
    input_steps = 0
    if input_script_raw not in (None, ""):
        resolved["input_script"] = _resolve_member(
            workspace_root, input_script_raw, label="input_script"
        )
        input_steps = _validate_input_script(resolved["input_script"])
        checks["input_script"] = {
            "format": INPUT_SCRIPT_FORMAT,
            "steps": input_steps,
            "ready": True,
        }

    interactive = profile.get("interactive", False)
    if not isinstance(interactive, bool):
        raise ProfileError("interactive must be a boolean")
    if interactive and input_steps:
        raise ProfileError("interactive mode cannot be combined with input_script")
    if interactive and "frames" in profile:
        raise ProfileError("interactive mode must not specify frames")

    if interactive:
        frames = None
    else:
        frames_raw = profile.get("frames", input_steps if input_steps else 120)
        if isinstance(frames_raw, bool):
            raise ProfileError("frames must be a positive integer")
        try:
            frames = int(frames_raw)
        except (TypeError, ValueError) as exc:
            raise ProfileError("frames must be a positive integer") from exc
        if frames <= 0:
            raise ProfileError("frames must be a positive integer")
        if input_steps and frames != input_steps:
            raise ProfileError(
                f"frames must equal input script step count ({input_steps}), got {frames}"
            )

    runtime_path = Path(runtime)
    if not runtime_path.is_absolute():
        runtime_path = (workspace_root / runtime_path).resolve()
    if not runtime_path.is_file():
        raise ProfileError(f"native runtime executable not found: {runtime_path}")
    if not os.access(runtime_path, os.X_OK):
        raise ProfileError(f"native runtime is not executable: {runtime_path}")

    argv = [
        str(runtime_path),
        "--scene-set",
        str(resolved["scene_set"]),
        # The current CLI requires --shader-dir for every geometry source. The
        # scene-set path carries child SPIR-V, so this existing directory is a
        # compatibility value rather than a new shader-selection semantic.
        "--shader-dir",
        str(workspace_root),
        "--camera-state",
        str(resolved["camera_state"]),
        "--physics-manifest",
        str(resolved["physics_manifest"]),
        "--participant-boundary",
        str(resolved["participant_boundary"]),
    ]
    if input_steps:
        argv.extend(["--input-script", str(resolved["input_script"])])
    if interactive:
        argv.append("--continuous")
    else:
        argv.extend(["--frames", str(frames)])
    if validation:
        argv.append("--validation")

    environment = {"SHIFT_NATIVE_BODY_FEEDBACK": "1"}
    for environment_name, resolved_key in BODY_FEEDBACK_ENV.items():
        environment[environment_name] = str(resolved[resolved_key])

    if input_steps:
        mode = "script"
    elif interactive:
        mode = "interactive-keyboard"
    else:
        mode = "keyboard"

    return {
        "format": PLAN_FORMAT,
        "version": 1,
        "ready": True,
        "profile": str(profile_path),
        "workspace_root": str(workspace_root),
        "resource_pipeline": (
            str(resolved["resource_pipeline"])
            if use_resource_pipeline
            else None
        ),
        "mode": mode,
        "interactive": interactive,
        "frames": frames,
        "frame_limit_policy": (
            "native-continuous-until-window-quit"
            if interactive
            else "explicit-bounded-frame-count"
        ),
        "persist_post_solve_body_state": True,
        "checks": checks,
        "argv": argv,
        "environment": environment,
        "boundary": {
            "scene_render_admitted": True,
            "camera_state_admitted": True,
            "participant_runtime_identity_admitted": True,
            "provider_absent_solver_chain_admitted": True,
            "constraint_refresh_admitted": True,
            "relation_reset_selection_admitted": True,
            "post_solve_body_accumulator_persistence_admitted": True,
            "dynamic_body_feedback_scheduler_admitted": True,
            "legacy_solver_replay_cli_disabled": True,
            "scene_and_physics_from_resource_pipeline": use_resource_pipeline,
            "participant_runtime_evidence_from_resource_pipeline": (
                participant_from_resource_pipeline
            ),
            "resource_pipeline_replaces_runtime_evidence": False,
            "camera_or_body_feedback_from_resource_pipeline": False,
            "retail_archive_identity_revalidated": (
                retail_identity_check is not None
            ),
            "retail_archive_identity_rederived_by_process2": False,
            "window_quit_drives_session_end": interactive,
            "native_continuous_runtime_loop_admitted": interactive,
            "persistent_vehicle_transform_motion_claimed": False,
            "provider_present_dispatch_claimed": False,
            "retail_game_loop_claimed": False,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", help=f"{PROFILE_FORMAT} JSON profile")
    parser.add_argument(
        "--runtime",
        default="native_runtime/build/shift_runtime",
        help="native runtime executable, workspace-relative unless absolute",
    )
    parser.add_argument(
        "--validation", action="store_true", help="enable Vulkan validation"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate and print the launch plan only",
    )
    parser.add_argument("--json-out", help="optional path for the launch-plan JSON")
    args = parser.parse_args(argv)

    try:
        plan = build_launch_plan(
            args.profile,
            runtime=args.runtime,
            validation=args.validation,
        )
    except (OSError, ProfileError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered, encoding="utf-8")
    print(rendered, end="")

    if args.dry_run:
        return 0
    launch_environment = os.environ.copy()
    launch_environment.update(plan["environment"])
    completed = subprocess.run(
        plan["argv"],
        env=launch_environment,
        check=False,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
