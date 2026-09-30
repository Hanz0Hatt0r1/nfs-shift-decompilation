#!/usr/bin/env python3
"""Verify track/path analyzer offsets against recovered reflection metadata."""
from __future__ import annotations

import argparse
import json
import runpy
from pathlib import Path

from extract_shift_reflection_fields import extract_reflection_fields

FORMAT = "SHIFT-TRACK-PATH-REFLECTION-LAYOUTS/1"

# (reflected field name, analyzer field key, reflection type code)
LAYOUT_BINDINGS = {
    "AIPathInfo": ("PATH", (
        ("tangent", "tx", 7),
        ("outside", "outside", 1),
        ("centreDist", "centre", 1),
        ("StartNode", "start_node", 0x0D),
        ("pathSide", "side", 0x16),
        ("pathEndReached", "end", 0x16),
        ("spawnedge", "spawn", 0x16),
        ("trackEdge", "edge", 0x16),
    )),
    "AIArea": ("INCIDENT", (
        ("incident pos", "incident_x", 7),
        ("path pointer", "path", 4),
        ("area type", "area", 3),
        ("CentrePos", "cx", 8),
        ("Radius", "radius", 1),
        ("active", "active", 2),
        ("active incident", "active_incident", 2),
        ("roaming characters", "roaming", 2),
        ("incident path dist", "incident_path_dist", 1),
        ("incident timer", "incident_timer", 1),
        ("interest level", "interest_level", 1),
        ("min spacing", "min_spacing", 1),
        ("TrackDist", "track_dist", 1),
        ("RaceFlag", "race_flag", 3),
        ("AreaIndex", "area_index", 3),
        ("nMarshals", "n_marshals", 3),
        ("nFlagMarshals", "n_flag_marshals", 3),
    )),
    "AISegmentPath": ("SEGMENT", (
        ("num nodes", "nodes", 3),
        ("track side", "side", 3),
        ("segmentnode array", "array", 6),
        ("length", "length", 1),
        ("cyclic", "cyclic", 2),
        ("NarrowPath", "narrow", 2),
        ("PathNodeSpacing", "spacing", 1),
        ("PathDist", "path_dist", 1),
        ("CurrentNode", "current", 3),
        ("EdgeStep", "edge_step", 1),
    )),
    "AIPathNode": ("SEGMENT_NODE", (
        ("pos1", "pos1_x", 7),
        ("pos2", "pos2_x", 7),
        ("normal", "normal_x", 7),
        ("height1", "height1", 1),
        ("height2", "height2", 1),
        ("dist", "distance", 1),
        ("distributionratio", "distribution_ratio", 1),
    )),
    "AIPolylinePath": ("POLY", (
        ("num nodes", "nodes", 3),
        ("polylinenode array", "array", 6),
        ("length", "length", 1),
        ("width", "width", 1),
        ("cyclic", "cyclic", 2),
        ("PathNodeSpacing", "spacing", 1),
        ("DefaultPathWidth", "default_width", 1),
    )),
    "AIPolyPathNode": ("POLY_NODE", (
        ("pos", "x", 7),
        ("normal", "dx", 7),
        ("dist", "distance", 1),
    )),
    "Knot": ("KNOT", (
        ("Pos", "pos_x", 8),
        ("ConstantA", "constant_a_x", 8),
        ("ConstantB", "constant_b_x", 8),
        ("ConstantC", "constant_c_x", 8),
        ("Length", "length", 1),
        ("InvLength", "inv_length", 1),
    )),
    "AISpline": ("SPLINE", (
        ("knot array", "array", 6),
        ("length", "length", 1),
        ("knot count", "knots", 3),
        ("StepDist", "step_dist", 1),
    )),
}


def _load_analyzer_specs(path: Path, class_names: list[str]) -> dict:
    namespace = runpy.run_path(str(path))
    specs = {}
    spec_names = {LAYOUT_BINDINGS[name][0] for name in class_names}
    for spec_name in sorted(spec_names):
        value = namespace.get(spec_name)
        if not isinstance(value, dict):
            raise ValueError(f"{path}: analyzer spec {spec_name} not found")
        specs[spec_name] = value
    return specs


def verify(
    source: Path,
    exe: Path,
    analyzer: Path,
    class_names: list[str] | None = None,
) -> dict:
    reflection = extract_reflection_fields(source, exe)
    selected = class_names or list(LAYOUT_BINDINGS)

    unknown = sorted(set(selected) - set(LAYOUT_BINDINGS))
    if unknown:
        raise ValueError("unknown layout class(es): " + ", ".join(unknown))

    specs = _load_analyzer_specs(analyzer, selected)

    source_index: dict[tuple[str, str], list[dict]] = {}
    for row in reflection["fields"]:
        class_name = row.get("class_name")
        field_name = row.get("field_name")
        if class_name is None or field_name is None:
            continue
        source_index.setdefault((class_name, field_name), []).append(row)

    rows = []
    for class_name in selected:
        spec_name, bindings = LAYOUT_BINDINGS[class_name]
        spec = specs[spec_name]
        for reflected_name, analyzer_field, expected_type in bindings:
            candidates = source_index.get((class_name, reflected_name), [])
            analyzer_entry = spec.get(analyzer_field)
            analyzer_offset = (
                int(analyzer_entry[0])
                if isinstance(analyzer_entry, tuple) and analyzer_entry
                else None
            )
            exact_source = [
                row
                for row in candidates
                if row.get("offset") == analyzer_offset
                and row.get("type_code") == expected_type
            ]
            rows.append({
                "class": class_name,
                "analyzer_spec": spec_name,
                "reflected_field": reflected_name,
                "expected_type_code": expected_type,
                "analyzer_field": analyzer_field,
                "analyzer_offset": analyzer_offset,
                "source_candidate_count": len(candidates),
                "source_offsets": sorted({
                    int(row["offset"])
                    for row in candidates
                    if row.get("offset") is not None
                }),
                "source_type_codes": sorted({
                    int(row["type_code"])
                    for row in candidates
                    if row.get("type_code") is not None
                }),
                "source_functions": sorted({
                    row["reflection_function"]
                    for row in candidates
                    if row.get("reflection_function")
                }),
                "match": bool(exact_source),
            })

    return {
        "format": FORMAT,
        "source": str(source),
        "source_sha256": reflection["source_sha256"],
        "exe": str(exe),
        "exe_sha256": reflection["exe_sha256"],
        "analyzer": str(analyzer),
        "class_count": len(selected),
        "binding_count": len(rows),
        "matched_binding_count": sum(row["match"] for row in rows),
        "ready": all(row["match"] for row in rows),
        "classes": selected,
        "bindings": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="recovered SHIFT.exe.c")
    parser.add_argument("--exe", required=True, type=Path, help="retail SHIFT.exe")
    parser.add_argument(
        "--analyzer",
        type=Path,
        default=Path(__file__).with_name("analyze_track_paths.py"),
    )
    parser.add_argument(
        "--class-name",
        action="append",
        choices=sorted(LAYOUT_BINDINGS),
        help="verify only this class (repeatable)",
    )
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = verify(args.source, args.exe, args.analyzer, args.class_name)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
