#!/usr/bin/env python3
"""Build a fail-closed native vertical-slice profile directly from SHIFT resources.

Optional historical-capture renderer evidence can be regenerated in the same
command. When enabled, the renderer path consumes the exact runtime-bootstrap
artifact created earlier in this invocation, so no manual resource->renderer
handoff is required.
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

from offline_vertical_slice_bootstrap import build_offline_vertical_slice_bootstrap
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
        or args.renderer_pe_evidence
        or args.renderer_pe_image
        or args.renderer_bundle
        or args.renderer_compact_evidence
        or args.renderer_no_compact_crosscheck
    )


def _validate_renderer_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> bool:
    requested = _renderer_requested(args)
    pe_count = int(bool(args.renderer_pe_evidence)) + int(bool(args.renderer_pe_image))
    if requested and not args.renderer_capture_jsonl:
        parser.error(
            "renderer evidence requires --renderer-capture-jsonl"
        )
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


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.decode_limit_per_archive < 0:
        parser.error("--decode-limit-per-archive must be non-negative")
    renderer_requested = _validate_renderer_args(parser, args)

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
    renderer_dir = out / "renderer-evidence"

    boundary = dict(report.get("boundary") or {})
    boundary["launcher_validation_requested"] = bool(args.validate_launch_plan)
    boundary["renderer_evidence_requested"] = renderer_requested
    boundary["renderer_uses_selected_runtime_bootstrap"] = renderer_requested
    boundary["manual_resource_to_renderer_handoff_required"] = False
    boundary["renderer_bundle_is_selection_authority"] = False
    boundary["renderer_missing_evidence_synthesized"] = False
    boundary["renderer_evidence_ready_is_runtime_render_admission"] = False
    report["boundary"] = boundary

    artifacts = dict(report.get("artifacts") or {})
    stages = dict(report.get("stages") or {})
    blockers = list(report.get("blocking_reasons") or [])
    renderer_report: Mapping[str, Any] | None = None
    renderer_ready = not renderer_requested
    renderer_started = False

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
                blockers.append(
                    f"renderer-evidence:failed:{type(exc).__name__}:{exc}"
                )
                renderer_report = None
            if isinstance(renderer_report, Mapping):
                renderer_ready = renderer_report.get("ready") is True
                if not renderer_ready:
                    blockers.extend(
                        f"renderer-evidence:{reason}"
                        for reason in (
                            renderer_report.get("blocking_reasons")
                            or ["not-ready"]
                        )
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

    report["artifacts"] = artifacts
    report["stages"] = stages
    report["renderer_evidence_requested"] = renderer_requested
    report["renderer_evidence_ready"] = renderer_ready
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
    elif args.validate_launch_plan and report.get("profile_ready") is True and not renderer_ready:
        boundary["launcher_validation_performed"] = False
        report["launch_plan_ready"] = False
        if launch_plan_path.exists():
            launch_plan_path.unlink()
    elif launch_plan_path.exists():
        launch_plan_path.unlink()

    if (
        renderer_requested
        and not renderer_ready
        and report.get("offline_bootstrap_ready") is True
    ):
        report["status"] = "renderer-evidence-blocked"
        report["ready"] = False
        report["launch_plan_ready"] = False
    elif report.get("profile_ready") is True and not args.validate_launch_plan:
        report["ready"] = True
    elif report.get("profile_ready") is not True:
        report["ready"] = False

    report["blocking_reasons"] = _unique(blockers)
    _write(report_path, report)
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "offline_bootstrap_ready": report["offline_bootstrap_ready"],
        "renderer_evidence_requested": report["renderer_evidence_requested"],
        "renderer_evidence_ready": report["renderer_evidence_ready"],
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
