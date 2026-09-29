#!/usr/bin/env python3
"""Validate concrete AIW -> runtime waypoint graph evidence exported by the track analyzer."""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

FORMAT = "SHIFT-LIVE-MEMORY-AIW-RUNTIME-GRAPH/1"


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise SystemExit(f"missing input: {path}")
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def as_int(row: dict[str, str], key: str) -> int:
    try:
        return int(row[key], 0)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid integer field {key!r}: {row!r}") from exc


def as_float(row: dict[str, str], key: str, default: float = 0.0) -> float:
    value = row.get(key)
    if value in (None, ""):
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"invalid float field {key!r}: {row!r}") from exc


def edge_key(row: dict[str, str]) -> tuple[str, int, int]:
    return (
        row["aiw_source"],
        as_int(row, "from_waypoint"),
        as_int(row, "to_waypoint"),
    )


def build_source_summary(
    source: str,
    waypoints: list[dict[str, str]],
    next_edges: list[dict[str, str]],
    runtime_edges: list[dict[str, str]],
    position_tolerance: float,
) -> tuple[dict, list[dict]]:
    source_waypoints = [r for r in waypoints if r.get("source") == source]
    source_next = [r for r in next_edges if r.get("aiw_source") == source]
    source_runtime = [r for r in runtime_edges if r.get("aiw_source") == source]

    waypoint_indices = {
        as_int(row, "index") for row in source_waypoints
    }
    declared_links = [
        row for row in source_waypoints
        if as_int(row, "next") in waypoint_indices
    ]
    normalized_keys = {
        edge_key(row) for row in source_next
    }
    runtime_groups: dict[tuple[str, int, int], list[dict[str, str]]] = defaultdict(list)
    for row in source_runtime:
        runtime_groups[edge_key(row)].append(row)

    missing_keys = sorted(normalized_keys - set(runtime_groups))
    ambiguous_groups = {
        key: rows for key, rows in runtime_groups.items() if len(rows) > 1
    }

    deltas = [as_int(row, "runtime_delta") for row in source_runtime]
    positive = [d for d in deltas if d > 0 and 4 <= d <= 0x10000]
    negative = [d for d in deltas if d < 0]
    dominant_stride, dominant_stride_count = (
        Counter(positive).most_common(1)[0] if positive else (0, 0)
    )

    group_rows: list[dict] = []
    stride_groups = 0
    negative_groups = 0
    for key in sorted(runtime_groups):
        rows = runtime_groups[key]
        errors = [as_float(row, "position_match_error") for row in rows]
        min_index = min(range(len(rows)), key=lambda i: (
            errors[i],
            abs(as_int(rows[i], "runtime_delta") - dominant_stride)
            if dominant_stride else abs(as_int(rows[i], "runtime_delta")),
            as_int(rows[i], "from_runtime_address"),
            as_int(rows[i], "to_runtime_address"),
        ))
        min_row = rows[min_index]
        group_deltas = sorted({as_int(row, "runtime_delta") for row in rows})
        has_stride = bool(
            dominant_stride
            and any(as_int(row, "runtime_delta") == dominant_stride for row in rows)
        )
        has_negative = any(d < 0 for d in group_deltas)
        if has_stride:
            stride_groups += 1
        if has_negative:
            negative_groups += 1
        group_rows.append({
            "aiw_source": source,
            "from_waypoint": key[1],
            "to_waypoint": key[2],
            "candidate_count": len(rows),
            "runtime_delta_values": json.dumps(group_deltas, separators=(",", ":")),
            "min_position_match_error": min(errors) if errors else 0.0,
            "min_error_from_runtime_address": as_int(
                min_row, "from_runtime_address"
            ),
            "min_error_to_runtime_address": as_int(
                min_row, "to_runtime_address"
            ),
            "min_error_runtime_delta": as_int(min_row, "runtime_delta"),
            "min_error_matches_stride": bool(
                dominant_stride
                and as_int(min_row, "runtime_delta") == dominant_stride
            ),
            "position_within_tolerance": bool(
                errors and min(errors) <= position_tolerance
            ),
        })

    runtime_edge_count = len(source_runtime)
    normalized_edge_count = len(source_next)
    grouped_edge_count = len(runtime_groups)
    coverage = (
        grouped_edge_count / normalized_edge_count
        if normalized_edge_count else 1.0
    )
    unambiguous_group_count = sum(
        1 for rows in runtime_groups.values() if len(rows) == 1
    )
    unambiguous_coverage = (
        unambiguous_group_count / normalized_edge_count
        if normalized_edge_count else 1.0
    )
    stride_coverage = (
        stride_groups / grouped_edge_count
        if grouped_edge_count else 0.0
    )

    errors = [as_float(row, "position_match_error") for row in source_runtime]
    source_status = (
        "no-edges"
        if normalized_edge_count == 0
        else "missing-runtime"
        if runtime_edge_count == 0
        else "complete-unambiguous"
        if coverage == 1.0 and not ambiguous_groups
        else "complete-ambiguous"
        if coverage == 1.0
        else "partial"
    )

    summary = {
        "source": source,
        "waypoint_count": len(source_waypoints),
        "declared_next_edge_count": len(declared_links),
        "normalized_next_edge_count": normalized_edge_count,
        "runtime_edge_candidate_count": runtime_edge_count,
        "runtime_edge_group_count": grouped_edge_count,
        "missing_runtime_edge_count": len(missing_keys),
        "missing_runtime_edges": [
            {"from_waypoint": key[1], "to_waypoint": key[2]}
            for key in missing_keys
        ],
        "ambiguous_edge_group_count": len(ambiguous_groups),
        "max_candidates_per_edge": max(
            (len(rows) for rows in runtime_groups.values()),
            default=0,
        ),
        "runtime_matched_waypoint_count": len({
            as_int(row, "from_waypoint") for row in source_runtime
        } | {
            as_int(row, "to_waypoint") for row in source_runtime
        }),
        "forward_runtime_edge_count": sum(1 for d in deltas if d > 0),
        "negative_runtime_edge_count": len(negative),
        "dominant_forward_stride": dominant_stride,
        "dominant_forward_stride_count": dominant_stride_count,
        "dominant_forward_stride_coverage": (
            sum(1 for d in positive if d == dominant_stride) / len(positive)
            if positive else 0.0
        ),
        "runtime_edge_group_stride_coverage": stride_coverage,
        "exact_stride_group_count": stride_groups,
        "negative_delta_group_count": negative_groups,
        "runtime_edge_coverage": coverage,
        "unambiguous_edge_coverage": unambiguous_coverage,
        "position_match_error_max": max(errors, default=0.0),
        "position_match_error_mean": (
            statistics.fmean(errors) if errors else 0.0
        ),
        "position_match_error_within_tolerance": bool(
            errors and max(errors) <= position_tolerance
        ) if errors else True,
        "status": source_status,
    }
    return summary, group_rows


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Validate AIW runtime graph evidence emitted by analyze_track_paths.py"
    )
    ap.add_argument("analysis_dir", type=Path)
    ap.add_argument(
        "--out",
        type=Path,
        help="output JSON; defaults to <analysis_dir>/aiw_runtime_graph_validation.json",
    )
    ap.add_argument(
        "--position-tolerance",
        type=float,
        default=0.05,
        help="position-match error threshold used for the descriptive tolerance flag",
    )
    ap.add_argument(
        "--require-complete",
        action="store_true",
        help="return exit code 2 when any source lacks a runtime candidate for an explicit edge",
    )
    ap.add_argument(
        "--require-unambiguous",
        action="store_true",
        help="return exit code 2 when any explicit edge has multiple runtime candidates",
    )
    args = ap.parse_args()

    if args.position_tolerance <= 0 or not math.isfinite(args.position_tolerance):
        ap.error("--position-tolerance must be finite and > 0")

    root = args.analysis_dir
    manifest_path = root / "track_path_analysis.json"
    manifest = {}
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    waypoints = load_csv(root / "aiw_waypoints.csv")
    next_edges = load_csv(root / "aiw_next_edges.csv")
    runtime_edges = load_csv(root / "aiw_runtime_edges.csv")

    sources = sorted({
        row.get("source") for row in waypoints if row.get("source")
    } | {
        row.get("aiw_source") for row in next_edges if row.get("aiw_source")
    } | {
        row.get("aiw_source") for row in runtime_edges if row.get("aiw_source")
    })

    source_summaries = []
    group_rows = []
    for source in sources:
        summary, groups = build_source_summary(
            source, waypoints, next_edges, runtime_edges,
            args.position_tolerance,
        )
        source_summaries.append(summary)
        group_rows.extend(groups)

    expected_runtime_edges = manifest.get("aiw_runtime_edge_count")
    manifest_runtime_edge_count_match = (
        expected_runtime_edges is None
        or int(expected_runtime_edges) == len(runtime_edges)
    )

    result = {
        "format": FORMAT,
        "analysis_dir": str(root),
        "source_count": len(source_summaries),
        "runtime_edge_candidate_count": len(runtime_edges),
        "runtime_edge_group_count": len(group_rows),
        "complete_source_count": sum(
            1 for row in source_summaries
            if row["status"] in ("complete-unambiguous", "complete-ambiguous")
        ),
        "unambiguous_source_count": sum(
            1 for row in source_summaries
            if row["status"] == "complete-unambiguous"
        ),
        "ambiguous_edge_group_count": sum(
            int(row["ambiguous_edge_group_count"]) for row in source_summaries
        ),
        "manifest_runtime_edge_count": expected_runtime_edges,
        "manifest_runtime_edge_count_match": manifest_runtime_edge_count_match,
        "sources": source_summaries,
        "notes": [
            "This validator classifies exported runtime edge candidates; it does not choose a semantic track-path interpretation.",
            "A source is complete when every normalized AIW next edge has at least one runtime-address candidate.",
            "An ambiguous edge has multiple runtime-address candidates for the same explicit AIW edge and requires more capture evidence before collapsing to one mapping.",
        ],
    }

    out = args.out or root / "aiw_runtime_graph_validation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    write_csv_path = out.with_name("aiw_runtime_edge_groups.csv")
    with write_csv_path.open("w", newline="", encoding="utf-8") as fh:
        keys = [
            "aiw_source", "from_waypoint", "to_waypoint", "candidate_count",
            "runtime_delta_values", "min_position_match_error",
            "min_error_from_runtime_address", "min_error_to_runtime_address",
            "min_error_runtime_delta", "min_error_matches_stride",
            "position_within_tolerance",
        ]
        writer = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(group_rows)

    print(f"sources: {len(source_summaries)}")
    print(f"runtime edge candidates: {len(runtime_edges)}")
    print(f"runtime edge groups: {len(group_rows)}")
    print(f"ambiguous edge groups: {result['ambiguous_edge_group_count']}")
    print(f"output: {out}")

    complete = result["complete_source_count"] == result["source_count"]
    unambiguous = result["ambiguous_edge_group_count"] == 0
    if not manifest_runtime_edge_count_match:
        return 2
    if args.require_complete and not complete:
        return 2
    if args.require_unambiguous and not unambiguous:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
