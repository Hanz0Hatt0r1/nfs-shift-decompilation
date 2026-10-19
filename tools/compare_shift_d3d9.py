#!/usr/bin/env python3
"""Compare stable D3D9 call contracts from retail proxy JSONL and Linux evidence.

Pointer identities, timestamps, capture-local resource paths, and host frames are
intentionally excluded: they are not comparable across two processes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

FORMAT = "SHIFT.D3D9TraceComparison/1"
FIELDS = {
    "create_texture": ("width", "height", "levels", "usage", "format", "pool"),
    "create_device_begin": ("adapter", "device_type", "behavior_flags"),
    "create_device_result": ("success", "hresult"),
    "clear": ("rect_count", "clear_flags", "color", "depth", "stencil"),
    "draw_indexed_primitive": (
        "primitive_type", "base_vertex_index", "min_vertex_index",
        "num_vertices", "start_index", "primitive_count"
    ),
    "set_texture": ("sampler", "resource_signature"),
}
D3DX_FAILURE = re.compile(
    r"unimplemented PE import d3dx9_41\.dll!D3DXCreateTexture[^\n]*?\bargs=\[([^\]]+)\]",
    re.IGNORECASE,
)


def canonical(value):
    """Canonicalize hexadecimal integer strings only, never opaque identifiers."""
    if isinstance(value, str) and re.fullmatch(r"0[xX][0-9a-fA-F]+", value):
        return int(value, 16)
    return value


def event_contract(event: dict) -> dict | None:
    kind = event.get("event")
    if kind not in FIELDS:
        return None
    return {
        "event": kind,
        "fields": {key: canonical(event[key]) for key in FIELDS[kind] if key in event},
    }


def linux_failure_request(text: str) -> list[dict]:
    """v173 diagnostic yields an uncompleted D3DX request, NOT a created texture."""
    matched = D3DX_FAILURE.search(text)
    if not matched:
        return []
    try:
        arguments = [int(item.strip(), 0) for item in matched.group(1).split(",")]
    except ValueError:
        return []
    if len(arguments) != 8:
        return []
    return [{
        "event": "create_texture",
        "fields": dict(zip(FIELDS["create_texture"], arguments[1:7])),
        "observation": "request-only",
    }]


def load_events(path: Path, kinds: set[str], maximum: int) -> tuple[list[dict], str, int]:
    """Bound memory even when the raw retail capture is hundreds of MB."""
    if maximum < 1:
        raise ValueError("--max-events must be a positive integer")
    selected: list[dict] = []
    rejected = 0
    mode = "jsonl"
    with path.open("r", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                # Raw Linux probe has a pretty-printed bootstrap object and a
                # diagnostic line. It is NOT an equivalent D3D9 event stream.
                mode = "probe-diagnostic"
                break
            if not isinstance(obj, dict):
                rejected += 1
                continue
            contract = event_contract(obj)
            if contract is not None and contract["event"] in kinds:
                selected.append(contract)
                if len(selected) >= maximum:
                    break
    if mode == "probe-diagnostic":
        raw = path.read_text(encoding="utf-8", errors="replace")
        selected = [item for item in linux_failure_request(raw) if item["event"] in kinds]
    return selected, mode, rejected


def compare(reference: list[dict], candidate: list[dict], candidate_mode: str) -> dict:
    # Subsequence mode: Linux may expose only a bounded prefix/subset of the
    # reference capture. Matches do not establish frame or resource parity.
    i = 0
    matched_positions = []
    first_missing = None
    for item in candidate:
        while i < len(reference) and (
            reference[i]["event"], reference[i]["fields"]
        ) != (item["event"], item["fields"]):
            i += 1
        if i >= len(reference):
            first_missing = item
            break
        matched_positions.append(i)
        i += 1
    if not candidate or not reference:
        status = "insufficient-evidence"
    elif first_missing is not None:
        status = "not-found"
    elif candidate_mode == "probe-diagnostic":
        status = "request-only-match"
    else:
        status = "matched-subsequence"
    return {
        "format": FORMAT,
        "status": status,
        "comparison_scope": "stable API fields and event order only",
        "reference_event_count": len(reference),
        "candidate_event_count": len(candidate),
        "matched_event_count": len(matched_positions),
        "matched_reference_indices": matched_positions[:20],
        "first_unmatched_candidate": first_missing,
        "candidate_mode": candidate_mode,
        "semantic_parity_proven": False,
        "warnings": (
            ["Linux evidence is a failed D3DX call request, not a successful texture creation."]
            if candidate_mode == "probe-diagnostic" else []
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True, type=Path, help="original retail proxy JSONL")
    parser.add_argument("--candidate", required=True, type=Path, help="Linux JSONL or v173-style probe log")
    parser.add_argument("--event", action="append", choices=sorted(FIELDS),
                        help="event type to compare; defaults to create_texture")
    parser.add_argument("--max-events", type=int, default=2000)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--strict", action="store_true", help="exit nonzero if no match")
    args = parser.parse_args(argv)
    try:
        events = set(args.event or ["create_texture"])
        ref, ref_mode, ref_bad = load_events(args.reference, events, args.max_events)
        cand, cand_mode, cand_bad = load_events(args.candidate, events, args.max_events)
        if ref_mode != "jsonl":
            parser.error("reference must be a retail proxy JSONL event stream")
        report = compare(ref, cand, cand_mode)
        report["reference_unstructured_lines"] = ref_bad
        report["candidate_unstructured_lines"] = cand_bad
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(report, sort_keys=True))
        return int(args.strict and report["status"] not in (
            "matched-subsequence", "request-only-match"
        ))
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    sys.exit(main())
