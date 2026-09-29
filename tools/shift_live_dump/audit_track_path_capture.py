#!/usr/bin/env python3
"""Audit a track-path capture and generate the next extraction/runtime handoff."""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

FORMAT = "SHIFT-LIVE-MEMORY-TRACK-PATH-CAPTURE-HANDOFF/1"

REQUIRED_FILES = (
    "track_path_analysis.json",
    "path.csv",
    "aipolylinepath.csv",
    "aipolylinepath_nodes.csv",
    "path_root_targets.csv",
    "path_root_ranges.txt",
    "aiw_waypoints.csv",
    "aiw_next_edges.csv",
    "aiw_runtime_matches.csv",
    "aiw_runtime_sequences.csv",
    "aiw_runtime_edges.csv",
    "path_polyline_links.csv",
    "track_path_instance_edges.csv",
)


def read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON: {path}: {exc}")
    if not isinstance(value, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return value


def csv_rows(path: Path) -> tuple[bool, int, list[str], str | None]:
    if not path.is_file():
        return False, 0, [], None
    try:
        with path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            fields = reader.fieldnames or []
            rows = sum(1 for _ in reader)
    except (OSError, csv.Error, UnicodeError) as exc:
        return True, 0, [], str(exc)
    return True, rows, fields, None


def parse_hex(value: str) -> int:
    value = value.strip()
    if not value:
        raise ValueError("empty address")
    return int(value, 0)


def parse_root_ranges(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    out = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if ":" not in line:
            raise SystemExit(f"invalid root range on line {lineno}: {raw}")
        start_text, size_text = line.split(":", 1)
        try:
            start = parse_hex(start_text)
            size = parse_hex(size_text)
        except ValueError as exc:
            raise SystemExit(f"invalid root range on line {lineno}: {raw}: {exc}")
        if start < 0 or size <= 0:
            raise SystemExit(f"invalid root range on line {lineno}: {raw}")
        out.append({"start": start, "size": size, "end": start + size})
    return out


def read_root_targets(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows: list[dict] = []
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                target = int(row["target"], 0)
                candidate_count = int(row.get("candidate_count", "0"), 0)
                mapping_start = int(row.get("mapping_start", "0"), 0)
                mapping_end = int(row.get("mapping_end", "0"), 0)
            except (KeyError, TypeError, ValueError):
                continue
            rows.append({
                "target": target,
                "candidate_count": candidate_count,
                "mapping_start": mapping_start,
                "mapping_end": mapping_end,
                "mapping_perms": row.get("mapping_perms", ""),
                "candidate_addresses": row.get("candidate_addresses", ""),
            })
    rows.sort(key=lambda row: (-row["candidate_count"], row["target"]))
    return rows


def format_addr(value: int) -> str:
    return f"0x{value:x}"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Audit a track-path capture and generate a reproducible next-capture handoff"
    )
    ap.add_argument("analysis_dir", type=Path)
    ap.add_argument("--out", type=Path,
                    help="output JSON; defaults to <analysis_dir>/track_path_capture_handoff.json")
    ap.add_argument("--full-capture", default="<FULL_CAPTURE>",
                    help="full capture path placeholder used in generated commands")
    ap.add_argument("--aiw", default="<AIW_SOURCE>",
                    help="AIW/BFF/ZIP source placeholder used in generated commands")
    ap.add_argument("--aiw-entry", default="<AIW_ENTRY>",
                    help="AIW entry name placeholder used in generated commands")
    ap.add_argument("--strict", action="store_true",
                    help="return 2 unless the runtime instance graph is available")
    args = ap.parse_args()

    root = args.analysis_dir
    manifest = read_json(root / "track_path_analysis.json")
    inventory: dict[str, dict] = {}
    for filename in REQUIRED_FILES:
        present, rows, fields, error = csv_rows(root / filename)
        if filename.endswith(".json"):
            present = (root / filename).is_file()
            rows = 0
            fields = []
            error = None
        elif filename.endswith(".txt"):
            present = (root / filename).is_file()
            lines = [
                line for line in (root / filename).read_text(encoding="utf-8").splitlines()
                if line.split("#", 1)[0].strip()
            ] if present else []
            rows = len(lines)
            fields = []
            error = None
        inventory[filename] = {
            "present": present,
            "rows": rows,
            "nonempty": rows > 0,
            "fields": fields,
            "error": error,
        }

    path_roots = read_root_targets(root / "path_root_targets.csv")
    root_ranges = parse_root_ranges(root / "path_root_ranges.txt")
    high_value_roots = [
        row for row in path_roots
        if row["candidate_count"] >= 2
        and row["target"] >= 0x01000000
        and ("x" in row["mapping_perms"] or row["mapping_end"] > 0x01000000)
    ]

    static_ready = (
        inventory["path.csv"]["nonempty"]
        and inventory["aiw_waypoints.csv"]["nonempty"]
        and inventory["aiw_next_edges.csv"]["nonempty"]
    )
    node_ready = inventory["aipolylinepath_nodes.csv"]["nonempty"]
    runtime_match_ready = inventory["aiw_runtime_matches.csv"]["nonempty"]
    runtime_sequence_ready = inventory["aiw_runtime_sequences.csv"]["nonempty"]
    runtime_edge_ready = inventory["aiw_runtime_edges.csv"]["nonempty"]
    object_join_ready = inventory["path_polyline_links.csv"]["nonempty"]
    instance_graph_ready = inventory["track_path_instance_edges.csv"]["nonempty"]

    blocking_reasons: list[str] = []
    next_actions: list[str] = []

    if not node_ready:
        blocking_reasons.append("no decoded AIPolyPathNode array is present")
        next_actions.append("extract the path_root_ranges against the original full capture")
    if not runtime_match_ready:
        blocking_reasons.append("aiw_runtime_matches.csv is empty or missing")
        next_actions.append("rerun analyzer with selected runtime roots and AIW source")
    if not runtime_edge_ready:
        blocking_reasons.append("aiw_runtime_edges.csv is empty or missing")
        next_actions.append("obtain concrete runtime next-edge address pairs from the recovered node sequence")
    if not object_join_ready:
        blocking_reasons.append("path_polyline_links.csv is empty or missing")
        next_actions.append("capture the AIPolylinePath object(s) whose array equals the recovered Path.StartNode")
    if not instance_graph_ready:
        blocking_reasons.append("track_path_instance_edges.csv is empty or missing")
        next_actions.append("run the runtime instance-graph validator after node/object correlation")
    if not runtime_sequence_ready:
        blocking_reasons.append("aiw_runtime_sequences.csv is empty or missing")

    status = (
        "ready"
        if instance_graph_ready
        else "runtime-correlation-blocked"
        if static_ready
        else "capture-structure-incomplete"
    )

    runtime_roots = [row["target"] for row in high_value_roots]
    root_args = " ".join(f"--runtime-root {format_addr(value)}" for value in runtime_roots)
    extraction_cmd = (
        f"python3 tools/shift_live_dump/extract_ranges.py "
        f"{args.full_capture} track-path-roots --preset none "
        f"--range-file {root / 'path_root_ranges.txt'}"
    )
    analyzer_cmd = (
        f"python3 tools/shift_live_dump/analyze_track_paths.py "
        f"track-path-roots --out track-path-roots/track_path_analysis "
        f"--skip-pointer-analysis --aiw {args.aiw} "
        f"--aiw-entry '{args.aiw_entry}'"
    )
    if root_args:
        analyzer_cmd += f" {root_args}"

    result = {
        "format": FORMAT,
        "analysis_dir": str(root),
        "status": status,
        "manifest": {
            "format": manifest.get("format"),
            "snapshots": manifest.get("snapshots"),
            "common_regions": manifest.get("common_regions"),
            "candidate_counts": manifest.get("candidate_counts", {}),
        },
        "inventory": inventory,
        "evidence": {
            "static_ready": static_ready,
            "node_geometry_ready": node_ready,
            "runtime_match_ready": runtime_match_ready,
            "runtime_sequence_ready": runtime_sequence_ready,
            "runtime_edge_ready": runtime_edge_ready,
            "path_polyline_join_ready": object_join_ready,
            "instance_graph_ready": instance_graph_ready,
        },
        "path_roots": {
            "target_count": len(path_roots),
            "range_count": len(root_ranges),
            "high_value_root_count": len(high_value_roots),
            "high_value_targets": [format_addr(value) for value in runtime_roots],
            "ranges": root_ranges,
        },
        "blocking_reasons": blocking_reasons,
        "next_actions": list(dict.fromkeys(next_actions)),
        "recommended_commands": {
            "extract_roots": extraction_cmd,
            "rerun_runtime_correlation": analyzer_cmd,
            "validate_runtime_graph": (
                "python3 tools/shift_live_dump/validate_aiw_runtime_graph.py "
                "track-path-roots/track_path_analysis --require-complete"
            ),
            "validate_instance_graph": (
                "python3 tools/shift_live_dump/validate_track_path_instance_graph.py "
                "track-path-roots/track_path_analysis "
                "--require-node-owner --require-same-array --require-stride "
                "--require-path-polyline-join"
            ),
        },
        "evidence_boundary": (
            "A ready handoff does not prove gameplay semantics. It only confirms "
            "that the concrete capture contains enough correlated objects to run "
            "the next fail-closed validation stage."
        ),
    }

    out = args.out or root / "track_path_capture_handoff.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print(f"status: {status}")
    print(f"snapshots: {manifest.get('snapshots', 0)}")
    print(f"path roots: {len(path_roots)}")
    print(f"root ranges: {len(root_ranges)}")
    print(f"high-value runtime roots: {len(runtime_roots)}")
    print(f"node geometry ready: {node_ready}")
    print(f"runtime matches ready: {runtime_match_ready}")
    print(f"runtime edges ready: {runtime_edge_ready}")
    print(f"Path/Polyline join ready: {object_join_ready}")
    print(f"instance graph ready: {instance_graph_ready}")
    print(f"output: {out}")

    if args.strict and not instance_graph_ready:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
