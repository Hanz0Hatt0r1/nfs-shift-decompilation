"""Prepare a resource-pipeline profile that names one playable-scene bootstrap.

This stage transports paths only.  It deliberately delegates all existing
resource/runtime admission to offline_vertical_slice_profile and leaves playable
scene provenance to the dedicated launcher wrapper.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from offline_vertical_slice_profile import (
    build_vertical_slice_profile_prepare,
    _resolve_under_workspace,
)

FORMAT = "SHIFT.OfflinePlayablePipelineProfilePrepare/1"


def build_playable_pipeline_profile_prepare(
    requirements: Mapping[str, Any],
    *,
    workspace_root: str | Path,
    profile_path: str | Path,
    explicit_inputs: Mapping[str, str | Path | None] | None,
    resource_pipeline: str | Path,
    playable_scene_bootstrap: str | Path,
    input_script: str | Path | None = None,
    interactive: bool = False,
    keyboard: bool = False,
    frames: int | None = None,
) -> dict[str, Any]:
    root = Path(workspace_root).resolve()
    base = build_vertical_slice_profile_prepare(
        requirements,
        workspace_root=root,
        profile_path=profile_path,
        explicit_inputs=explicit_inputs,
        resource_pipeline=resource_pipeline,
        input_script=input_script,
        interactive=interactive,
        keyboard=keyboard,
        frames=frames,
    )

    blockers = [str(reason) for reason in base.get("blocking_reasons") or []]
    playable_relative, playable_error = _resolve_under_workspace(
        root,
        playable_scene_bootstrap,
        label="playable-scene-bootstrap",
    )
    if playable_error:
        blockers.append(playable_error)

    resource_pipeline_ready = bool(base.get("resource_pipeline"))
    if not resource_pipeline_ready:
        blockers.append("playable-pipeline-profile:resource-pipeline-required")

    blockers = list(dict.fromkeys(blockers))
    profile: dict[str, Any] | None = None
    if base.get("ready") is True and playable_relative is not None and not blockers:
        raw_profile = base.get("profile")
        if not isinstance(raw_profile, Mapping):
            blockers.append("playable-pipeline-profile:base-ready-without-profile")
        else:
            profile = dict(raw_profile)
            profile["playable_scene_bootstrap"] = playable_relative.as_posix()

    return {
        "format": FORMAT,
        "version": 1,
        "status": "profile-complete" if profile is not None else "blocked",
        "ready": profile is not None,
        "profile": profile,
        "workspace_root": str(root),
        "profile_path": str(Path(profile_path).resolve()),
        "resource_pipeline": base.get("resource_pipeline"),
        "playable_scene_bootstrap": (
            playable_relative.as_posix() if playable_relative is not None else None
        ),
        "blocking_reasons": blockers,
        "base_profile_prepare": base,
        "boundary": {
            "base_resource_pipeline_profile_prepare_required": True,
            "base_resource_pipeline_profile_prepare_ready": base.get("ready") is True,
            "playable_scene_bootstrap_workspace_local_required": True,
            "playable_scene_bootstrap_path_presence_is_provenance": False,
            "playable_scene_provenance_validation_deferred_to_launcher": True,
            "resource_pipeline_physics_or_participant_revalidated": False,
            "runtime_execution_claimed": False,
        },
    }
