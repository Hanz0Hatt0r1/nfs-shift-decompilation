"""Compose the proven offline resource/bootstrap stages into a vertical-slice profile.

This module stops before launcher validation or runtime execution. Missing runtime
inputs remain explicit and a blocked selected resource bootstrap cannot be
bypassed with externally supplied runtime artifacts. Explicit runtime artifacts
are admitted into the requirements ledger only after launcher-equivalent
validation.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from offline_runtime_bootstrap import build_offline_runtime_bootstrap
from offline_runtime_requirements import build_runtime_requirements
from offline_vertical_slice_profile import (
    FORMAT as PROFILE_PREPARE_FORMAT,
    build_vertical_slice_profile_prepare,
)
from runtime_input_validation import validate_explicit_runtime_inputs

FORMAT = "SHIFT.OfflineNativeVerticalSliceBootstrap/1"


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _blocked_profile_prepare(
    *,
    workspace_root: Path,
    profile_path: Path,
    reasons: Sequence[str],
) -> dict[str, Any]:
    blockers = list(dict.fromkeys(str(reason) for reason in reasons if reason))
    return {
        "format": PROFILE_PREPARE_FORMAT,
        "version": 1,
        "status": "blocked",
        "ready": False,
        "profile": None,
        "workspace_root": str(workspace_root),
        "profile_path": str(profile_path),
        "auto_filled_inputs": [],
        "explicit_filled_inputs": [],
        "blocking_reasons": blockers or ["offline-bootstrap:not-ready"],
        "boundary": {
            "offline_bootstrap_gate_bypassed": False,
            "missing_evidence_synthesized": False,
            "runtime_execution_claimed": False,
        },
    }


def build_offline_vertical_slice_bootstrap(
    inputs: Sequence[str | Path],
    output_dir: str | Path,
    *,
    track: str,
    vehicle: str,
    workspace_root: str | Path,
    explicit_runtime_inputs: Mapping[str, str | Path | None] | None = None,
    input_script: str | Path | None = None,
    interactive: bool = False,
    keyboard: bool = False,
    frames: int | None = None,
    decode_limit_per_archive: int = 0,
    root_consensus_path: str | Path | None = None,
    runtime_shader_admission_path: str | Path | None = None,
    participant_observation_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build offline bootstrap, exact runtime requirements, and launch profile."""
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    bootstrap_dir = out / "runtime-bootstrap"
    requirements_path = out / "runtime_requirements.json"
    profile_path = out / "vertical_slice_profile.json"
    prepare_path = out / "vertical_slice_profile.prepare.json"
    report_path = out / "vertical_slice_bootstrap.json"
    workspace = Path(workspace_root).resolve()
    explicit = dict(explicit_runtime_inputs or {})

    runtime_bootstrap = build_offline_runtime_bootstrap(
        inputs,
        bootstrap_dir,
        track=track,
        vehicle=vehicle,
        decode_limit_per_archive=decode_limit_per_archive,
        root_consensus_path=root_consensus_path,
        runtime_shader_admission_path=runtime_shader_admission_path,
        participant_observation_path=participant_observation_path,
    )
    validated_runtime_inputs = validate_explicit_runtime_inputs(
        workspace_root=workspace,
        explicit_inputs=explicit,
        input_script=input_script,
        interactive=interactive,
        keyboard=keyboard,
    )
    requirements = build_runtime_requirements(
        runtime_bootstrap,
        validated_runtime_inputs=validated_runtime_inputs,
    )
    _write(requirements_path, requirements)

    offline_bootstrap_ready = runtime_bootstrap.get("offline_build_ready") is True
    if offline_bootstrap_ready:
        profile_prepare = build_vertical_slice_profile_prepare(
            requirements,
            workspace_root=workspace,
            profile_path=profile_path,
            explicit_inputs=explicit,
            input_script=input_script,
            interactive=interactive,
            keyboard=keyboard,
            frames=frames,
        )
    else:
        upstream = runtime_bootstrap.get("blocking_reasons") or ["not-ready"]
        profile_prepare = _blocked_profile_prepare(
            workspace_root=workspace,
            profile_path=profile_path,
            reasons=[f"offline-bootstrap:{reason}" for reason in upstream],
        )

    profile_ready = profile_prepare.get("ready") is True
    if profile_ready:
        profile = profile_prepare.get("profile")
        if not isinstance(profile, Mapping):
            raise ValueError("profile prepare reported ready without a profile object")
        _write(profile_path, profile)
    elif profile_path.exists():
        profile_path.unlink()
    _write(prepare_path, profile_prepare)

    blockers: list[str] = []
    if not offline_bootstrap_ready:
        blockers.extend(
            f"offline-bootstrap:{reason}"
            for reason in runtime_bootstrap.get("blocking_reasons") or ["not-ready"]
        )
    elif not profile_ready:
        blockers.extend(
            f"profile:{reason}"
            for reason in profile_prepare.get("blocking_reasons") or ["not-ready"]
        )
    blockers = list(dict.fromkeys(blockers))

    if not offline_bootstrap_ready:
        status = "offline-bootstrap-blocked"
    elif not profile_ready:
        status = "profile-blocked"
    else:
        status = "profile-ready"

    artifacts: dict[str, str | None] = {
        "runtime_bootstrap": str(bootstrap_dir / "runtime_bootstrap.json"),
        "runtime_requirements": str(requirements_path),
        "profile_prepare": str(prepare_path),
        "profile": str(profile_path) if profile_ready else None,
        "launch_plan": None,
    }
    report = {
        "format": FORMAT,
        "version": 1,
        "status": status,
        "ready": profile_ready,
        "offline_bootstrap_ready": offline_bootstrap_ready,
        "profile_ready": profile_ready,
        "launch_plan_ready": False,
        "track": track,
        "vehicle": vehicle,
        "blocking_reasons": blockers,
        "stages": {
            "runtime_bootstrap": runtime_bootstrap,
            "validated_runtime_inputs": validated_runtime_inputs,
            "runtime_requirements": requirements,
            "profile_prepare": profile_prepare,
        },
        "artifacts": artifacts,
        "boundary": {
            "selected_offline_bootstrap_required": True,
            "offline_bootstrap_gate_bypassed": False,
            "runtime_requirements_reused": True,
            "explicit_runtime_inputs_launcher_validated_before_requirement_admission": True,
            "validated_input_path_presence_is_proof": False,
            "missing_runtime_evidence_synthesized": False,
            "explicit_runtime_artifact_substitution_for_offline_failure": False,
            "launcher_validation_performed": False,
            "launcher_validation_still_required": True,
            "runtime_execution_claimed": False,
        },
    }
    _write(report_path, report)
    return report
