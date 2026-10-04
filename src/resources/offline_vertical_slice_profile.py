"""Prepare a native vertical-slice profile from explicit/proven runtime inputs.

This stage only assembles paths. It never promotes missing runtime evidence and
it never replaces the validation performed by tools/run_native_vertical_slice.py.
A runtime requirement may record a prevalidated explicit input for diagnostics;
that origin remains explicit here rather than being relabeled as pipeline proof.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.OfflineNativeVerticalSliceProfilePrepare/1"
REQUIREMENTS_FORMAT = "SHIFT.OfflineNativeRuntimeRequirements/1"
PROFILE_FORMAT = "SHIFT.NativeVerticalSliceProfile/1"
RETAIL_ARCHIVE_ADMISSION_FORMAT = "SHIFT.RetailArchiveIdentityAdmission/1"

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


def _requirements_by_name(requirements: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        str(row.get("name")): row
        for row in (requirements.get("requirements") or [])
        if isinstance(row, Mapping) and row.get("name")
    }


def _resolve_under_workspace(
    workspace_root: Path,
    raw: Any,
    *,
    label: str,
    expect_dir: bool = False,
) -> tuple[Path | None, str | None]:
    text = str(raw or "").strip()
    if not text:
        return None, f"{label}:path-missing"
    value = Path(text)
    resolved = value.resolve() if value.is_absolute() else (workspace_root / value).resolve()
    try:
        relative = resolved.relative_to(workspace_root)
    except ValueError:
        return None, f"{label}:path-escapes-workspace:{text}"
    if expect_dir:
        if not resolved.is_dir():
            return None, f"{label}:directory-not-found:{text}"
    elif not resolved.is_file():
        return None, f"{label}:file-not-found:{text}"
    return relative, None


def build_vertical_slice_profile_prepare(
    requirements: Mapping[str, Any],
    *,
    workspace_root: str | Path,
    profile_path: str | Path,
    explicit_inputs: Mapping[str, str | Path | None] | None = None,
    input_script: str | Path | None = None,
    interactive: bool = False,
    keyboard: bool = False,
    frames: int | None = None,
) -> dict[str, Any]:
    """Assemble a profile only from exact requirements artifacts or explicit paths."""
    if requirements.get("format") != REQUIREMENTS_FORMAT:
        raise ValueError(f"requirements must be {REQUIREMENTS_FORMAT}")

    root = Path(workspace_root).resolve()
    profile_path = Path(profile_path).resolve()
    explicit = dict(explicit_inputs or {})
    rows = _requirements_by_name(requirements)
    blockers: list[str] = []
    profile_inputs: dict[str, str] = {}
    auto_filled: list[str] = []
    explicit_filled: list[str] = []

    if not root.is_dir():
        blockers.append(f"workspace-root:not-directory:{root}")

    retail_identity_required = (
        requirements.get("retail_archive_identity_required") is True
    )
    retail_identity_relative: Path | None = None
    retail_track = str(requirements.get("track") or "").strip()
    retail_vehicle = str(requirements.get("vehicle") or "").strip()
    if retail_identity_required:
        if requirements.get("retail_archive_identity_ready") is not True:
            blockers.append("retail-archive-identity:not-ready")
        if not retail_track:
            blockers.append("retail-archive-identity:track-missing")
        if not retail_vehicle:
            blockers.append("retail-archive-identity:vehicle-missing")
        relative, error = _resolve_under_workspace(
            root,
            requirements.get("retail_archive_identity_admission"),
            label="retail-archive-identity-admission",
        )
        if error:
            blockers.append(error)
        else:
            retail_identity_relative = relative

    for name in PROFILE_INPUTS:
        row = rows.get(name)
        if row is None:
            blockers.append(f"requirements:missing-row:{name}")
            continue

        # A validated explicit input is READY for diagnostics but is still an
        # explicit user/runtime input, not a pipeline-proven artifact. Keep it
        # on the explicit path so provenance and conflict semantics are honest.
        artifact_origin = str(row.get("artifact_origin") or "")
        proven_artifact = None
        if (
            row.get("satisfied") is True
            and artifact_origin != "explicit-validated"
        ):
            text = str(row.get("artifact") or "").strip()
            if text:
                proven_artifact = text

        supplied = explicit.get(name)
        supplied_text = str(supplied or "").strip() or None
        chosen = proven_artifact or supplied_text
        if proven_artifact is not None and supplied_text is not None:
            proven_resolved = (
                Path(proven_artifact).resolve()
                if Path(proven_artifact).is_absolute()
                else (root / proven_artifact).resolve()
            )
            supplied_resolved = (
                Path(supplied_text).resolve()
                if Path(supplied_text).is_absolute()
                else (root / supplied_text).resolve()
            )
            if proven_resolved != supplied_resolved:
                blockers.append(f"{name}:explicit-conflicts-with-proven-artifact")
                continue
            chosen = proven_artifact

        if chosen is None:
            blockers.append(f"{name}:explicit-input-required")
            continue

        relative, error = _resolve_under_workspace(
            root,
            chosen,
            label=name,
            expect_dir=name == "scene_set",
        )
        if error:
            blockers.append(error)
            continue
        assert relative is not None
        profile_inputs[name] = relative.as_posix()
        if proven_artifact is not None:
            auto_filled.append(name)
        else:
            explicit_filled.append(name)

    selected_modes = int(bool(input_script)) + int(interactive) + int(keyboard)
    if selected_modes != 1:
        blockers.append("input-mode:choose-exactly-one-of-script-interactive-keyboard")

    input_script_relative: str | None = None
    if input_script is not None:
        relative, error = _resolve_under_workspace(
            root,
            input_script,
            label="input-script",
        )
        if error:
            blockers.append(error)
        elif relative is not None:
            input_script_relative = relative.as_posix()

    if interactive and frames is not None:
        blockers.append("interactive:frames-not-allowed")
    if keyboard and frames is None:
        blockers.append("keyboard:explicit-frames-required")
    if frames is not None:
        if isinstance(frames, bool) or not isinstance(frames, int) or frames <= 0:
            blockers.append("frames:positive-integer-required")

    blockers = list(dict.fromkeys(blockers))
    profile: dict[str, Any] | None = None
    if not blockers:
        workspace_value = os.path.relpath(root, profile_path.parent)
        profile = {
            "format": PROFILE_FORMAT,
            "version": 1,
            "workspace_root": workspace_value,
            **profile_inputs,
            "persist_post_solve_body_state": True,
        }
        if retail_identity_required:
            assert retail_identity_relative is not None
            profile["track"] = retail_track
            profile["vehicle"] = retail_vehicle
            profile["retail_archive_identity_admission"] = (
                retail_identity_relative.as_posix()
            )
        if input_script_relative is not None:
            profile["input_script"] = input_script_relative
            if frames is not None:
                profile["frames"] = frames
        elif interactive:
            profile["interactive"] = True
        else:
            profile["frames"] = frames

    return {
        "format": FORMAT,
        "version": 1,
        "status": "profile-complete" if profile is not None else "blocked",
        "ready": profile is not None,
        "profile": profile,
        "track": requirements.get("track"),
        "vehicle": requirements.get("vehicle"),
        "workspace_root": str(root),
        "profile_path": str(profile_path),
        "auto_filled_inputs": auto_filled,
        "explicit_filled_inputs": explicit_filled,
        "blocking_reasons": blockers,
        "boundary": {
            "requirements_artifact_identity_is_authoritative": True,
            "validated_explicit_requirement_stays_explicit": True,
            "explicit_override_of_proven_artifact_allowed": False,
            "retail_archive_identity_required": retail_identity_required,
            "retail_archive_identity_admission_format": (
                RETAIL_ARCHIVE_ADMISSION_FORMAT
            ),
            "retail_archive_identity_propagated": (
                retail_identity_required
                and retail_identity_relative is not None
                and requirements.get("retail_archive_identity_ready") is True
            ),
            "retail_archive_identity_revalidated_by_profile_builder": False,
            "missing_evidence_synthesized": False,
            "path_outside_workspace_allowed": False,
            "input_mode_invented": False,
            "camera_or_body_feedback_generated": False,
            "static_scene_promoted_to_runtime_scene": False,
            "launcher_validation_performed": False,
            "launcher_validation_still_required": True,
            "runtime_execution_claimed": False,
        },
    }
