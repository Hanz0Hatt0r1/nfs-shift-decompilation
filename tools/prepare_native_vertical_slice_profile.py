#!/usr/bin/env python3
"""Prepare a fail-closed native vertical-slice profile from runtime requirements."""
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

from offline_vertical_slice_profile import build_vertical_slice_profile_prepare
from run_native_vertical_slice import ProfileError, build_launch_plan


def _load(path: str | Path) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("requirements", help="SHIFT.OfflineNativeRuntimeRequirements/1 JSON")
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("-o", "--output", required=True, help="profile JSON path")
    parser.add_argument("--report", help="prepare-report JSON path")
    parser.add_argument(
        "--resource-pipeline",
        help=(
            "workspace-local SHIFT offline resource pipeline directory; when set, "
            "scene_set, physics_manifest and participant_boundary are resolved "
            "and fully validated later by the native launcher"
        ),
    )
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
    parser.add_argument(
        "--validate-launch-plan",
        action="store_true",
        help="validate the completed profile through tools/run_native_vertical_slice.py",
    )
    parser.add_argument(
        "--runtime",
        default="native_runtime/build/shift_runtime",
        help="native runtime executable used only for launch-plan validation",
    )
    parser.add_argument(
        "--launch-plan",
        help="launch-plan JSON output; defaults next to the prepared profile",
    )
    parser.add_argument(
        "--validation",
        action="store_true",
        help="include native Vulkan validation in the generated launch plan",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    profile_path = Path(args.output)
    report_path = Path(args.report) if args.report else profile_path.with_suffix(
        profile_path.suffix + ".prepare.json"
    )
    launch_plan_path = (
        Path(args.launch_plan)
        if args.launch_plan
        else profile_path.with_suffix(profile_path.suffix + ".launch_plan.json")
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
    report = build_vertical_slice_profile_prepare(
        _load(args.requirements),
        workspace_root=args.workspace_root,
        profile_path=profile_path,
        explicit_inputs=explicit,
        resource_pipeline=args.resource_pipeline,
        input_script=args.input_script,
        interactive=args.interactive,
        keyboard=args.keyboard,
        frames=args.frames,
    )
    report = dict(report)
    report["profile_ready"] = report["ready"] is True
    report["launcher_validation_requested"] = bool(args.validate_launch_plan)
    report["launcher_validation_ready"] = False
    report["launch_plan"] = None

    if report["profile_ready"]:
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(profile_path, report["profile"])
    elif profile_path.exists():
        profile_path.unlink()
    if not report["profile_ready"] and launch_plan_path.exists():
        launch_plan_path.unlink()

    if report["profile_ready"] and args.validate_launch_plan:
        boundary = dict(report.get("boundary") or {})
        boundary["launcher_validation_performed"] = True
        boundary["launcher_validation_still_required"] = False
        report["boundary"] = boundary
        try:
            launch_plan = build_launch_plan(
                profile_path,
                runtime=args.runtime,
                validation=args.validation,
            )
        except (ProfileError, OSError, ValueError) as exc:
            report["status"] = "launcher-validation-blocked"
            report["ready"] = False
            report["blocking_reasons"] = list(dict.fromkeys(
                list(report.get("blocking_reasons") or [])
                + [f"launcher-validation:{type(exc).__name__}:{exc}"]
            ))
            if launch_plan_path.exists():
                launch_plan_path.unlink()
        else:
            _write_json(launch_plan_path, launch_plan)
            report["status"] = "launch-plan-ready"
            report["ready"] = True
            report["launcher_validation_ready"] = True
            report["launch_plan"] = str(launch_plan_path)
    elif report["profile_ready"]:
        report["ready"] = True

    _write_json(report_path, report)

    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "profile_ready": report["profile_ready"],
        "resource_pipeline": report.get("resource_pipeline"),
        "launcher_validation_requested": report["launcher_validation_requested"],
        "launcher_validation_ready": report["launcher_validation_ready"],
        "auto_filled_inputs": report["auto_filled_inputs"],
        "explicit_filled_inputs": report["explicit_filled_inputs"],
        "blocking_reasons": report["blocking_reasons"],
        "profile": str(profile_path) if report["profile_ready"] else None,
        "launch_plan": report["launch_plan"],
        "report": str(report_path),
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
