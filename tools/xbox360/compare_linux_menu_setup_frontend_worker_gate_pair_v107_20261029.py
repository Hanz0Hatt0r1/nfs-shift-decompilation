#!/usr/bin/env python3
"""Compare immediate queue-pop returns and one-shot PPC r3 watches across backends."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


PULSES = [("Start", 5, 17), ("A", 21, 33), ("Start", 37, 49)]
INPUT_FIELDS = ("buttons", "host_buttons", "previous", "start_edge", "a_edge")
CALLER = "0x822fdf88"


class ComparisonError(ValueError):
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _records(path: Path) -> list[tuple[str, dict[str, Any]]]:
    records = []
    for number, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
        if not line.startswith("P1_") or " {" not in line:
            continue
        marker, raw = line.split(" ", 1)
        try:
            records.append((marker, json.loads(raw)))
        except json.JSONDecodeError as exc:
            raise ComparisonError(f"{path}:{number}: invalid event JSON") from exc
    return records


def _host_symbol(row: dict[str, Any]) -> str | None:
    value = row.get("host_symbol_after_return") or row.get("host_symbol")
    if not value:
        return None
    return re.sub(r" in section \.ltext of .+$", "", value).strip()


def _capture(run_dir: Path, backend: str) -> dict[str, Any]:
    metadata = json.loads((run_dir / "run_metadata.json").read_text())
    if (metadata.get("backend") != backend or metadata.get("gdb_exit") != 0
            or metadata.get("guest_memory_modified_by_probe") is not False):
        raise ComparisonError(f"{run_dir}: failed run or mutating probe")
    pulses = [(row.get("button"), row.get("observed_down_state2_index"),
               row.get("observed_up_state2_index"))
              for row in metadata.get("controller_pulses", [])]
    if pulses != PULSES:
        raise ComparisonError(f"{run_dir}: incomplete or misaligned button schedule")

    log = Path(metadata.get("events_log", ""))
    if not log.is_file() or metadata.get("events_log_sha256") != _sha256(log):
        raise ComparisonError(f"{run_dir}: missing or hash-mismatched GDB log")
    records = _records(log)
    updates = [row for marker, row in records if marker == "P1_STATE2_UPDATE"]
    if ([row.get("state2_index") for row in updates] != list(range(1, 50))
            or any(row.get("state") != 2 for row in updates)):
        raise ComparisonError(f"{run_dir}: did not remain in state 2 through update 49")

    calls, returns = {}, {}
    watch_events, summaries = [], []
    for marker, row in records:
        if marker == "P1_WORKER_GATE_CALL" and row.get("function") == "sub_822E1910":
            calls[row["call_index"]] = row
        elif marker == "P1_WORKER_GATE_RETURN" and row.get("function") == "sub_822E1910":
            returns[row["call_index"]] = row
        elif marker == "P1_CONTEXT_R3_WRITE_WATCH":
            watch_events.append(row)
        elif marker == "P1_CONTEXT_R3_WATCH_SUMMARY":
            summaries.append(row)
    if set(calls) != set(returns):
        raise ComparisonError(f"{run_dir}: queue-pop calls and returns do not pair")
    if len(watch_events) != 1 or len(summaries) != 1:
        raise ComparisonError(f"{run_dir}: missing one-shot r3 watch evidence")
    watch = watch_events[0]
    if (watch.get("guest_memory_modified_by_probe") is not False
            or watch.get("context_r3_before") is None
            or watch.get("context_r3_after") is None
            or summaries[0].get("watchpoints") != 1):
        raise ComparisonError(f"{run_dir}: invalid r3 watch result")

    samples: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for index, call in calls.items():
        if call.get("caller_lr") != CALLER:
            continue
        returned = returns[index]
        inp = call.get("input") or {}
        key = (call.get("button"), tuple(inp.get(field) for field in INPUT_FIELDS),
               call.get("caller_lr"), call.get("args_r3_r10", [None])[0])
        samples[key].append({
            "return_r3": returned.get("return_r3"),
            "live_context_gpr3": returned.get("live_context_gpr3"),
            "live_context_matches_saved": returned.get("live_context_matches_saved"),
            "host_continuation": _host_symbol(returned),
        })
    if not samples or any(
            row["live_context_gpr3"] is None
            or row["live_context_matches_saved"] is not True
            or row["return_r3"] != row["live_context_gpr3"]
            for rows in samples.values() for row in rows):
        raise ComparisonError(f"{run_dir}: immediate live-context return evidence is incomplete")

    hashes = metadata.get("hashes", {})
    return {
        "backend": backend,
        "run_dir": str(run_dir),
        "duration_seconds": metadata.get("duration_seconds"),
        "event_log_sha256": metadata["events_log_sha256"],
        "xex_sha256": hashes.get("xex"),
        "host_sha256": hashes.get("host"),
        "runtime_sha256": hashes.get("runtime"),
        "plugin_sha256": hashes.get("plugin"),
        "runner_sha256": metadata.get("runner_sha256"),
        "trace_sha256": metadata.get("trace_sha256"),
        "game_data_root": metadata.get("game_data_root"),
        "input_pulses": pulses,
        "state2_update_count": len(updates),
        "queue_pop_samples": {
            repr(key): sorted(rows, key=lambda row: json.dumps(row, sort_keys=True))
            for key, rows in samples.items()
        },
        "r3_watch": {
            "before": watch.get("context_r3_before"),
            "after": watch.get("context_r3_after"),
            "guest_lr": watch.get("context_guest_lr"),
            "host_symbol": _host_symbol(watch),
            "guest_memory_modified_by_probe": watch.get("guest_memory_modified_by_probe"),
        },
    }


def compare_runs(xenos_dir: Path, native_dir: Path) -> dict[str, Any]:
    xenos, native = _capture(xenos_dir, "xenos"), _capture(native_dir, "shift-native")
    for field in ("xex_sha256", "host_sha256", "runtime_sha256", "runner_sha256",
                  "trace_sha256", "game_data_root", "input_pulses"):
        if xenos[field] != native[field]:
            raise ComparisonError(f"runs do not share {field}")
    if xenos["plugin_sha256"] == native["plugin_sha256"]:
        raise ComparisonError("backend plugin hashes unexpectedly match")

    left, right = xenos["queue_pop_samples"], native["queue_pop_samples"]
    shared = set(left) & set(right)
    differences = [{"key": key, "xenos": left[key], "shift_native": right[key]}
                   for key in sorted(shared) if left[key] != right[key]]
    watch_matches = xenos["r3_watch"] == native["r3_watch"]
    return {
        "schema": "shift.xbox360.linux-menu-worker-gate-pair.v107",
        "result": {
            "same_retail_xex_host_runtime_and_capture": True,
            "same_input_schedule": True,
            "both_remained_in_menu_setup_state_2_through_index_49": True,
            "shared_queue_pop_sample_keys": len(shared),
            "queue_pop_outcomes_match": bool(shared) and not differences,
            "live_context_r3_matches_return_value": all(
                row["return_r3"] == row["live_context_gpr3"]
                and row["live_context_matches_saved"] is True
                for run in (xenos, native)
                for rows in run["queue_pop_samples"].values() for row in rows
                if row["live_context_gpr3"] is not None),
            "context_r3_write_outcome_matches": watch_matches,
            "backend_specific_cause_established": bool(differences) or not watch_matches,
        },
        "runs": {"xenos": xenos, "shift-native": native},
        "comparison": {
            "queue_pop_outcome_differences": differences,
            "xenos_only_sample_keys": sorted(set(left) - shared),
            "shift_native_only_sample_keys": sorted(set(right) - shared),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xenos_run", type=Path)
    parser.add_argument("native_run", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rendered = json.dumps(compare_runs(args.xenos_run, args.native_run), indent=2,
                           sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered)
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
