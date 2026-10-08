#!/usr/bin/env python3
"""Build a provenance-gated playable native slice from one resource pipeline."""
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

from bmw_vehicle_render_model_resource_join import (
    load_bmw_vehicle_render_model_resource_join,
)
from native_playable_scene_bootstrap import build_native_playable_scene_bootstrap
from offline_playable_pipeline_profile import build_playable_pipeline_profile_prepare
from offline_vertical_slice_bootstrap import build_offline_vertical_slice_bootstrap
import run_native_vertical_slice as native
from run_native_vertical_slice_playable_pipeline import (
    build_playable_pipeline_launch_plan,
)

BMW_RENDER_MODEL_JOIN = (
    ROOT / "evidence" / "process1_bmw_vehicle_render_model_resource_join.json"
)
FORMAT = "SHIFT.PlayableResourcePipelineBootstrap/1"


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", help="BFF, ZIP, or directory inputs")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--track", required=True)
    parser.add_argument("--vehicle", required=True)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--resource-pipeline", required=True)
    parser.add_argument("--camera-state", required=True)
    parser.add_argument("--solver-frame", required=True)
    parser.add_argument("--generated-body-constraint-frame", required=True)
    parser.add_argument("--constraint-sample-relation-frame", required=True)
    parser.add_argument("--constraint-relation-reset-frame", required=True)
    parser.add_argument("--post-solve-projection", required=True)
    parser.add_argument("--root-consensus")
    parser.add_argument("--runtime-shader-admission")
    parser.add_argument("--participant-observation")
    parser.add_argument("--decode-limit-per-archive", type=int, default=0)
    parser.add_argument("--vhf-hierarchy-root-frame")
    parser.add_argument("--renderer-validator")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--input-script")
    mode.add_argument("--interactive", action="store_true")
    mode.add_argument("--keyboard", action="store_true")
    parser.add_argument("--frames", type=int)
    parser.add_argument("--validate-launch-plan", action="store_true")
    parser.add_argument("--validation", action="store_true")
    parser.add_argument(
        "--runtime",
        default="native_runtime/build/shift_runtime",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.decode_limit_per_archive < 0:
        parser.error("--decode-limit-per-archive must be non-negative")
    if args.keyboard and args.frames is None:
        parser.error("--keyboard requires --frames")
    if args.interactive and args.frames is not None:
        parser.error("--interactive cannot be combined with --frames")

    workspace = Path(args.workspace_root).resolve()
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / "playable_pipeline_bootstrap.json"
    profile_path = out / "vertical_slice_profile.json"
    launch_plan_path = out / "launch_plan.json"
    explicit = {
        "camera_state": args.camera_state,
        "solver_frame": args.solver_frame,
        "generated_body_constraint_frame": args.generated_body_constraint_frame,
        "constraint_sample_relation_frame": args.constraint_sample_relation_frame,
        "constraint_relation_reset_frame": args.constraint_relation_reset_frame,
        "post_solve_projection": args.post_solve_projection,
    }

    blockers: list[str] = []
    stages: dict[str, Any] = {}
    artifacts: dict[str, Any] = {
        "profile": None,
        "playable_scene_bootstrap": None,
        "launch_plan": None,
    }

    try:
        pipeline_paths, pipeline_check = native._resolve_resource_pipeline_inputs(
            workspace,
            args.resource_pipeline,
            expected_track=args.track,
            expected_vehicle=args.vehicle,
        )
    except (OSError, native.ProfileError, ValueError) as exc:
        blockers.append(f"resource-pipeline:{type(exc).__name__}:{exc}")
        pipeline_paths = {}
        pipeline_check = None
    else:
        stages["resource_pipeline"] = pipeline_check
        if "participant_boundary" not in pipeline_paths:
            blockers.append("resource-pipeline:participant-runtime-evidence-required")

    base_report: Mapping[str, Any] | None = None
    if not blockers:
        try:
            base_report = build_offline_vertical_slice_bootstrap(
                args.inputs,
                out,
                track=args.track,
                vehicle=args.vehicle,
                workspace_root=workspace,
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
        except Exception as exc:
            blockers.append(f"offline-bootstrap:{type(exc).__name__}:{exc}")
        else:
            stages["offline_vertical_slice_bootstrap"] = dict(base_report)
            if base_report.get("offline_bootstrap_ready") is not True:
                blockers.extend(
                    "offline-bootstrap:" + str(reason)
                    for reason in base_report.get("blocking_reasons") or ["not-ready"]
                )

    playable: Mapping[str, Any] | None = None
    playable_path = out / "playable-scene" / "playable_scene_bootstrap.json"
    if not blockers:
        try:
            render_join = load_bmw_vehicle_render_model_resource_join(BMW_RENDER_MODEL_JOIN)
            playable = build_native_playable_scene_bootstrap(
                args.inputs,
                pipeline_paths["scene_set"],
                out / "playable-scene",
                vehicle=args.vehicle,
                validator=args.renderer_validator,
                vehicle_render_model_join=render_join,
                vhf_hierarchy_root_frame=args.vhf_hierarchy_root_frame,
            )
        except Exception as exc:
            blockers.append(f"playable-scene:{type(exc).__name__}:{exc}")
        else:
            stages["playable_scene_bootstrap"] = dict(playable)
            if playable.get("ready") is not True:
                blockers.extend(
                    "playable-scene:" + str(reason)
                    for reason in playable.get("blocking_reasons") or ["not-ready"]
                )
            else:
                artifacts["playable_scene_bootstrap"] = str(playable_path)

    profile_prepare: Mapping[str, Any] | None = None
    if not blockers and isinstance(base_report, Mapping):
        runtime_requirements = (
            (base_report.get("stages") or {}).get("runtime_requirements")
        )
        if not isinstance(runtime_requirements, Mapping):
            blockers.append("profile:runtime-requirements-missing")
        else:
            profile_prepare = build_playable_pipeline_profile_prepare(
                runtime_requirements,
                workspace_root=workspace,
                profile_path=profile_path,
                explicit_inputs=explicit,
                resource_pipeline=args.resource_pipeline,
                playable_scene_bootstrap=playable_path,
                input_script=args.input_script,
                interactive=args.interactive,
                keyboard=args.keyboard,
                frames=args.frames,
            )
            stages["playable_pipeline_profile_prepare"] = dict(profile_prepare)
            if profile_prepare.get("ready") is not True:
                blockers.extend(
                    "profile:" + str(reason)
                    for reason in profile_prepare.get("blocking_reasons") or ["not-ready"]
                )
            else:
                profile = profile_prepare.get("profile")
                if not isinstance(profile, Mapping):
                    blockers.append("profile:ready-without-profile")
                else:
                    _write(profile_path, profile)
                    artifacts["profile"] = str(profile_path)

    launch_plan: Mapping[str, Any] | None = None
    if not blockers and args.validate_launch_plan:
        try:
            launch_plan = build_playable_pipeline_launch_plan(
                profile_path,
                runtime=args.runtime,
                validation=args.validation,
            )
        except (OSError, native.ProfileError, ValueError) as exc:
            blockers.append(f"launch-plan:{type(exc).__name__}:{exc}")
        else:
            _write(launch_plan_path, launch_plan)
            artifacts["launch_plan"] = str(launch_plan_path)
            stages["launch_plan"] = dict(launch_plan)

    blockers = list(dict.fromkeys(blockers))
    profile_ready = artifacts["profile"] is not None
    launch_plan_ready = artifacts["launch_plan"] is not None
    ready = profile_ready and (not args.validate_launch_plan or launch_plan_ready)
    report = {
        "format": FORMAT,
        "version": 1,
        "status": (
            "launch-plan-ready"
            if launch_plan_ready
            else "profile-ready"
            if ready
            else "blocked"
        ),
        "ready": ready,
        "track": args.track,
        "vehicle": args.vehicle,
        "resource_pipeline": str(args.resource_pipeline),
        "profile_ready": profile_ready,
        "launch_plan_ready": launch_plan_ready,
        "blocking_reasons": blockers,
        "stages": stages,
        "artifacts": artifacts,
        "boundary": {
            "pipeline_scene_validated_before_playable_composition": True,
            "pipeline_participant_runtime_evidence_required": True,
            "phase643_playable_composite_required": True,
            "playable_scene_provenance_revalidated_by_launcher": (
                launch_plan_ready
            ),
            "resource_pipeline_physics_or_participant_replaced": False,
            "runtime_execution_claimed": False,
        },
    }
    _write(report_path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
