#!/usr/bin/env python3
"""Build the current fail-closed Silverstone + BMW native Linux playable slice.

This entry point deliberately reuses tools/bootstrap_native_vertical_slice.py for
all existing resource, renderer-evidence, runtime-input and profile behavior. It
then inserts the Phase 644 corpus -> BMW material -> Phase 643 composite-scene
stage and rebuilds the runtime requirements/profile against that composite scene.

Phase 653 additionally accepts a ready Phase 650 capture-result bundle and uses
the existing Phase 652 exact feedback resolver to derive the canonical sibling
raw capture/root. Phase 655 can also resolve one canonical
``SHIFT.PEImageEvidence/1`` from the existing renderer report bundle when no
explicit PE selector is supplied. The full renderer re-attribution chain remains
unchanged.

The historical track-only bootstrap remains unchanged. This command is the
playable-specific orchestration path and therefore owns scene-set production;
passing --scene-set is rejected rather than silently replacing the generated
track+vehicle scene.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
for path in (TOOLS, ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

# Importing the existing bootstrap installs the repository src/* search paths.
from bootstrap_native_vertical_slice import build_parser as build_base_parser
from bootstrap_native_vertical_slice import main as base_main
from bootstrap_native_vertical_slice_from_capture_result import (
    resolve_capture_feedback_input,
)
from native_playable_scene_bootstrap import build_native_playable_scene_bootstrap
from offline_runtime_requirements import build_runtime_requirements
from offline_vertical_slice_profile import build_vertical_slice_profile_prepare
from resolve_playable_renderer_pe_evidence import (
    resolve_renderer_pe_evidence_from_bundles,
)
from run_native_vertical_slice import ProfileError, build_launch_plan
from runtime_input_validation import validate_explicit_runtime_inputs


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_map(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object expected: {path}")
    return value


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if value))


def _without_flag(argv: list[str], flag: str) -> list[str]:
    return [value for value in argv if value != flag]


def _without_option(argv: list[str], option: str) -> list[str]:
    """Remove one ordinary option/value pair, including --option=value form."""
    result: list[str] = []
    index = 0
    while index < len(argv):
        value = argv[index]
        if value == option:
            if index + 1 >= len(argv):
                raise ValueError(f"missing value for {option}")
            index += 2
            continue
        if value.startswith(option + "="):
            index += 1
            continue
        result.append(value)
        index += 1
    return result


def _runtime_bootstrap(report: Mapping[str, Any]) -> Mapping[str, Any] | None:
    stages = report.get("stages") or {}
    value = stages.get("runtime_bootstrap") if isinstance(stages, Mapping) else None
    if isinstance(value, Mapping):
        return value
    artifacts = report.get("artifacts") or {}
    raw = str(artifacts.get("runtime_bootstrap") or "") if isinstance(artifacts, Mapping) else ""
    if not raw:
        return None
    try:
        return _load_map(Path(raw))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


def _track_scene_set(report: Mapping[str, Any]) -> str | None:
    stages = report.get("stages") or {}
    handoff = stages.get("renderer_native_scene_handoff") if isinstance(stages, Mapping) else None
    if not isinstance(handoff, Mapping):
        return None
    if handoff.get("ready") is not True or handoff.get("scene_set_ready") is not True:
        return None
    artifacts = handoff.get("artifacts") or {}
    if not isinstance(artifacts, Mapping):
        return None
    value = str(artifacts.get("scene_set_dir") or "").strip()
    return value or None


def _explicit_inputs(args: Any, scene_set: str) -> dict[str, str | Path | None]:
    return {
        "scene_set": scene_set,
        "camera_state": args.camera_state,
        "physics_manifest": args.physics_manifest,
        "participant_boundary": args.participant_boundary,
        "solver_frame": args.solver_frame,
        "generated_body_constraint_frame": args.generated_body_constraint_frame,
        "constraint_sample_relation_frame": args.constraint_sample_relation_frame,
        "constraint_relation_reset_frame": args.constraint_relation_reset_frame,
        "post_solve_projection": args.post_solve_projection,
    }


def _blocked_status(report: Mapping[str, Any]) -> str:
    if report.get("offline_bootstrap_ready") is not True:
        return "offline-bootstrap-blocked"
    if report.get("renderer_evidence_ready") is not True:
        return "renderer-evidence-blocked"
    if report.get("renderer_native_scene_ready") is not True:
        return "renderer-native-scene-blocked"
    return "playable-scene-blocked"


def main(argv: list[str] | None = None) -> int:
    values = list(sys.argv[1:] if argv is None else argv)
    parser = build_base_parser()
    parser.add_argument(
        "--renderer-capture-result",
        help=(
            "ready Phase 650 external-sampler capture-result bundle; derives "
            "the exact sibling renderer capture JSONL/root via Phase 652"
        ),
    )
    args = parser.parse_args(values)
    if args.scene_set:
        parser.error(
            "bootstrap_playable_linux_slice owns the composite scene set; "
            "do not pass --scene-set"
        )

    capture_feedback: Mapping[str, Any] | None = None
    pe_bundle_resolution: Mapping[str, Any] | None = None
    base_values = list(values)
    if args.renderer_capture_result:
        if args.renderer_capture_jsonl or args.renderer_capture_root:
            parser.error(
                "--renderer-capture-result owns the exact renderer capture "
                "JSONL/root; do not also pass --renderer-capture-jsonl or "
                "--renderer-capture-root"
            )
        try:
            capture_feedback = resolve_capture_feedback_input(
                args.renderer_capture_result
            )
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            parser.error(
                "renderer capture result is not a ready exact Phase 650 bundle: "
                f"{type(exc).__name__}:{exc}"
            )
        base_values = _without_option(base_values, "--renderer-capture-result")
        base_values.extend([
            "--renderer-capture-jsonl",
            str(capture_feedback["capture_jsonl"]),
            "--renderer-capture-root",
            str(capture_feedback["capture_root"]),
        ])
        # Keep the parsed playable-layer values aligned with the exact inputs
        # that the lower-level bootstrap will consume.
        args.renderer_capture_jsonl = str(capture_feedback["capture_jsonl"])
        args.renderer_capture_root = str(capture_feedback["capture_root"])

    if not args.renderer_capture_jsonl:
        parser.error(
            "playable scene composition requires renderer evidence through "
            "either --renderer-capture-result or --renderer-capture-jsonl"
        )

    if not args.renderer_pe_evidence and not args.renderer_pe_image:
        if not args.renderer_bundle:
            parser.error(
                "playable renderer evidence requires either an explicit "
                "--renderer-pe-evidence/--renderer-pe-image selector or a "
                "--renderer-bundle containing one exact SHIFT.PEImageEvidence/1"
            )
        try:
            pe_bundle_resolution = resolve_renderer_pe_evidence_from_bundles(
                list(args.renderer_bundle),
                output_dir=(
                    Path(args.output).expanduser().resolve()
                    / "renderer-evidence"
                    / "bundle-pe-input"
                ),
                max_json_bytes=args.renderer_max_json_bytes,
            )
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            parser.error(
                "renderer bundle PE evidence is not exactly resolvable: "
                f"{type(exc).__name__}:{exc}"
            )
        pe_path = str(pe_bundle_resolution["path"])
        base_values.extend(["--renderer-pe-evidence", pe_path])
        args.renderer_pe_evidence = pe_path

    # A launch plan produced before Phase 644 would point at the track-only scene.
    # Defer launcher validation until the composite scene/profile is rebuilt.
    base_argv = _without_flag(base_values, "--validate-launch-plan")
    base_main(base_argv)

    out = Path(args.output).resolve()
    report_path = out / "vertical_slice_bootstrap.json"
    report = _load_map(report_path)
    artifacts = dict(report.get("artifacts") or {})
    stages = dict(report.get("stages") or {})
    boundary = dict(report.get("boundary") or {})
    blockers = [
        str(reason)
        for reason in report.get("blocking_reasons") or []
        if not str(reason).startswith("profile:")
        and not str(reason).startswith("launch-plan:")
    ]

    if capture_feedback is not None:
        stages["renderer_capture_feedback"] = dict(capture_feedback)
        artifacts["renderer_capture_result"] = str(
            Path(args.renderer_capture_result).expanduser().resolve()
        )
    if pe_bundle_resolution is not None:
        stages["renderer_pe_bundle_resolution"] = dict(pe_bundle_resolution)
        artifacts["renderer_pe_evidence"] = pe_bundle_resolution.get("path")
        artifacts["renderer_pe_bundle_index"] = pe_bundle_resolution.get(
            "bundle_index"
        )

    boundary.update({
        "playable_linux_scene_composition_requested": True,
        "playable_linux_scene_uses_same_resource_corpus": True,
        "manual_vehicle_material_slice_handoff_required": False,
        "manual_vehicle_bff_path_handoff_required": False,
        "manual_renderer_capture_path_handoff_required": False,
        "manual_renderer_pe_path_handoff_required_when_bundle_has_exact_pe": False,
        "renderer_pe_bundle_resolution_used": pe_bundle_resolution is not None,
        "renderer_pe_bundle_selection_uses_embedded_format_and_canonical_json_sha256": (
            pe_bundle_resolution is not None
        ),
        "renderer_pe_bundle_filename_is_selection_authority": False,
        "renderer_pe_bundle_archive_order_is_selection_authority": False,
        "phase652_capture_feedback_consumed": capture_feedback is not None,
        "renderer_capture_result_is_render_admission": False,
        "track_only_profile_is_playable_profile": False,
        "phase700_runtime_pose_handoff_consumed": False,
        "dynamic_vehicle_world_transform_claimed": False,
        "runtime_execution_claimed": False,
    })

    track_scene = _track_scene_set(report)
    playable: Mapping[str, Any] | None = None
    if track_scene is None:
        blockers.append("playable-scene:renderer-native-track-scene-not-ready")
    else:
        try:
            playable = build_native_playable_scene_bootstrap(
                args.inputs,
                track_scene,
                out / "playable-scene",
                vehicle=args.vehicle,
                validator=args.renderer_validator,
            )
        except Exception as exc:
            blockers.append(
                f"playable-scene:failed:{type(exc).__name__}:{exc}"
            )
        else:
            if playable.get("ready") is not True:
                blockers.extend(
                    "playable-scene:" + str(reason)
                    for reason in playable.get("blocking_reasons") or ["not-ready"]
                )

    playable_ready = isinstance(playable, Mapping) and playable.get("ready") is True
    if isinstance(playable, Mapping):
        stages["playable_scene_bootstrap"] = dict(playable)
        playable_artifacts = playable.get("artifacts") or {}
        if isinstance(playable_artifacts, Mapping):
            artifacts["playable_scene_bootstrap"] = str(
                out / "playable-scene" / "playable_scene_bootstrap.json"
            )
            artifacts["playable_scene_set"] = playable_artifacts.get("scene_set_dir")
            artifacts["vehicle_material_admission"] = playable_artifacts.get(
                "vehicle_material_admission"
            )
            artifacts["vehicle_material_slice_set"] = playable_artifacts.get(
                "vehicle_material_slice_set"
            )
    else:
        stages["playable_scene_bootstrap"] = None
        artifacts["playable_scene_bootstrap"] = None
        artifacts["playable_scene_set"] = None
        artifacts["vehicle_material_admission"] = None
        artifacts["vehicle_material_slice_set"] = None

    report["playable_scene_requested"] = True
    report["playable_scene_ready"] = playable_ready
    report["stages"] = stages
    report["artifacts"] = artifacts
    report["boundary"] = boundary

    if not playable_ready:
        report["status"] = _blocked_status(report)
        report["ready"] = False
        report["profile_ready"] = False
        report["launch_plan_ready"] = False
        artifacts["profile"] = None
        artifacts["launch_plan"] = None
        for stale in (
            out / "vertical_slice_profile.json",
            out / "launch_plan.json",
        ):
            if stale.exists():
                stale.unlink()
        report["blocking_reasons"] = _unique(blockers)
        _write(report_path, report)
        print(json.dumps({
            "format": report.get("format"),
            "status": report["status"],
            "ready": False,
            "playable_scene_ready": False,
            "blocking_reasons": report["blocking_reasons"],
        }, ensure_ascii=False, indent=2))
        return 2

    scene_set = str((playable.get("artifacts") or {}).get("scene_set_dir") or "")
    runtime_bootstrap = _runtime_bootstrap(report)
    if not scene_set or runtime_bootstrap is None:
        blockers.append("playable-scene:profile-refresh-input-missing")
        report["status"] = "playable-scene-blocked"
        report["ready"] = False
        report["profile_ready"] = False
        report["launch_plan_ready"] = False
        report["blocking_reasons"] = _unique(blockers)
        _write(report_path, report)
        return 2

    explicit = _explicit_inputs(args, scene_set)
    validated = validate_explicit_runtime_inputs(
        workspace_root=Path(args.workspace_root).resolve(),
        explicit_inputs=explicit,
        input_script=args.input_script,
        interactive=args.interactive,
        keyboard=args.keyboard,
    )
    scene_validated = validated.get("scene_set")
    if isinstance(scene_validated, dict):
        scene_validated["source"] = "Phase 644 generated playable scene"

    requirements = build_runtime_requirements(
        runtime_bootstrap,
        validated_runtime_inputs=validated,
    )
    requirements_path = out / "runtime_requirements.json"
    profile_path = out / "vertical_slice_profile.json"
    prepare_path = out / "vertical_slice_profile.prepare.json"
    _write(requirements_path, requirements)

    prepare = build_vertical_slice_profile_prepare(
        requirements,
        workspace_root=args.workspace_root,
        profile_path=profile_path,
        explicit_inputs=explicit,
        input_script=args.input_script,
        interactive=args.interactive,
        keyboard=args.keyboard,
        frames=args.frames,
    )
    _write(prepare_path, prepare)
    profile_ready = prepare.get("ready") is True
    if profile_ready:
        profile = prepare.get("profile")
        if not isinstance(profile, Mapping):
            raise ValueError("ready playable profile prepare has no profile object")
        _write(profile_path, profile)
        artifacts["profile"] = str(profile_path)
    else:
        if profile_path.exists():
            profile_path.unlink()
        artifacts["profile"] = None
        blockers.extend(
            "profile:" + str(reason)
            for reason in prepare.get("blocking_reasons") or ["not-ready"]
        )

    stages["validated_runtime_inputs"] = validated
    stages["runtime_requirements"] = requirements
    stages["profile_prepare"] = prepare
    artifacts["runtime_requirements"] = str(requirements_path)
    artifacts["profile_prepare"] = str(prepare_path)
    report["stages"] = stages
    report["artifacts"] = artifacts
    report["profile_ready"] = profile_ready
    report["ready"] = profile_ready
    report["launch_plan_ready"] = False

    launch_plan_path = out / "launch_plan.json"
    boundary["launcher_validation_requested"] = bool(args.validate_launch_plan)
    boundary["launcher_validation_performed"] = False
    if profile_ready and args.validate_launch_plan:
        boundary["launcher_validation_performed"] = True
        try:
            launch_plan = build_launch_plan(
                profile_path,
                runtime=args.runtime,
                validation=args.validation,
            )
            if not isinstance(launch_plan, dict) or launch_plan.get("ready") is not True:
                raise ValueError("launcher did not return a ready launch plan")
        except (ProfileError, OSError, ValueError) as exc:
            blockers.append(f"launch-plan:{type(exc).__name__}:{exc}")
            report["status"] = "launch-plan-blocked"
            report["ready"] = False
            report["launch_plan_ready"] = False
            artifacts["launch_plan"] = None
            if launch_plan_path.exists():
                launch_plan_path.unlink()
        else:
            _write(launch_plan_path, launch_plan)
            artifacts["launch_plan"] = str(launch_plan_path)
            report["status"] = "launch-plan-ready"
            report["ready"] = True
            report["launch_plan_ready"] = True
    elif profile_ready:
        report["status"] = "profile-ready"
        report["ready"] = True
        artifacts["launch_plan"] = None
        if launch_plan_path.exists():
            launch_plan_path.unlink()
    else:
        report["status"] = "profile-blocked"
        report["ready"] = False
        artifacts["launch_plan"] = None
        if launch_plan_path.exists():
            launch_plan_path.unlink()

    boundary["phase643_composite_scene_consumed"] = playable_ready
    boundary["generated_playable_scene_launcher_validated"] = (
        bool(args.validate_launch_plan) and report.get("launch_plan_ready") is True
    )
    report["boundary"] = boundary
    report["artifacts"] = artifacts
    report["blocking_reasons"] = _unique(blockers)
    _write(report_path, report)

    print(json.dumps({
        "format": report.get("format"),
        "status": report["status"],
        "ready": report["ready"],
        "playable_scene_ready": report["playable_scene_ready"],
        "profile_ready": report["profile_ready"],
        "launch_plan_ready": report["launch_plan_ready"],
        "scene_set": artifacts.get("playable_scene_set"),
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())