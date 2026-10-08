#!/usr/bin/env python3
"""Build a fail-closed native vertical-slice profile directly from SHIFT resources.

Optional historical-capture renderer evidence can be regenerated in the same
command. When enabled, the renderer path consumes the exact runtime-bootstrap
artifact created earlier in this invocation. If no explicit scene-set is
supplied, the same command then attempts the existing Phase 574 -> 585 runtime
scene chain. Phase 641 additionally exhausts existing Phase 591/590/592 scene
instance and external-sampler evidence before leaving a Phase 580/585 blocker.
When Phase 641 proves an exact missing sampler snapshot frontier, Phase 643
materializes the existing Phase 642 selective Wine capture plan automatically.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TOOLS = ROOT / "tools"
if SRC.is_dir():
    paths = [SRC]
    paths.extend(sorted(
        (path for path in SRC.rglob("*") if path.is_dir()),
        key=lambda path: (len(path.parts), str(path)),
    ))
    for path in reversed(paths):
        value = str(path)
        if value not in sys.path:
            sys.path.insert(0, value)
for path in (ROOT, TOOLS):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from materialize_renderer_native_scene_capture_handoff import (
    materialize_renderer_native_scene_capture_handoff as materialize_renderer_native_scene_handoff,
)
from offline_runtime_requirements import build_runtime_requirements
from offline_vertical_slice_bootstrap import build_offline_vertical_slice_bootstrap
from offline_vertical_slice_profile import build_vertical_slice_profile_prepare
from phase641_external_sampler_capture_plan import build_capture_plan
from run_native_vertical_slice import ProfileError, build_launch_plan
from run_silverstone_renderer_source_bootstrap_production import (
    run_source_bootstrap_production,
)


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_map(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"JSON object expected: {path}")
    return value


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if value))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", help="BFF, ZIP, or directory inputs")
    parser.add_argument("-o", "--output", required=True, help="output directory")
    parser.add_argument("--track", required=True, help="exact track archive stem")
    parser.add_argument("--vehicle", required=True, help="exact vehicle archive stem")
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--decode-limit-per-archive", type=int, default=0)
    parser.add_argument("--root-consensus")
    parser.add_argument("--runtime-shader-admission")
    parser.add_argument("--participant-observation")
    parser.add_argument("--resource-pipeline")
    for option in (
        "scene-set",
        "camera-state",
        "physics-manifest",
        "participant-boundary",
        "solver-frame",
        "generated-body-constraint-frame",
        "constraint-sample-relation-frame",
        "constraint-relation-reset-frame",
        "post-solve-projection",
    ):
        parser.add_argument("--" + option)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--input-script")
    mode.add_argument("--interactive", action="store_true")
    mode.add_argument("--keyboard", action="store_true")
    parser.add_argument("--frames", type=int)

    renderer = parser.add_argument_group(
        "offline renderer evidence",
        "regenerate renderer evidence from the existing historical D3D9 capture",
    )
    renderer.add_argument(
        "--renderer-capture-jsonl",
        help="historical raw D3D9 capture; enables unified renderer evidence",
    )
    renderer.add_argument(
        "--renderer-capture-root",
        help=(
            "root containing existing PPM texture snapshots; defaults to the "
            "directory containing --renderer-capture-jsonl"
        ),
    )
    renderer_pe = renderer.add_mutually_exclusive_group()
    renderer_pe.add_argument("--renderer-pe-evidence")
    renderer_pe.add_argument("--renderer-pe-image")
    renderer.add_argument(
        "--renderer-bundle",
        action="append",
        default=[],
        help="optional historical renderer report bundle for exact cross-check only",
    )
    renderer.add_argument("--renderer-compact-evidence")
    renderer.add_argument(
        "--renderer-no-compact-crosscheck",
        action="store_true",
    )
    renderer.add_argument(
        "--renderer-max-json-bytes",
        type=int,
        default=128 * 1024 * 1024,
    )
    renderer.add_argument("--renderer-environment-cube-dds")
    renderer.add_argument("--renderer-external-sampler-snapshots")
    renderer.add_argument("--renderer-external-sampler-cube-snapshots")
    renderer.add_argument("--renderer-validator")

    parser.add_argument("--validate-launch-plan", action="store_true")
    parser.add_argument(
        "--runtime",
        default="native_runtime/build/shift_runtime",
        help="runtime executable used only for launch-plan validation",
    )
    parser.add_argument("--validation", action="store_true")
    return parser


def _renderer_requested(args: argparse.Namespace) -> bool:
    return bool(
        args.renderer_capture_jsonl
        or args.renderer_capture_root
        or args.renderer_pe_evidence
        or args.renderer_pe_image
        or args.renderer_bundle
        or args.renderer_compact_evidence
        or args.renderer_no_compact_crosscheck
        or args.renderer_environment_cube_dds
        or args.renderer_external_sampler_snapshots
        or args.renderer_external_sampler_cube_snapshots
        or args.renderer_validator
    )


def _validate_renderer_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> bool:
    requested = _renderer_requested(args)
    pe_count = int(bool(args.renderer_pe_evidence)) + int(bool(args.renderer_pe_image))
    if requested and not args.renderer_capture_jsonl:
        parser.error("renderer evidence requires --renderer-capture-jsonl")
    if args.renderer_capture_jsonl and pe_count != 1:
        parser.error(
            "--renderer-capture-jsonl requires exactly one of "
            "--renderer-pe-evidence or --renderer-pe-image"
        )
    if args.renderer_max_json_bytes <= 0:
        parser.error("--renderer-max-json-bytes must be positive")
    return requested


def _renderer_manifest_path(out: Path) -> Path:
    return (
        out
        / "renderer-evidence"
        / "silverstone_renderer_source_bootstrap_production_run.json"
    )


def _scene_handoff_path(out: Path) -> Path:
    return out / "renderer-native-scene" / "renderer_native_scene_handoff.json"


def _capture_plan_path(out: Path) -> Path:
    return out / "renderer-native-scene" / "external_sampler_capture_plan.json"


def _refresh_runtime_profile(
    report: dict[str, Any],
    *,
    out: Path,
    workspace_root: str | Path,
    explicit: Mapping[str, str | Path | None],
    runtime_scene_handoff: Mapping[str, Any] | None,
    input_script: str | Path | None,
    interactive: bool,
    keyboard: bool,
    frames: int | None,
) -> list[str]:
    """Rebuild requirements/profile after renderer scene evidence changes."""
    stages = dict(report.get("stages") or {})
    artifacts = dict(report.get("artifacts") or {})
    runtime_bootstrap = stages.get("runtime_bootstrap")
    if not isinstance(runtime_bootstrap, Mapping):
        raw = str(artifacts.get("runtime_bootstrap") or "").strip()
        if not raw:
            return ["profile-refresh:runtime-bootstrap-missing"]
        try:
            runtime_bootstrap = _load_map(Path(raw))
        except Exception as exc:
            return [f"profile-refresh:runtime-bootstrap-unreadable:{type(exc).__name__}:{exc}"]

    validated_runtime_inputs = stages.get("validated_runtime_inputs")
    if not isinstance(validated_runtime_inputs, Mapping):
        validated_runtime_inputs = None
    requirements = build_runtime_requirements(
        runtime_bootstrap,
        runtime_scene_handoff=runtime_scene_handoff,
        validated_runtime_inputs=validated_runtime_inputs,
    )
    requirements_path = Path(
        str(artifacts.get("runtime_requirements") or (out / "runtime_requirements.json"))
    )
    profile_path = out / "vertical_slice_profile.json"
    prepare_path = Path(
        str(artifacts.get("profile_prepare") or (out / "vertical_slice_profile.prepare.json"))
    )
    _write(requirements_path, requirements)

    prepare = build_vertical_slice_profile_prepare(
        requirements,
        workspace_root=workspace_root,
        profile_path=profile_path,
        explicit_inputs=explicit,
        input_script=input_script,
        interactive=interactive,
        keyboard=keyboard,
        frames=frames,
    )
    _write(prepare_path, prepare)
    profile_ready = prepare.get("ready") is True
    if profile_ready:
        profile = prepare.get("profile")
        if not isinstance(profile, Mapping):
            return ["profile-refresh:ready-without-profile"]
        _write(profile_path, profile)
        artifacts["profile"] = str(profile_path)
    else:
        artifacts["profile"] = None
        if profile_path.exists():
            profile_path.unlink()

    artifacts["runtime_requirements"] = str(requirements_path)
    artifacts["profile_prepare"] = str(prepare_path)
    stages["runtime_requirements"] = requirements
    stages["profile_prepare"] = prepare
    report["artifacts"] = artifacts
    report["stages"] = stages
    report["profile_ready"] = profile_ready
    report["ready"] = profile_ready
    report["status"] = "profile-ready" if profile_ready else "profile-blocked"
    return [
        f"profile:{reason}"
        for reason in prepare.get("blocking_reasons") or []
    ]


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.decode_limit_per_archive < 0:
        parser.error("--decode-limit-per-archive must be non-negative")
    renderer_requested = _validate_renderer_args(parser, args)
    resource_pipeline_requested = bool(str(args.resource_pipeline or "").strip())
    if resource_pipeline_requested:
        overlaps = [
            option
            for option, value in (
                ("--scene-set", args.scene_set),
                ("--physics-manifest", args.physics_manifest),
                ("--participant-boundary", args.participant_boundary),
            )
            if value not in (None, "")
        ]
        if overlaps:
            parser.error(
                "--resource-pipeline cannot be combined with " + ", ".join(overlaps)
            )
    renderer_capture_root = None
    if args.renderer_capture_jsonl:
        renderer_capture_root = (
            Path(args.renderer_capture_root).expanduser()
            if args.renderer_capture_root
            else Path(args.renderer_capture_jsonl).expanduser().parent
        )

    explicit = {
        "scene_set": args.scene_set,
        "camera_state": args.camera_state,
        "physics_manifest": args.physics_manifest,
        "participant_boundary": args.participant_boundary,
        "solver_frame": args.solver_frame,
        "generated_body_constraint_frame": args.generated_body_constraint_frame,
        "constraint_sample_relation_frame": args.constraint_sample_relation_frame,
        "constraint_relation_reset_frame": args.constraint_relation_reset_frame,
        "post_solve_projection": args.post_solve_projection,
    }
    report = build_offline_vertical_slice_bootstrap(
        args.inputs,
        args.output,
        track=args.track,
        vehicle=args.vehicle,
        workspace_root=args.workspace_root,
        explicit_runtime_inputs=explicit,
        resource_pipeline=args.resource_pipeline,
        input_script=args.input_script,
        interactive=args.interactive,
        keyboard=args.keyboard,
        frames=args.frames,
        decode_limit_per_archive=args.decode_limit_per_archive,
        root_consensus_path=args.root_consensus,
        runtime_shader_admission_path=args.runtime_shader_admission,
        participant_observation_path=args.participant_observation,
    )
    report = dict(report)
    out = Path(args.output).resolve()
    report_path = out / "vertical_slice_bootstrap.json"
    launch_plan_path = out / "launch_plan.json"
    renderer_dir = out / "renderer-evidence"
    scene_handoff_dir = out / "renderer-native-scene"
    capture_plan_path = _capture_plan_path(out)

    boundary = dict(report.get("boundary") or {})
    boundary["launcher_validation_requested"] = bool(args.validate_launch_plan)
    boundary["renderer_evidence_requested"] = renderer_requested
    boundary["renderer_uses_selected_runtime_bootstrap"] = renderer_requested
    boundary["manual_resource_to_renderer_handoff_required"] = False
    boundary["renderer_bundle_is_selection_authority"] = False
    boundary["renderer_missing_evidence_synthesized"] = False
    boundary["renderer_evidence_ready_is_runtime_render_admission"] = False
    boundary["renderer_scene_handoff_uses_existing_phase574_to_585_chain"] = True
    boundary["existing_capture_external_sampler_completion_enabled"] = renderer_requested
    boundary["renderer_capture_root_is_identity_proof"] = False
    boundary["runtime_requirements_refreshed_only_after_renderer_scene_attempt"] = True
    boundary["validated_runtime_input_admission_preserved_across_renderer_refresh"] = True
    boundary["phase642_capture_plan_materialization_enabled"] = renderer_requested
    boundary["generic_renderer_recapture_inferred"] = False
    boundary["renderer_capture_execution_claimed"] = False
    boundary["resource_pipeline_selected"] = resource_pipeline_requested
    boundary["resource_pipeline_has_scene_authority"] = resource_pipeline_requested
    boundary["renderer_scene_handoff_suppressed_by_resource_pipeline"] = (
        renderer_requested and resource_pipeline_requested
    )
    report["boundary"] = boundary

    artifacts = dict(report.get("artifacts") or {})
    stages = dict(report.get("stages") or {})
    blockers = list(report.get("blocking_reasons") or [])
    renderer_report: Mapping[str, Any] | None = None
    renderer_ready = not renderer_requested
    renderer_started = False
    capture_plan_report: Mapping[str, Any] | None = None
    capture_plan_required = False
    capture_plan_ready = False

    if renderer_requested:
        runtime_bootstrap_path = artifacts.get("runtime_bootstrap")
        if report.get("offline_bootstrap_ready") is not True:
            blockers.append("renderer-evidence:offline-bootstrap-not-ready")
        elif not runtime_bootstrap_path:
            blockers.append("renderer-evidence:runtime-bootstrap-artifact-missing")
        else:
            renderer_started = True
            try:
                renderer_report = run_source_bootstrap_production(
                    capture_jsonl=args.renderer_capture_jsonl,
                    pe_evidence=args.renderer_pe_evidence,
                    pe_image=args.renderer_pe_image,
                    output_dir=renderer_dir,
                    corpus=list(args.inputs),
                    bundles=list(args.renderer_bundle),
                    runtime_bootstrap=runtime_bootstrap_path,
                    compact_evidence=args.renderer_compact_evidence,
                    compact_crosscheck=not args.renderer_no_compact_crosscheck,
                    max_json_bytes=args.renderer_max_json_bytes,
                )
            except Exception as exc:
                blockers.append(f"renderer-evidence:failed:{type(exc).__name__}:{exc}")
                renderer_report = None
            if isinstance(renderer_report, Mapping):
                renderer_ready = renderer_report.get("ready") is True
                if not renderer_ready:
                    blockers.extend(
                        f"renderer-evidence:{reason}"
                        for reason in renderer_report.get("blocking_reasons") or ["not-ready"]
                    )
            else:
                renderer_ready = False

    if renderer_started and isinstance(renderer_report, Mapping):
        artifacts["renderer_source_bootstrap"] = str(_renderer_manifest_path(out))
        stages["renderer_source_bootstrap"] = dict(renderer_report)
    else:
        artifacts["renderer_source_bootstrap"] = None
        if renderer_requested:
            stages["renderer_source_bootstrap"] = {
                "format": "SHIFT.SilverstoneRendererSourceBootstrapProductionRun/1",
                "status": "blocked",
                "ready": False,
                "blocking_reasons": [
                    reason.removeprefix("renderer-evidence:")
                    for reason in blockers
                    if reason.startswith("renderer-evidence:")
                ],
            }

    scene_handoff_requested = (
        renderer_requested
        and not bool(args.scene_set)
        and not resource_pipeline_requested
    )
    scene_handoff_report: Mapping[str, Any] | None = None
    scene_handoff_ready = not scene_handoff_requested
    if renderer_ready and scene_handoff_requested:
        runtime_bootstrap_path = str(artifacts.get("runtime_bootstrap") or "")
        renderer_manifest = str(artifacts.get("renderer_source_bootstrap") or "")
        if not runtime_bootstrap_path or not renderer_manifest:
            scene_handoff_ready = False
            blockers.append("renderer-native-scene:required-input-artifact-missing")
        else:
            try:
                scene_handoff_report = materialize_renderer_native_scene_handoff(
                    runtime_bootstrap=runtime_bootstrap_path,
                    renderer_source_bootstrap=renderer_manifest,
                    output_dir=scene_handoff_dir,
                    capture_root=renderer_capture_root,
                    environment_cube_dds=args.renderer_environment_cube_dds,
                    external_sampler_snapshots=args.renderer_external_sampler_snapshots,
                    external_sampler_cube_snapshots=(
                        args.renderer_external_sampler_cube_snapshots
                    ),
                    validator=args.renderer_validator,
                )
            except Exception as exc:
                scene_handoff_ready = False
                blockers.append(
                    f"renderer-native-scene:failed:{type(exc).__name__}:{exc}"
                )
                scene_handoff_report = None
            else:
                scene_handoff_ready = scene_handoff_report.get("ready") is True
                if not scene_handoff_ready:
                    blockers.extend(
                        f"renderer-native-scene:{reason}"
                        for reason in scene_handoff_report.get("blocking_reasons")
                        or ["not-ready"]
                    )

        artifacts["renderer_native_scene_handoff"] = (
            str(_scene_handoff_path(out))
            if isinstance(scene_handoff_report, Mapping)
            else None
        )
        stages["renderer_native_scene_handoff"] = (
            dict(scene_handoff_report)
            if isinstance(scene_handoff_report, Mapping)
            else {
                "format": "SHIFT.RendererNativeSceneHandoff/1",
                "status": "blocked",
                "ready": False,
                "scene_set_ready": False,
                "blocking_reasons": [
                    reason.removeprefix("renderer-native-scene:")
                    for reason in blockers
                    if reason.startswith("renderer-native-scene:")
                ],
            }
        )

        if isinstance(scene_handoff_report, Mapping):
            handoff_boundary = scene_handoff_report.get("boundary")
            capture_plan_required = (
                isinstance(handoff_boundary, Mapping)
                and handoff_boundary.get("capture_observation_required") is True
            )
            if capture_plan_required:
                try:
                    capture_plan_report = build_capture_plan(scene_handoff_report)
                except Exception as exc:
                    blockers.append(
                        f"renderer-capture-plan:failed:{type(exc).__name__}:{exc}"
                    )
                else:
                    capture_plan_ready = capture_plan_report.get("ready") is True
                    stages["renderer_external_sampler_capture_plan"] = dict(
                        capture_plan_report
                    )
                    if capture_plan_ready:
                        _write(capture_plan_path, capture_plan_report)
                        artifacts["renderer_external_sampler_capture_plan"] = str(
                            capture_plan_path
                        )
                    else:
                        blockers.extend(
                            f"renderer-capture-plan:{reason}"
                            for reason in capture_plan_report.get("blocking_reasons")
                            or ["not-ready"]
                        )
            if not capture_plan_ready:
                artifacts["renderer_external_sampler_capture_plan"] = None
                if capture_plan_path.exists():
                    capture_plan_path.unlink()
        else:
            artifacts["renderer_external_sampler_capture_plan"] = None
            if capture_plan_path.exists():
                capture_plan_path.unlink()

        blockers = [reason for reason in blockers if not reason.startswith("profile:")]
        report["artifacts"] = artifacts
        report["stages"] = stages
        blockers.extend(
            _refresh_runtime_profile(
                report,
                out=out,
                workspace_root=args.workspace_root,
                explicit=explicit,
                runtime_scene_handoff=scene_handoff_report,
                input_script=args.input_script,
                interactive=args.interactive,
                keyboard=args.keyboard,
                frames=args.frames,
            )
        )
        artifacts = dict(report.get("artifacts") or {})
        stages = dict(report.get("stages") or {})
    else:
        artifacts["renderer_native_scene_handoff"] = None
        artifacts["renderer_external_sampler_capture_plan"] = None
        if capture_plan_path.exists():
            capture_plan_path.unlink()

    boundary["phase642_capture_plan_required"] = capture_plan_required
    boundary["phase642_capture_plan_ready"] = capture_plan_ready
    report["artifacts"] = artifacts
    report["stages"] = stages
    report["renderer_evidence_requested"] = renderer_requested
    report["renderer_evidence_ready"] = renderer_ready
    report["renderer_native_scene_requested"] = scene_handoff_requested
    report["renderer_native_scene_ready"] = scene_handoff_ready
    report["renderer_capture_observation_required"] = capture_plan_required
    report["renderer_capture_plan_ready"] = capture_plan_ready
    report["renderer_capture_root"] = (
        str(renderer_capture_root) if renderer_capture_root is not None else None
    )
    report["renderer_frontier"] = (
        (((renderer_report.get("self_bootstrap") or {}).get("production") or {}).get(
            "renderer_frontier"
        ))
        if isinstance(renderer_report, Mapping)
        else None
    )

    launch_gate_ready = (
        report.get("profile_ready") is True
        and renderer_ready
        and scene_handoff_ready
    )
    if launch_gate_ready and args.validate_launch_plan:
        profile_path = Path(str((report.get("artifacts") or {}).get("profile") or ""))
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
            report["status"] = "launch-plan-blocked"
            report["ready"] = False
            report["launch_plan_ready"] = False
            blockers.append(f"launch-plan:{type(exc).__name__}:{exc}")
            if launch_plan_path.exists():
                launch_plan_path.unlink()
        else:
            _write(launch_plan_path, launch_plan)
            report["status"] = "launch-plan-ready"
            report["ready"] = True
            report["launch_plan_ready"] = True
            artifacts["launch_plan"] = str(launch_plan_path)
    elif args.validate_launch_plan:
        boundary["launcher_validation_performed"] = False
        report["launch_plan_ready"] = False
        if launch_plan_path.exists():
            launch_plan_path.unlink()
    elif launch_plan_path.exists():
        launch_plan_path.unlink()

    if report.get("offline_bootstrap_ready") is not True:
        report["status"] = "offline-bootstrap-blocked"
        report["ready"] = False
        report["launch_plan_ready"] = False
    elif renderer_requested and not renderer_ready:
        report["status"] = "renderer-evidence-blocked"
        report["ready"] = False
        report["launch_plan_ready"] = False
    elif scene_handoff_requested and not scene_handoff_ready:
        report["status"] = "renderer-native-scene-blocked"
        report["ready"] = False
        report["launch_plan_ready"] = False
    elif report.get("profile_ready") is not True:
        report["status"] = "profile-blocked"
        report["ready"] = False
    elif not args.validate_launch_plan:
        report["status"] = "profile-ready"
        report["ready"] = True

    report["blocking_reasons"] = _unique(blockers)
    report["boundary"] = boundary
    report["artifacts"] = artifacts
    _write(report_path, report)
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "offline_bootstrap_ready": report["offline_bootstrap_ready"],
        "resource_pipeline": report.get("resource_pipeline"),
        "renderer_evidence_requested": report["renderer_evidence_requested"],
        "renderer_evidence_ready": report["renderer_evidence_ready"],
        "renderer_native_scene_requested": report["renderer_native_scene_requested"],
        "renderer_native_scene_ready": report["renderer_native_scene_ready"],
        "renderer_capture_observation_required": report[
            "renderer_capture_observation_required"
        ],
        "renderer_capture_plan_ready": report["renderer_capture_plan_ready"],
        "renderer_capture_root": report["renderer_capture_root"],
        "renderer_frontier": report["renderer_frontier"],
        "profile_ready": report["profile_ready"],
        "launch_plan_ready": report["launch_plan_ready"],
        "blocking_reasons": report["blocking_reasons"],
        "artifacts": report["artifacts"],
        "output": str(report_path),
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
