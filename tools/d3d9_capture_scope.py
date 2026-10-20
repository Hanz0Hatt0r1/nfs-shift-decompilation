#!/usr/bin/env python3
"""Bound the SHIFT D3D9 -> Vulkan work to commands observed in retail captures.

An audit JSON is sufficient for the command inventory. Supply --capture to
enumerate observed render/sampler state IDs from original JSONL; binary payloads
and capture-local pointers are deliberately not stored in the report.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

FORMAT = "SHIFT.D3D9CapturedUsageScope/1"

# Only these game-rendering calls belong to the first-draw implementation lane.
# Other observed calls are retained in the inventory; they are not silently
# declared supported just because a D3D9 proxy was able to record them.
FIRST_DRAW = (
    "create_vertex_buffer", "create_index_buffer", "create_vertex_declaration",
    "create_vertex_shader", "create_pixel_shader", "create_texture",
    "set_stream_source", "set_indices", "set_vertex_declaration",
    "set_vertex_shader", "set_pixel_shader",
    "set_vertex_shader_constant_f", "set_pixel_shader_constant_f",
    "set_texture", "set_render_state", "set_sampler_state",
    "set_render_target", "set_depth_stencil_surface", "set_viewport",
    "begin_scene", "draw_indexed_primitive", "end_scene",
)
# These are the only retail operations whose Vulkan submissions are currently
# established by the pinned v194/v215 runtime evidence. They DO NOT constitute
# a drawn retail triangle, frontend, or a playable race.
VERIFIED_SUBMISSIONS = ("clear", "present_result")

RENDER_OPERATIONS = set(FIRST_DRAW) | set(VERIFIED_SUBMISSIONS) | {
    "create_cube_texture", "create_device_begin", "create_device_result",
}
STATE_EVENTS = {"set_render_state": "state", "set_sampler_state": "state"}


def normalize_state(value):
    """Only bounded integer state IDs are comparable across captures."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and 0 <= value <= 0xffff:
        return value
    if isinstance(value, str):
        try:
            number = int(value, 0)
        except ValueError:
            return None
        return number if 0 <= number <= 0xffff else None
    return None


def read_audit(path: Path) -> Counter:
    obj = json.loads(path.read_text(encoding="utf-8"))
    counts = obj.get("audit", obj).get("event_counts")
    if not isinstance(counts, dict):
        raise ValueError(f"{path}: expected audit.event_counts")
    normalized = Counter()
    for name, count in counts.items():
        if not isinstance(name, str) or type(count) is not int or count < 0:
            raise ValueError(f"{path}: invalid event counter")
        normalized[name] = count
    return normalized


def read_capture(path: Path) -> tuple[Counter, dict, int]:
    counts = Counter()
    state_ids = defaultdict(set)
    invalid = 0
    with path.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                invalid += 1
                continue
            if not isinstance(event, dict) or not isinstance(event.get("event"), str):
                invalid += 1
                continue
            name = event["event"]
            counts[name] += 1
            if name in STATE_EVENTS:
                state = normalize_state(event.get(STATE_EVENTS[name]))
                if state is not None:
                    state_ids[name].add(state)
    return counts, {name: sorted(values) for name, values in sorted(state_ids.items())}, invalid


def inventory(counts: Counter, state_ids: dict | None = None, malformed: int = 0) -> dict:
    observed = {name: count for name, count in sorted(counts.items()) if count > 0}
    scoped = {name: observed[name] for name in FIRST_DRAW if name in observed}
    return {
        "format": FORMAT,
        "status": "capture-inventory" if observed else "insufficient-evidence",
        "observed_event_counts": observed,
        "first_draw_command_counts": scoped,
        "first_draw_commands_not_observed": [
            name for name in FIRST_DRAW if name not in observed
        ],
        "first_draw_commands_not_yet_vulkan_verified": list(scoped),
        "known_vulkan_submission_scope": list(VERIFIED_SUBMISSIONS),
        "state_ids": state_ids or {},
        "malformed_capture_lines": malformed,
        "retail_draw_translation_proven": False,
        "frontend_proven": False,
        "notes": [
            "Commands are captured from original PC retail under PortProton, not Linux guest execution.",
            "Clear/Present Vulkan submissions were recorded separately by v194/v215; no guest draw was submitted.",
            "No API or state is considered equivalent merely because a capture contains it.",
            "Do not implement uncaptured D3D9 methods without new retail evidence.",
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, help="committed retail capture audit JSON")
    parser.add_argument("--capture", type=Path, help="original raw JSONL on the retail host")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--strict-capture", action="store_true",
                        help="fail on malformed raw capture events")
    args = parser.parse_args(argv)
    if not args.audit and not args.capture:
        parser.error("provide --audit and/or --capture")
    try:
        declared = read_audit(args.audit) if args.audit else None
        state_ids = {}
        malformed = 0
        actual = None
        if args.capture:
            actual, state_ids, malformed = read_capture(args.capture)
        if declared is not None and actual is not None:
            mismatched = {
                name: {"audit": count, "capture": actual[name]}
                for name, count in declared.items()
                if actual[name] != count
            }
            if mismatched:
                raise ValueError(f"retail capture/audit count mismatch: {mismatched}")
        result = inventory(actual if actual is not None else declared, state_ids, malformed)
        result["inputs"] = {
            "audit": str(args.audit) if args.audit else None,
            "capture": str(args.capture) if args.capture else None,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                               encoding="utf-8")
        print(json.dumps(result, sort_keys=True))
        return int(result["status"] != "capture-inventory"
                   or (args.strict_capture and malformed != 0))
    except (ValueError, OSError, TypeError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
