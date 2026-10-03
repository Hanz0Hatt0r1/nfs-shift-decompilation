#!/usr/bin/env python3
"""Build a fail-closed native vertical-slice profile directly from SHIFT resources."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

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

from offline_vertical_slice_bootstrap import build_offline_vertical_slice_bootstrap
from run_native_vertical_slice import ProfileError, build_launch_plan


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


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
    parser.add_argument("--validate-launch-plan", action="store_true")
    parser.add_argument(
        "--runtime",
        default="native_runtime/build/shift_runtime",
        help="runtime executable used only for launch-plan validation",
    )
    parser.add_argument("--validation", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.decode_limit_per_archive < 0:
        parser.error("--decode-limit-per-archive must be non-negative")

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
    boundary = dict(report.get("boundary") or {})
    boundary["launcher_validation_requested"] = bool(args.validate_launch_plan)
    report["boundary"] = boundary

    if report.get("profile_ready") is True and args.validate_launch_plan:
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
            report["blocking_reasons"] = list(dict.fromkeys(
                list(report.get("blocking_reasons") or [])
                + [f"launch-plan:{type(exc).__name__}:{exc}"]
            ))
            if launch_plan_path.exists():
                launch_plan_path.unlink()
        else:
            _write(launch_plan_path, launch_plan)
            report["status"] = "launch-plan-ready"
            report["ready"] = True
            report["launch_plan_ready"] = True
            artifacts = dict(report.get("artifacts") or {})
            artifacts["launch_plan"] = str(launch_plan_path)
            report["artifacts"] = artifacts
    elif launch_plan_path.exists():
        launch_plan_path.unlink()

    _write(report_path, report)
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "offline_bootstrap_ready": report["offline_bootstrap_ready"],
        "profile_ready": report["profile_ready"],
        "launch_plan_ready": report["launch_plan_ready"],
        "blocking_reasons": report["blocking_reasons"],
        "artifacts": report["artifacts"],
        "output": str(report_path),
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
