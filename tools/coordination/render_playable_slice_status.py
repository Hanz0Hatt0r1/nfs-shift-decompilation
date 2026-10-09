#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXECUTION_PATH = ROOT / "evidence/playable_slice_three_process_execution.json"
LANES_PATH = ROOT / "coordination/lane_ownership.json"
STATUS_PATH = ROOT / "coordination/PLAYABLE_SLICE_STATUS.md"

HUMAN_PHASE_PATTERNS = {
    "README.md": re.compile(r"Current `main` frontier:\s*\*\*Phase\s+(\d+)\*\*"),
    "PROCESS_INSTRUCTIONS.md": re.compile(r"Current merged main frontier:\s*\*\*Phase\s+(\d+)\*\*"),
    "ROADMAP.md": re.compile(r"Current mainline:\s*Phase\s+(\d+)"),
}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def queue_map(execution: dict) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for process in execution["processes"].values():
        for row in process["queue"]:
            task_id = row["id"]
            if task_id in result:
                raise ValueError(f"duplicate queue id: {task_id}")
            result[task_id] = row
    return result


def validate(execution: dict, registry: dict) -> None:
    if execution.get("format") != "SHIFT.PlayableSliceThreeProcessExecution/1":
        raise ValueError("unexpected execution-state format")
    if registry.get("format") != "SHIFT.DevelopmentLaneRegistry/1":
        raise ValueError("unexpected lane-registry format")
    if registry.get("source_of_truth") != str(EXECUTION_PATH.relative_to(ROOT)):
        raise ValueError("lane registry points at the wrong source of truth")

    frontier = execution["main_frontier"]
    provider_count = execution["provider_frontier"]["count"]
    if frontier["active_external_provider_count"] != provider_count:
        raise ValueError("provider count disagrees inside canonical execution state")

    queues = queue_map(execution)
    assigned: list[str] = []
    registry_shards: dict[str, tuple[str, str, dict]] = {}
    for lane in registry["lanes"]:
        if not lane.get("queue_ids"):
            raise ValueError(f"lane {lane['id']} owns no queue ids")
        assigned.extend(lane["queue_ids"])
        for task_id in lane["queue_ids"]:
            if task_id not in queues:
                raise ValueError(f"lane {lane['id']} references unknown queue id {task_id}")
        for shard in lane.get("shared_queue_shards", []):
            shard_id = shard["id"]
            parent_id = shard["parent_queue_id"]
            if shard_id in registry_shards:
                raise ValueError(f"duplicate shared queue shard id: {shard_id}")
            if parent_id not in queues:
                raise ValueError(f"shared shard {shard_id} references unknown parent queue id {parent_id}")
            if shard.get("state") != queues[parent_id]["state"]:
                raise ValueError(f"shared shard {shard_id} state disagrees with parent queue {parent_id}")
            registry_shards[shard_id] = (parent_id, lane["owner"], shard)

    if len(assigned) != len(set(assigned)):
        raise ValueError("a queue id is assigned to more than one lane")
    if set(assigned) != set(queues):
        missing = sorted(set(queues) - set(assigned))
        extra = sorted(set(assigned) - set(queues))
        raise ValueError(f"lane coverage mismatch: missing={missing}, extra={extra}")

    execution_shards: dict[str, tuple[str, dict]] = {}
    for parent_id, row in queues.items():
        for shard in row.get("parallel_shards", []):
            shard_id = shard["id"]
            if shard_id in execution_shards:
                raise ValueError(f"duplicate execution shard id: {shard_id}")
            execution_shards[shard_id] = (parent_id, shard)

    if set(registry_shards) != set(execution_shards):
        missing = sorted(set(execution_shards) - set(registry_shards))
        extra = sorted(set(registry_shards) - set(execution_shards))
        raise ValueError(f"shared shard coverage mismatch: missing={missing}, extra={extra}")

    for shard_id, (parent_id, lane_owner, _registry_shard) in registry_shards.items():
        execution_parent, execution_shard = execution_shards[shard_id]
        if execution_parent != parent_id:
            raise ValueError(f"shared shard {shard_id} parent mismatch")
        if execution_shard.get("owner") != lane_owner:
            raise ValueError(f"shared shard {shard_id} owner mismatch")
        if execution_shard.get("state") != queues[parent_id]["state"]:
            raise ValueError(f"execution shard {shard_id} state disagrees with parent queue")

    if frontier["final_playable_smoke_currently_runnable"]:
        required = (
            frontier["final_playable_smoke_entrypoint_ready"],
            frontier["retail_control_chain_complete"],
            frontier["retail_camera_follow_ready"],
        )
        if not all(required):
            raise ValueError("final smoke cannot be runnable while an upstream gate is false")

    if frontier["playable_slice_complete"] and not frontier["final_playable_smoke_currently_runnable"]:
        raise ValueError("playable slice cannot be complete before final smoke is runnable")


def is_available(state: str) -> bool:
    return state in {"current", "ready-parallel", "ready-to-consume", "continuous"}


def render(execution: dict, registry: dict) -> str:
    queues = queue_map(execution)
    frontier = execution["main_frontier"]
    lines: list[str] = [
        "# Playable slice status",
        "",
        "> Generated from `evidence/playable_slice_three_process_execution.json`.",
        "> Do not edit this file by hand. Human README/ROADMAP summaries are advisory only.",
        "",
        f"Updated: **{execution['updated']}**",
        "",
        "## Frontier",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Main phase | **{frontier['phase']}** |",
        f"| External vehicle providers | **{frontier['active_external_provider_count']}** |",
        f"| Selected-session physics rate | **{frontier['selected_session_rate_hz']} Hz** |",
        f"| Final smoke entrypoint | {'ready' if frontier['final_playable_smoke_entrypoint_ready'] else 'blocked'} |",
        f"| Final smoke runnable | {'yes' if frontier['final_playable_smoke_currently_runnable'] else 'no'} |",
        f"| Playable slice complete | {'yes' if frontier['playable_slice_complete'] else 'no'} |",
        "",
        "## Critical gates",
        "",
        "| Gate | State |",
        "| --- | --- |",
        f"| P1 contact-response proof complete | {'positive' if frontier['fun_00766510_p1_complete'] else 'open'} |",
        f"| Retail control chain | {'positive' if frontier['retail_control_chain_complete'] else 'open'} |",
        f"| Retail camera follow | {'positive' if frontier['retail_camera_follow_ready'] else 'open'} |",
        f"| Final smoke runnable | {'positive' if frontier['final_playable_smoke_currently_runnable'] else 'open'} |",
        "",
        "## Development lanes",
        "",
        "| Lane | Owner | Queue state | Consumers |",
        "| --- | --- | --- | --- |",
    ]

    for lane in registry["lanes"]:
        state_text = ", ".join(f"{task_id}={queues[task_id]['state']}" for task_id in lane["queue_ids"])
        consumers = ", ".join(lane["consumers"])
        lines.append(f"| {lane['id']} | {lane['owner']} | {state_text} | {consumers} |")

    available = [
        (task_id, row["state"])
        for task_id, row in queues.items()
        if is_available(row["state"])
    ]
    lines += ["", "## Parallel work available now", ""]
    if available:
        lines.extend(f"- `{task_id}` — `{state}`" for task_id, state in available)
    else:
        lines.append("- None.")

    terminal_gates = [
        frontier["fun_00766510_p1_complete"],
        frontier["retail_control_chain_complete"],
        frontier["retail_camera_follow_ready"],
        frontier["final_playable_smoke_currently_runnable"],
        frontier["playable_slice_complete"],
    ]
    closed = sum(bool(value) for value in terminal_gates)
    lines += [
        "",
        "## Blocker burndown",
        "",
        f"Terminal milestone gates closed: **{closed}/{len(terminal_gates)}**.",
        "",
        "The provider count is an architectural metric. It changes only when a complete external callback boundary is removed without dropping source-visible behavior.",
        "",
        "## Coordination rules",
        "",
        "- Live status comes only from the canonical execution JSON.",
        "- Lane ownership comes from `coordination/lane_ownership.json`; it does not override live status.",
        "- One canonical PR per blocker; at most one stacked successor.",
        "- Close superseded PRs after any unique evidence has been transplanted.",
        "- Re-read fresh `main` before substantial work and again before merge.",
        "- Do not add new phase-numbered GitHub Actions workflows; extend stable workflow families instead.",
        "",
    ]
    return "\n".join(lines)


def human_phase_warnings(canonical_phase: int) -> list[str]:
    warnings: list[str] = []
    for rel, pattern in HUMAN_PHASE_PATTERNS.items():
        path = ROOT / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        match = pattern.search(text)
        if match and int(match.group(1)) != canonical_phase:
            warnings.append(
                f"{rel}: human summary says Phase {match.group(1)}, canonical execution state says Phase {canonical_phase}"
            )
    return warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true")
    group.add_argument("--write", action="store_true")
    parser.add_argument("--strict-human-docs", action="store_true")
    args = parser.parse_args()

    execution = load_json(EXECUTION_PATH)
    registry = load_json(LANES_PATH)
    validate(execution, registry)
    rendered = render(execution, registry)
    warnings = human_phase_warnings(execution["main_frontier"]["phase"])

    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)

    if args.strict_human_docs and warnings:
        return 3

    if args.write:
        STATUS_PATH.write_text(rendered, encoding="utf-8")
        return 0

    if args.check:
        current = STATUS_PATH.read_text(encoding="utf-8") if STATUS_PATH.exists() else ""
        if current != rendered:
            diff = difflib.unified_diff(
                current.splitlines(),
                rendered.splitlines(),
                fromfile=str(STATUS_PATH),
                tofile="generated",
                lineterm="",
            )
            print("\n".join(diff), file=sys.stderr)
            return 2
        return 0

    sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
