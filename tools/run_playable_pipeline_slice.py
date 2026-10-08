#!/usr/bin/env python3
"""Build and execute one provenance-gated playable resource-pipeline slice."""
from __future__ import annotations

import argparse
import hashlib
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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_or_none(path: Path) -> str | None:
    try:
        return _sha256(path)
    except OSError:
        return None


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _output_from_bootstrap_args(args: Sequence[str]) -> Path:
    values = list(args)
    outputs: list[Path] = []
    index = 0
    while index < len(values):
        token = values[index]
        if token in {"-o", "--output"}:
            if index + 1 >= len(values):
                raise ExecutionError(f"{token} requires a value")
            outputs.append(Path(values[index + 1]).resolve())
            index += 2
            continue
        if token.startswith("--output="):
            raw = token.split("=", 1)[1]
            if not raw:
                raise ExecutionError("--output requires a value")
            outputs.append(Path(raw).resolve())
        index += 1

    if not outputs:
        raise ExecutionError("bootstrap arguments must include -o/--output")
    distinct = list(dict.fromkeys(outputs))
    if len(distinct) != 1:
        rendered = ", ".join(str(path) for path in distinct)
        raise ExecutionError(
            "bootstrap arguments contain conflicting output authorities: " + rendered
        )
    return distinct[0]


def _clear_stale_execution_receipt(output_dir: Path) -> bool:
    receipt = output_dir / "execution_result.json"
    if not receipt.exists() and not receipt.is_symlink():
        return False
    if receipt.is_dir() and not receipt.is_symlink():
        raise ExecutionError(
            f"stale execution receipt path is a directory: {receipt}"
        )
    try:
        receipt.unlink()
    except OSError as exc:
        raise ExecutionError(
            f"could not clear stale execution receipt: {receipt}: {exc}"
        ) from exc
    return True


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
    stale_receipt_removed = _clear_stale_execution_receipt(output_dir)
    if "--validate-launch-plan" not in args:
        args.append("--validate-launch-plan")

    bootstrap_exit = bootstrap.main(args)
    if bootstrap_exit != 0:
        raise ExecutionError(f"playable pipeline bootstrap failed with exit code {bootstrap_exit}")

    report, plan = _validated_execution_plan(output_dir)
    report_path = (output_dir / "playable_pipeline_bootstrap.json").resolve()
    plan_path = (output_dir / "launch_plan.json").resolve()
    report_sha256 = _sha256(report_path)
    plan_sha256 = _sha256(plan_path)

    runtime_path = Path(plan["argv"][0]).resolve()
    if not runtime_path.is_file():
        raise ExecutionError(f"launch plan runtime executable not found: {runtime_path}")
    if not os.access(runtime_path, os.X_OK):
        raise ExecutionError(f"launch plan runtime is not executable: {runtime_path}")
    runtime_sha256 = _sha256(runtime_path)

    launch_environment = os.environ.copy()
    launch_environment.update(dict(plan["environment"]))
    completed = runner(
        list(plan["argv"]),
        env=launch_environment,
        check=False,
    )

    report_sha256_after = _sha256_or_none(report_path)
    plan_sha256_after = _sha256_or_none(plan_path)
    runtime_sha256_after = _sha256_or_none(runtime_path)
    report_stable = report_sha256_after == report_sha256
    plan_stable = plan_sha256_after == plan_sha256
    launch_artifacts_stable = report_stable and plan_stable
    runtime_binary_stable = runtime_sha256_after == runtime_sha256
    execution_ready = (
        completed.returncode == 0
        and launch_artifacts_stable
        and runtime_binary_stable
    )
    if not launch_artifacts_stable:
        status = "launch-artifact-changed"
    elif not runtime_binary_stable:
        status = "runtime-binary-changed"
    elif completed.returncode == 0:
        status = "completed"
    else:
        status = "runtime-failed"

    receipt_path = (output_dir / "execution_result.json").resolve()
    result = {
        "format": FORMAT,
        "version": 1,
        "status": status,
        "ready": execution_ready,
        "runtime_returncode": completed.returncode,
        "runtime_executable": str(runtime_path),
        "runtime_executable_sha256": runtime_sha256,
        "runtime_executable_sha256_after": runtime_sha256_after,
        "runtime_executable_stable": runtime_binary_stable,
        "bootstrap_report": str(report_path),
        "bootstrap_report_sha256": report_sha256,
        "bootstrap_report_sha256_after": report_sha256_after,
        "bootstrap_report_stable": report_stable,
        "launch_plan": str(plan_path),
        "launch_plan_sha256": plan_sha256,
        "launch_plan_sha256_after": plan_sha256_after,
        "launch_plan_stable": plan_stable,
        "launch_artifacts_stable": launch_artifacts_stable,
        "execution_receipt": str(receipt_path),
        "stale_execution_receipt_removed": stale_receipt_removed,
        "track": report.get("track"),
        "vehicle": report.get("vehicle"),
        "boundary": {
            "single_output_authority_required": True,
            "stale_execution_receipt_cleared_before_attempt": True,
            "bootstrap_completed_before_runtime_execution": True,
            "provenance_validated_launch_plan_required": True,
            "launch_plan_argv_reconstructed": False,
            "launch_plan_environment_reconstructed": False,
            "bootstrap_report_hash_recorded_before_execution": True,
            "launch_plan_hash_recorded_before_execution": True,
            "bootstrap_report_rehashed_after_execution": True,
            "launch_plan_rehashed_after_execution": True,
            "launch_artifacts_stable_across_execution": launch_artifacts_stable,
            "runtime_executable_hash_recorded_before_execution": True,
            "runtime_executable_rehashed_after_execution": True,
            "runtime_executable_stable_across_execution": runtime_binary_stable,
            "resource_pipeline_physics_or_participant_replaced": False,
            "runtime_execution_attempted": True,
            "runtime_success_claimed": execution_ready,
            "retail_game_loop_claimed": False,
        },
    }
    _write_json(receipt_path, result)
    return result


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
