#!/usr/bin/env python3
"""Summarise a Menu Setup scene-gate capture run directory.

Reads a run directory produced by
``capture_linux_menu_setup_frontend_worker_gate_v112.py`` (or any later runner
that emits the same ``P1_*`` JSON-lines events) and prints a single JSON
summary of the facts the frontend frontier depends on:

- how many Menu Setup ``state 2`` updates were observed and over what interval;
- whether the ``MainMenu`` scene gate at ``scene+8`` was set and/or cleared;
- how many GUI event-queue constructors/opens/polls were seen, and how many
  enqueues (zero is reported as ``0`` only when the event family exists;
  otherwise it is reported as unknown, never invented). Concretely: the current
  traces instrument the *dequeue* side only, so "0 enqueues" is NOT observable
  from them. The honest statement the frontier can make is "the GUI queue was
  polled N times; no enqueue path was instrumented", which is what
  ``gui_queue.enqueue_evidence`` reports;
- which retail controller edges and input predicates were captured;
- the recorded artifact hashes from ``run_metadata.json``.

The reader is strictly read-only: it never opens a run directory for writing.

Usage:
    python3 analyse_menu_setup_scene_gate_run_20261029.py RUN_DIR [RUN_DIR ...]
    python3 analyse_menu_setup_scene_gate_run_20261029.py --json RUN_DIR
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Iterable

# Event families whose absence must not be read as a zero count. A capture can
# only claim "zero enqueues" if the trace actually instruments an enqueue path.
_OPTIONAL_COUNT_FAMILIES = {
    "gui_queue_enqueue_calls": (
        "P1_GUI_QUEUE_ENQUEUE_CALL",
        "P1_MAIN_MENU_GUI_EVENT_QUEUE_ENQUEUE",
    ),
    "gui_queue_direct_appends": ("P1_GUI_QUEUE_DIRECT_APPEND",),
}

_REQUIRED_FAMILIES = (
    "P1_STATE2_UPDATE",
    "P1_MAINMENU_SCENE_GATE_METHOD_CALL",
    "P1_SCENE_GATE_FIELD_WRITE",
)


def _iter_events(streams: Iterable[Any]) -> Iterable[tuple[str, dict]]:
    """Yield (event_name, payload) from gdb.log files and stream objects."""
    for stream in streams:
        if isinstance(stream, (str, Path)):
            path = Path(stream)
            if path.is_dir():
                path = path / "gdb.log"
            if not path.is_file():
                continue
            handle = path.open("r", encoding="utf-8", errors="replace")
        else:
            handle = stream
        with handle if hasattr(handle, "close") else _NullCtx(handle):
            for line in handle:
                line = line.rstrip("\n")
                if not line.startswith("P1_"):
                    continue
                name, _, rest = line.partition(" ")
                rest = rest.strip()
                if not rest.startswith("{"):
                    yield name, {}
                    continue
                try:
                    payload = json.loads(rest)
                except json.JSONDecodeError:
                    yield name, {}
                    continue
                yield name, payload if isinstance(payload, dict) else {}


class _NullCtx:
    """Context manager that leaves a borrowed stream open."""

    def __init__(self, stream):
        self._stream = stream

    def __enter__(self):
        return self._stream

    def __exit__(self, *exc):
        return False


def _load_metadata(run_dir: Path) -> dict:
    path = run_dir / "run_metadata.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def analyse_run(run_dir: str | Path) -> dict:
    """Return the JSON-serialisable summary for one run directory."""
    run_dir = Path(run_dir)
    counts: dict[str, int] = {}
    state2_times: list[float] = []
    gate_set_calls: list[dict] = []
    gate_clear_calls: list[dict] = []
    gate_writes: list[dict] = []
    input_edges: list[str] = []
    predicate_values: list[Any] = []

    for name, payload in _iter_events([run_dir]):
        counts[name] = counts.get(name, 0) + 1
        if name == "P1_STATE2_UPDATE":
            value = payload.get("elapsed_seconds")
            if isinstance(value, (int, float)):
                state2_times.append(float(value))
        elif name == "P1_MAINMENU_SCENE_GATE_METHOD_CALL":
            function = str(payload.get("function", payload.get("guest_function_address", "")))
            entry = {
                "elapsed_seconds": payload.get("elapsed_seconds"),
                "function": function,
                "caller_lr": payload.get("caller_lr"),
            }
            if "8FF8" in function.upper() or "CLEAR" in function.upper():
                gate_clear_calls.append(entry)
            else:
                gate_set_calls.append(entry)
        elif name == "P1_SCENE_GATE_FIELD_WRITE":
            gate_writes.append(
                {
                    "elapsed_seconds": payload.get("elapsed_seconds"),
                    "before": payload.get("before"),
                    "after": payload.get("after"),
                    "host_symbol": payload.get("host_symbol"),
                }
            )
        elif name == "P1_RETAIL_CONTROLLER_EDGE_STATE":
            button = payload.get("button")
            if button and button not in input_edges:
                input_edges.append(str(button))
        elif name == "P1_RETAIL_INPUT_PREDICATE":
            predicate_values.append(payload.get("predicate"))

    # Interval facts for state 2.
    state2_first = state2_times[0] if state2_times else None
    state2_last = state2_times[-1] if state2_times else None
    state2_span = round(state2_last - state2_first, 3) if state2_times else None
    gaps = [
        round(b - a, 3) for a, b in zip(state2_times, state2_times[1:]) if b >= a
    ]

    optional: dict[str, Any] = {}
    for label, families in _OPTIONAL_COUNT_FAMILIES.items():
        observed = sum(counts.get(family, 0) for family in families)
        instrumented = any(counts.get(family, 0) > 0 for family in families)
        optional[label] = observed if instrumented else "unknown: family not emitted"

    # Enqueue observability is a property of the trace, not of the guest. The
    # current captures breakpoint the dequeue/poll path, so a missing enqueue
    # family means "not instrumented", never "the guest enqueued nothing".
    polls = counts.get("P1_MAIN_MENU_GUI_EVENT_QUEUE_PROCESS", 0)
    enqueue_instrumented = any(
        counts.get(family, 0) > 0
        for families in _OPTIONAL_COUNT_FAMILIES.values()
        for family in families
    )
    if enqueue_instrumented:
        enqueue_evidence = "instrumented"
    elif polls:
        enqueue_evidence = (
            "not instrumented: the trace observes GUI queue polls only; "
            "absence of enqueue events cannot be read as zero enqueues"
        )
    else:
        enqueue_evidence = "unknown: neither enqueue nor poll path observed"

    missing = [family for family in _REQUIRED_FAMILIES if counts.get(family, 0) == 0]
    metadata = _load_metadata(run_dir)

    return {
        "run_dir": str(run_dir),
        "backend": metadata.get("backend"),
        "gdb_exit": metadata.get("gdb_exit"),
        "guest_memory_modified_by_probe": metadata.get("guest_memory_modified_by_probe"),
        "artifact_hashes": metadata.get("hashes"),
        "state2": {
            "updates": len(state2_times),
            "first_elapsed_seconds": state2_first,
            "last_elapsed_seconds": state2_last,
            "span_seconds": state2_span,
            "max_gap_seconds": max(gaps) if gaps else None,
        },
        "scene_gate": {
            "set_calls": len(gate_set_calls),
            "clear_calls": len(gate_clear_calls),
            "field_writes": len(gate_writes),
            "writes": gate_writes,
            "set_call_details": gate_set_calls[:5],
            "clear_call_details": gate_clear_calls[:5],
        },
        "gui_queue": {
            "ctor_calls": counts.get("P1_GUI_QUEUE_CTOR_CALL", 0),
            "ctor_returns": counts.get("P1_GUI_QUEUE_CTOR_RETURN", 0),
            "open_calls": counts.get("P1_GUI_QUEUE_OPEN_CALL", 0),
            "process_calls": polls,
            "enqueue_evidence": enqueue_evidence,
            **optional,
        },
        "input": {
            "controller_edges": input_edges,
            "predicate_samples": len(predicate_values),
            "predicate_values": sorted({str(v) for v in predicate_values}),
        },
        "missing_required_families": missing,
        "event_counts": dict(sorted(counts.items())),
    }


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in argv
    argv = [a for a in argv if a != "--json"]
    if not argv:
        print(__doc__.strip(), file=sys.stderr)
        return 2

    summaries = [analyse_run(path) for path in argv]
    result: Any = summaries[0] if len(summaries) == 1 else summaries
    if as_json or True:  # stdout is always JSON; --json kept for symmetry
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
