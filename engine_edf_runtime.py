"""Source-backed parser for SHIFT engine EDF configuration.

Unlike CDF, EDF is a flat key=value resource with RPMTorque appearing as a
repeated three-component record. The parser attaches the existing
VehiclePhysicsDetailsRuntime engine schema and preserves every unknown key.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Sequence

from vehicle_physics_runtime import (
    ENGINE_PROPERTIES,
    RPMTorquePoint,
    compute_rpm_torque_peak_power,
    parse_rpm_torque_points,
    sample_rpm_torque_curve,
)

FORMAT = "SHIFT.EngineEDFRuntime/1"
SOURCE_LOADER = "FUN_007c3280"
_NUMBER_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")
_SCHEMA = {item.name: item for item in ENGINE_PROPERTIES}


def _atom(raw: str) -> Any:
    value = raw.strip().strip('"')
    low = value.lower()
    if low in {"true", "false"}:
        return low == "true"
    if re.fullmatch(r"[+-]?\d+", value):
        return int(value)
    if _NUMBER_RE.fullmatch(value):
        return float(value)
    return value


def _value(raw: str) -> tuple[Any, str]:
    value = raw.strip()
    if value.startswith("(") and value.endswith(")"):
        parts = [part.strip() for part in value[1:-1].split(",")]
        if len(parts) == 1:
            return _atom(parts[0]), "scalar"
        values = [_atom(part) for part in parts]
        return values, f"tuple{len(values)}"
    return _atom(value), "scalar"


def parse_engine_edf(data: str | bytes, *, strict: bool = False) -> dict[str, Any]:
    text = data.decode("utf-8", "replace") if isinstance(data, bytes) else str(data)
    entries: list[dict[str, Any]] = []
    rpm_lines: list[str] = []
    warnings: list[str] = []

    for line_no, original in enumerate(text.splitlines(), 1):
        stripped = original.split("//", 1)[0].strip()
        if not stripped:
            continue
        if stripped.startswith("RPMTorque"):
            rpm_lines.append(stripped)
            continue
        if "=" not in stripped:
            warnings.append(f"line:{line_no}:unparsed:{original.strip()}")
            if strict:
                raise ValueError(warnings[-1])
            continue
        key, raw = (part.strip() for part in stripped.split("=", 1))
        value, shape = _value(raw)
        spec = _SCHEMA.get(key)
        entries.append({
            "name": key,
            "raw": raw,
            "value": value,
            "parsed_shape": shape,
            "line": line_no,
            "recognized": spec is not None,
            "schema": (
                {
                    "offset": spec.offset,
                    "offset_hex": f"0x{spec.offset:x}",
                    "registration": spec.registration,
                    "width": spec.width,
                }
                if spec is not None
                else None
            ),
        })

    rpm_report = parse_rpm_torque_points("\n".join(rpm_lines), strict=strict)
    rpm_points = rpm_report["points"]
    rpm_offsets = [point["line"] for point in rpm_points]
    # parse_rpm_torque_points receives a compacted string, so preserve the
    # original EDF line numbers by walking RPMTorque occurrences directly.
    original_rpm_line_numbers = [
        line_no
        for line_no, original in enumerate(text.splitlines(), 1)
        if original.split("//", 1)[0].strip().startswith("RPMTorque")
    ]
    for point, line_no in zip(rpm_points, original_rpm_line_numbers):
        point["line"] = line_no

    recognized = sum(1 for entry in entries if entry["recognized"]) + len(rpm_points)
    unknown = sum(1 for entry in entries if not entry["recognized"])
    warnings.extend(rpm_report.get("warnings") or [])

    if strict and warnings:
        raise ValueError(warnings[0])

    return {
        "format": FORMAT,
        "version": 1,
        "status": "parsed" if not warnings else "parsed-with-warnings",
        "ready": not warnings,
        "source": {
            "file": "./Source/Vehicle/vehload.cpp",
            "loader": SOURCE_LOADER,
            "extension": ".edf",
        },
        "entry_count": len(entries) + len(rpm_points),
        "recognized_entry_count": recognized,
        "unknown_entry_count": unknown,
        "unknown_keys": [entry["name"] for entry in entries if not entry["recognized"]],
        "entries": entries,
        "rpm_torque": {
            "points": rpm_points,
            "point_count": len(rpm_points),
            "peak_power_scan": compute_rpm_torque_peak_power(tuple(
                RPMTorquePoint(point["rpm"], point["brake"], point["throttle"])
                for point in rpm_points
            )),
            "interpolation_examples": [
                {
                    "rpm": rpm,
                    "brake": sample_rpm_torque_curve(
                        tuple(RPMTorquePoint(point["rpm"], point["brake"], point["throttle"]) for point in rpm_points), rpm
                    )[0],
                    "throttle": sample_rpm_torque_curve(
                        tuple(RPMTorquePoint(point["rpm"], point["brake"], point["throttle"]) for point in rpm_points), rpm
                    )[1],
                }
                for rpm in (
                    rpm_points[0]["rpm"],
                    rpm_points[-1]["rpm"],
                )
            ] if rpm_points else [],
            "limit": rpm_report["limit"],
            "source_tuple_order": ["rpm", "brake", "throttle"],
            "storage_order": ["brake", "throttle", "rpm"],
        },
        "warnings": warnings,
        "evidence": {
            "runtime_loader": SOURCE_LOADER,
            "tuple_reader": "FUN_007a6a90",
            "postload": "FUN_007c3920",
            "interpolator": "FUN_007becb0",
            "peak_power_scan": "FUN_007c3b00/FUN_007c3920",
        },
        "limitations": [
            "The parser does not assign physical units to EDF fields.",
            "Modifier resolution through FUN_007a6be0 is represented by source provenance; no external upgrade state is guessed.",
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parse SHIFT engine EDF configuration")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    report = parse_engine_edf(args.input.read_bytes(), strict=args.strict)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "entry_count": report["entry_count"],
        "recognized": report["recognized_entry_count"],
        "unknown": report["unknown_entry_count"],
        "rpm_torque_points": report["rpm_torque"]["point_count"],
        "warnings": len(report["warnings"]),
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
