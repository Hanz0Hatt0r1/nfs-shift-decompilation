#!/usr/bin/env python3
"""Run the final exact Silverstone + BMW playable smoke only after canonical gates."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import bootstrap_playable_pipeline_slice as bootstrap
import run_playable_pipeline_slice as execution

FORMAT = "SHIFT.FinalPlayablePipelineSmokePreflight/1"
COORDINATION_FORMAT = "SHIFT.PlayableSliceThreeProcessExecution/1"
COORDINATION = ROOT / "evidence" / "playable_slice_three_process_execution.json"
EXACT_TRACK = "Silverstone_Era3_GrandPrix"
EXACT_VEHICLE = "BMW_M3_E36"
REQUIRED_FRONTIER_GATES = (
    "vehicle_world_transform_ready",
    "retail_outer_cadence_admitted",
    "retail_inner_substep_execution_admitted",
    "retail_control_chain_complete",
    "retail_camera_follow_ready",
    "process_2_camera_feed_ready",
)


class FinalSmokeError(ValueError):
    """Raised when the final playable smoke is not yet admissible."""


def _load_json_with_sha256(path: Path, *, label: str) -> tuple[dict[str, Any], str]:
    try:
        raw = path.read_bytes()
    except FileNotFoundError as exc:
        raise FinalSmokeError(f"{label} not found: {path}") from exc
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FinalSmokeError(f"{label} is not valid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise FinalSmokeError(f"{label} must be a JSON object: {path}")
    return value, hashlib.sha256(raw).hexdigest()


def _sha256_file(path: Path, *, label: str) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError as exc:
        raise FinalSmokeError(f"{label} not found: {path}") from exc


def _parse_bootstrap_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = bootstrap.build_parser()
    try:
        return parser.parse_args(list(argv))
    except SystemExit as exc:
        raise FinalSmokeError("invalid playable bootstrap arguments") from exc


def build_final_smoke_preflight(
    bootstrap_args: Sequence[str],
    *,
    coordination_path: str | Path = COORDINATION,
) -> tuple[dict[str, Any], list[str]]:
    args = _parse_bootstrap_args(bootstrap_args)
    blockers: list[str] = []

    if args.track != EXACT_TRACK:
        blockers.append(f"target:track-must-be-{EXACT_TRACK}:got-{args.track}")
    if args.vehicle != EXACT_VEHICLE:
        blockers.append(f"target:vehicle-must-be-{EXACT_VEHICLE}:got-{args.vehicle}")
    if not args.interactive:
        blockers.append("runtime:final-smoke-requires-interactive-continuous-mode")
    if args.frames is not None:
        blockers.append("runtime:final-smoke-must-not-have-frame-limit")
    if args.input_script:
        blockers.append("runtime:test-input-script-not-allowed")
    if args.keyboard:
        blockers.append("runtime:bounded-keyboard-mode-not-allowed")

    coordination_file = Path(coordination_path).resolve()
    coordination, coordination_sha256 = _load_json_with_sha256(
        coordination_file,
        label="playable coordination",
    )
    if coordination.get("format") != COORDINATION_FORMAT:
        blockers.append(f"coordination:format-must-be-{COORDINATION_FORMAT}")
    if coordination.get("status") != "active":
        blockers.append("coordination:not-active")
    frontier = coordination.get("main_frontier")
    if not isinstance(frontier, Mapping):
        blockers.append("coordination:main-frontier-missing")
        frontier = {}

    missing_gates = [gate for gate in REQUIRED_FRONTIER_GATES if frontier.get(gate) is not True]
    blockers.extend(f"coordination:{gate}:not-ready" for gate in missing_gates)

    blockers = list(dict.fromkeys(blockers))
    ready = not blockers
    report = {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "track": args.track,
        "vehicle": args.vehicle,
        "mode": "interactive-continuous" if args.interactive else "not-continuous",
        "coordination": str(coordination_file),
        "coordination_sha256": coordination_sha256,
        "required_frontier_gates": list(REQUIRED_FRONTIER_GATES),
        "blocking_reasons": blockers,
        "boundary": {
            "exact_silverstone_required": True,
            "exact_bmw_m3_e36_required": True,
            "interactive_continuous_runtime_required": True,
            "bounded_frame_smoke_allowed": False,
            "test_input_script_allowed": False,
            "test_only_vehicle_world_transform_script_allowed": False,
            "fresh_vehicle_world_transform_required": True,
            "retail_cadence_required": True,
            "retail_control_chain_required": True,
            "retail_camera_follow_required": True,
            "process_2_runtime_camera_feed_required": True,
            "coordination_bytes_bound_to_preflight": True,
            "coordination_must_remain_stable_before_runtime": True,
            "missing_upstream_gate_may_be_guessed": False,
            "retail_game_loop_claimed": False,
        },
    }
    return report, list(bootstrap_args)


def execute_final_smoke(
    bootstrap_args: Sequence[str],
    *,
    coordination_path: str | Path = COORDINATION,
) -> dict[str, Any]:
    preflight, forwarded = build_final_smoke_preflight(
        bootstrap_args,
        coordination_path=coordination_path,
    )
    if preflight["ready"] is not True:
        raise FinalSmokeError(
            "final playable smoke preflight blocked: "
            + ", ".join(str(reason) for reason in preflight["blocking_reasons"])
        )

    coordination_file = Path(str(preflight["coordination"]))
    current_coordination_sha256 = _sha256_file(
        coordination_file,
        label="playable coordination",
    )
    if current_coordination_sha256 != preflight["coordination_sha256"]:
        raise FinalSmokeError("playable coordination changed after final smoke preflight")

    result = execution.execute_playable_pipeline_slice(forwarded)
    return {
        "format": "SHIFT.FinalPlayablePipelineSmokeExecution/1",
        "version": 1,
        "ready": result.get("ready") is True,
        "preflight": preflight,
        "execution": result,
        "boundary": {
            "preflight_completed_before_runtime": True,
            "coordination_stability_checked_before_runtime": True,
            "coordination_rehash_occurs_immediately_before_runtime_delegation": True,
            "exact_resource_driven_target_required": True,
            "test_only_core_vehicle_transform_allowed": False,
            "retail_game_loop_claimed": False,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "bootstrap_args",
        nargs=argparse.REMAINDER,
        help="arguments for bootstrap_playable_pipeline_slice.py; prefix with --",
    )
    parsed = parser.parse_args(argv)
    forwarded = list(parsed.bootstrap_args)
    if forwarded and forwarded[0] == "--":
        forwarded = forwarded[1:]
    if not forwarded:
        parser.error("bootstrap arguments are required after --")
    try:
        report = execute_final_smoke(forwarded)
    except (OSError, FinalSmokeError, execution.ExecutionError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
