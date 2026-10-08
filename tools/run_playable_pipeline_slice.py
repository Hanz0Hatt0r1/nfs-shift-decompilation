#!/usr/bin/env python3
"""Build and execute one provenance-gated playable resource-pipeline slice."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import bootstrap_playable_pipeline_slice as bootstrap

FORMAT = "SHIFT.PlayableResourcePipelineExecution/1"
BOOTSTRAP_FORMAT = "SHIFT.PlayableResourcePipelineBootstrap/1"
PLAN_FORMAT = "SHIFT.NativeVerticalSliceLaunchPlan/1"


class ExecutionError(ValueError):
    """Raised when a prepared playable pipeline execution is unsafe."""


def _load_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ExecutionError(f"{label} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ExecutionError(f"{label} is not valid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ExecutionError(f"{label} must be a JSON object: {path}")
    return value


def _output_from_bootstrap_args(args: Sequence[str]) -> Path:
    values = list(args)
    for index, token in enumerate(values):
        if token in {"-o", "--output"}:
            if index + 1 >= len(values):
                raise ExecutionError(f"{token} requires a value")
            return Path(values[index + 1]).resolve()
        if token.startswith("--output="):
            return Path(token.split("=", 1)[1]).resolve()
    raise ExecutionError("bootstrap arguments must include -o/--output")


def _validated_execution_plan(output_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    report_path = output_dir / "playable_pipeline_bootstrap.json"
    report = _load_json(report_path, label="playable pipeline bootstrap report")
    if report.get("format") != BOOTSTRAP_FORMAT:
        raise ExecutionError(f"bootstrap report must be {BOOTSTRAP_FORMAT}")
    if report.get("ready") is not True or report.get("launch_plan_ready") is not True:
        raise ExecutionError("bootstrap report has no ready validated launch plan")

    artifacts = report.get("artifacts")
    if not isinstance(artifacts, Mapping):
        raise ExecutionError("bootstrap report artifacts must be an object")
    recorded_plan = str(artifacts.get("launch_plan") or "").strip()
    if not recorded_plan:
        raise ExecutionError("bootstrap report launch-plan artifact is missing")
    plan_path = Path(recorded_plan).resolve()
    expected_plan = (output_dir / "launch_plan.json").resolve()
    if plan_path != expected_plan:
        raise ExecutionError("bootstrap report launch-plan path disagrees with output layout")

    plan = _load_json(plan_path, label="playable pipeline launch plan")
    if plan.get("format") != PLAN_FORMAT or plan.get("ready") is not True:
        raise ExecutionError(f"launch plan must be ready {PLAN_FORMAT}")
    argv = plan.get("argv")
    environment = plan.get("environment")
    if not isinstance(argv, list) or not argv or not all(isinstance(item, str) and item for item in argv):
        raise ExecutionError("launch plan argv must be a non-empty string array")
    if not isinstance(environment, Mapping) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in environment.items()
    ):
        raise ExecutionError("launch plan environment must be a string map")
    return report, plan


def execute_playable_pipeline_slice(
    bootstrap_args: Sequence[str],
    *,
    runner=subprocess.run,
) -> dict[str, Any]:
    args = list(bootstrap_args)
    output_dir = _output_from_bootstrap_args(args)
    if "--validate-launch-plan" not in args:
        args.append("--validate-launch-plan")

    bootstrap_exit = bootstrap.main(args)
    if bootstrap_exit != 0:
        raise ExecutionError(f"playable pipeline bootstrap failed with exit code {bootstrap_exit}")

    report, plan = _validated_execution_plan(output_dir)
    launch_environment = os.environ.copy()
    launch_environment.update(dict(plan["environment"]))
    completed = runner(
        list(plan["argv"]),
        env=launch_environment,
        check=False,
    )
    return {
        "format": FORMAT,
        "version": 1,
        "status": "completed" if completed.returncode == 0 else "runtime-failed",
        "ready": completed.returncode == 0,
        "runtime_returncode": completed.returncode,
        "bootstrap_report": str((output_dir / "playable_pipeline_bootstrap.json").resolve()),
        "launch_plan": str((output_dir / "launch_plan.json").resolve()),
        "track": report.get("track"),
        "vehicle": report.get("vehicle"),
        "boundary": {
            "bootstrap_completed_before_runtime_execution": True,
            "provenance_validated_launch_plan_required": True,
            "launch_plan_argv_reconstructed": False,
            "launch_plan_environment_reconstructed": False,
            "resource_pipeline_physics_or_participant_replaced": False,
            "runtime_execution_attempted": True,
            "runtime_success_claimed": completed.returncode == 0,
            "retail_game_loop_claimed": False,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "bootstrap_args",
        nargs=argparse.REMAINDER,
        help="arguments forwarded to bootstrap_playable_pipeline_slice.py; prefix with --",
    )
    args = parser.parse_args(argv)
    forwarded = list(args.bootstrap_args)
    if forwarded and forwarded[0] == "--":
        forwarded = forwarded[1:]
    if not forwarded:
        parser.error("bootstrap arguments are required after --")
    try:
        result = execute_playable_pipeline_slice(forwarded)
    except (OSError, ExecutionError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["ready"] else int(result["runtime_returncode"] or 1)


if __name__ == "__main__":
    raise SystemExit(main())
