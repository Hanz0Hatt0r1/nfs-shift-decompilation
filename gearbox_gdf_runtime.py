"""Conservative parser for SHIFT gearbox GDF resources.

The retail gearbox path in FUN_007c2110 loads an external '.gdf' resource.
The gearbox-data reader shown in SHIFT.exe.c recognizes [GEAR_RATIOS] and
[FINAL_DRIVE], reading 'ratio' as a pair and 'bevel' as a pair. This module
keeps the pair values exact and does not assign tooth-count semantics beyond
the source field names.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.GearboxGDFRuntime/1"
SOURCE_LOADER = "FUN_007c2110"
SECTIONS = ("GEAR_RATIOS", "FINAL_DRIVE")

_SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$")
_ASSIGN_RE = re.compile(r"^\s*([^=]+?)\s*=\s*(.*?)\s*$")
_NUM_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")


def _atom(value: str) -> int | float | str:
    value = value.strip().strip('"')
    if _NUM_RE.fullmatch(value):
        number = float(value)
        return int(number) if number.is_integer() and "." not in value and "e" not in value.lower() else number
    return value


def parse_gdf(data: str | bytes, *, strict: bool = False) -> dict[str, Any]:
    text = data.decode("utf-8", "replace") if isinstance(data, bytes) else str(data)
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    warnings: list[str] = []

    for line_no, original in enumerate(text.splitlines(), 1):
        stripped = original.split("//", 1)[0].strip()
        if not stripped:
            continue
        section_match = _SECTION_RE.match(stripped)
        if section_match:
            name = section_match.group(1).strip().upper()
            current = {"section": name, "source_section": section_match.group(1).strip(), "line": line_no, "entries": []}
            sections.append(current)
            continue

        assignment = _ASSIGN_RE.match(stripped)
        if assignment is None:
            warnings.append(f"line:{line_no}:unparsed:{original.strip()}")
            if strict:
                raise ValueError(warnings[-1])
            continue
        if current is None:
            warnings.append(f"line:{line_no}:property-before-section")
            if strict:
                raise ValueError(warnings[-1])
            continue

        key = assignment.group(1).strip()
        raw = assignment.group(2).strip()
        if raw.startswith("(") and raw.endswith(")"):
            parts = [part.strip() for part in raw[1:-1].split(",")]
            value = [_atom(part) for part in parts]
            shape = f"tuple{len(value)}"
        elif "," in raw:
            value = [_atom(part) for part in raw.split(",")]
            shape = f"tuple{len(value)}"
        else:
            value = _atom(raw)
            shape = "scalar" if isinstance(value, (int, float)) else "string"

        if current["section"] == "GEAR_RATIOS":
            expected = {"ratio": "tuple2"}
        elif current["section"] == "FINAL_DRIVE":
            expected = {"bevel": "tuple2", "ratio": "tuple2"}
        else:
            expected = {}

        current["entries"].append({
            "name": key,
            "raw": raw,
            "value": value,
            "parsed_shape": shape,
            "line": line_no,
            "recognized_by_loader": key in expected,
            "loader_shape": expected.get(key),
        })

    counts = {section: 0 for section in SECTIONS}
    for row in sections:
        counts[row["section"]] = counts.get(row["section"], 0) + 1

    return {
        "format": FORMAT,
        "version": 1,
        "status": "parsed" if not warnings else "parsed-with-warnings",
        "ready": not warnings,
        "source": {
            "file": "SHIFT.exe.c",
            "loader": SOURCE_LOADER,
            "extension": ".gdf",
        },
        "section_count": len(sections),
        "sections": sections,
        "counts": counts,
        "gear_ratio_count": sum(
            1 for row in sections if row["section"] == "GEAR_RATIOS"
            for entry in row["entries"] if entry["name"] == "ratio"
        ),
        "final_drive_ratio_count": sum(
            1 for row in sections if row["section"] == "FINAL_DRIVE"
            for entry in row["entries"] if entry["name"] == "ratio"
        ),
        "final_drive_bevel": [
            entry["value"]
            for row in sections if row["section"] == "FINAL_DRIVE"
            for entry in row["entries"] if entry["name"] == "bevel"
        ],
        "warnings": warnings,
        "evidence": {
            "gear_ratio_section": "[GEAR_RATIOS]",
            "final_drive_section": "[FINAL_DRIVE]",
            "ratio_field": "ratio",
            "bevel_field": "bevel",
            "ratio_record_stride": "0x18",
            "gear_ratio_storage": "selected ratio pair occupies +0x10/+0x14",
            "final_drive_bevel_storage": "+0x10/+0x14",
        },
        "limitations": [
            "The parser does not claim tooth-count versus ratio semantics for each pair.",
            "Sorting/comparator behavior is exposed only as provenance; no reordering is performed during parsing.",
            "Mode-4 database fallback in FUN_007c2110 is outside this text-file parser.",
        ],
    }


def entries(report: Mapping[str, Any], section: str, key: str | None = None) -> list[Mapping[str, Any]]:
    wanted = section.strip().upper()
    rows = [
        entry
        for row in report.get("sections") or []
        if str(row.get("section", "")).upper() == wanted
        for entry in row.get("entries") or []
    ]
    return [row for row in rows if key is None or row.get("name") == key]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parse SHIFT gearbox GDF resources")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    report = parse_gdf(args.input.read_bytes(), strict=args.strict)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "gear_ratio_count": report["gear_ratio_count"],
        "final_drive_ratio_count": report["final_drive_ratio_count"],
        "warnings": len(report["warnings"]),
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
