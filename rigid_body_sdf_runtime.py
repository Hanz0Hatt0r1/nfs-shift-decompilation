"""Source-backed parser for SHIFT rigid-body suspension SDF resources.

The retail loader is FUN_007b6900 in SHIFT.exe.c. It recognizes BODY, JOINT,
HINGE, BAR and JOINT&HINGE records. This module preserves the text faithfully
and normalizes only the fields that the loader explicitly reads.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.RigidBodySDFRuntime/1"
SOURCE_LOADER = "FUN_007b6900"
SECTIONS = ("BODY", "JOINT", "HINGE", "BAR", "JOINT&HINGE")

_SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$")
_ASSIGN_RE = re.compile(r"^\s*([^=]+?)\s*=\s*(.*?)\s*$")
_NUM_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")

BODY_KEYS = {
    "name": "string",
    "mass": "scalar",
    "inertia": "tuple3",
    "pos": "tuple3",
    "ori": "tuple3",
    "vel": "tuple3",
    "rot": "tuple3",
}
CONSTRAINT_KEYS = {
    "name": "string",
    "posbody": "string",
    "negbody": "string",
    "axis": "tuple3",
    "neg": "tuple3",
    "pos": "tuple3-or-string",
}


def _atom(value: str) -> Any:
    value = value.strip()
    low = value.lower()
    if low in {"true", "false"}:
        return low == "true"
    if _NUM_RE.fullmatch(value):
        return float(value)
    return value.strip('"')


def _value(value: str) -> tuple[Any, str]:
    raw = value.strip()
    if raw.startswith("(") and raw.endswith(")"):
        inner = raw[1:-1].strip()
        parts = [] if not inner else [part.strip() for part in inner.split(",")]
        values = [_atom(part) for part in parts]
        return values, f"tuple{len(values)}"
    if "," in raw:
        values = [_atom(part) for part in raw.split(",")]
        return values, f"tuple{len(values)}"
    return _atom(raw), "scalar" if _NUM_RE.fullmatch(raw) else "string"


def parse_sdf(data: str | bytes, *, strict: bool = False) -> dict[str, Any]:
    text = data.decode("utf-8", "replace") if isinstance(data, bytes) else str(data)
    records: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    warnings: list[str] = []

    for line_no, original in enumerate(text.splitlines(), 1):
        stripped = original.split("//", 1)[0].strip()
        if not stripped:
            continue

        match = _SECTION_RE.match(stripped)
        if match:
            name = match.group(1).strip().upper()
            current = {
                "section": name,
                "source_section": match.group(1).strip(),
                "line": line_no,
                "entries": [],
            }
            records.append(current)
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
        value, shape = _value(raw)
        schema = BODY_KEYS if current["section"] == "BODY" else CONSTRAINT_KEYS
        expected_shape = schema.get(key)

        current["entries"].append({
            "name": key,
            "raw": raw,
            "value": value,
            "parsed_shape": shape,
            "line": line_no,
            "recognized_by_loader": expected_shape is not None,
            "loader_shape": expected_shape,
        })

    counts = {section: 0 for section in SECTIONS}
    for record in records:
        counts[record["section"]] = counts.get(record["section"], 0) + 1

    recognized = sum(
        1 for record in records
        for entry in record["entries"]
        if entry["recognized_by_loader"]
    )
    unknown = sum(
        1 for record in records
        for entry in record["entries"]
        if not entry["recognized_by_loader"]
    )
    return {
        "format": FORMAT,
        "version": 1,
        "status": "parsed" if not warnings else "parsed-with-warnings",
        "ready": not warnings,
        "source": {
            "file": "SHIFT.exe.c",
            "loader": SOURCE_LOADER,
            "recognized_sections": list(SECTIONS),
        },
        "record_count": len(records),
        "entry_count": sum(len(record["entries"]) for record in records),
        "recognized_entry_count": recognized,
        "unknown_entry_count": unknown,
        "topology": {
            "body_count": counts.get("BODY", 0),
            "joint_count": counts.get("JOINT", 0) + counts.get("JOINT&HINGE", 0),
            "hinge_count": counts.get("HINGE", 0) + counts.get("JOINT&HINGE", 0),
            "bar_count": counts.get("BAR", 0),
            "joint_hinge_count": counts.get("JOINT&HINGE", 0),
            "combined_slot_weight": counts.get("JOINT&HINGE", 0) * 3,
        },
        "records": records,
        "warnings": warnings,
        "evidence": {
            "record_count_fields": {
                "bodies": "+0x10",
                "joints": "+0x18",
                "hinges": "+0x20",
                "bars": "+0x28",
                "joint_hinge_aux": "+0x30",
            },
            "body_array_stride": "0x170",
            "joint_array_stride": "0xa0",
            "hinge_array_stride": "0xa0",
            "bar_array_stride": "0xb8",
            "constraint_name_fields": ["name", "posbody", "negbody"],
            "constraint_vector_fields": ["axis", "neg", "pos"],
        },
        "limitations": [
            "Actual PhysX object construction in FUN_007b3150 is not reproduced here.",
            "Lengths/constraints are parsed structurally; no physical-unit normalization is attempted.",
            "Unknown keys remain in the IR rather than being discarded.",
        ],
    }


def records_by_type(report: Mapping[str, Any], section: str) -> list[Mapping[str, Any]]:
    wanted = section.strip().upper()
    return [
        record
        for record in report.get("records") or []
        if str(record.get("section", "")).upper() == wanted
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parse SHIFT rigid-body SDF resources against the recovered runtime loader")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)

    report = parse_sdf(args.input.read_bytes(), strict=args.strict)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "record_count": report["record_count"],
        "topology": report["topology"],
        "warnings": len(report["warnings"]),
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
