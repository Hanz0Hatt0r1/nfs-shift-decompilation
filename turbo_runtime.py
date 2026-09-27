"""Source-backed Turbo BBF/TBF runtime parser for Need for Speed: SHIFT.

The parser intentionally separates:
  * text-file decoding;
  * source-backed field/storage metadata;
  * post-load scalar normalization.

No physical unit is invented. The only conversions exposed here are the exact
multipliers visible in Turbo.cpp.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from upgrade_modifier_runtime import ModifierNode, evaluate_modifier_chain

FORMAT = "SHIFT.TurboRuntime/1"

SIZE_SCALE = 0.01
RPM_SCALE = 0.10471976
EPSILON = 1e-5

BBF_FIELDS = {
    "Boost": {"offset": 0x34, "shape": "scalar", "helper": "FUN_007a75a0"},
    "Max Boost": {"offset": 0x20, "shape": "scalar", "helper": "FUN_007a75a0"},
    "Boost Time": {"offset": 0x08, "shape": "scalar", "helper": "FUN_007a75a0"},
    "Fill Time": {"offset": 0x04, "shape": "scalar", "helper": "FUN_007a67b0"},
    "Max Boost Time": {"offset": 0x1C, "shape": "scalar", "helper": "FUN_007a67b0"},
    "Ramp Down Time": {"offset": 0x48, "shape": "scalar", "helper": "FUN_007a67b0"},
    "Min Level To Fire": {"offset": 0x4C, "shape": "scalar", "helper": "FUN_007a67b0"},
    "GlobalUpgrades": {"offset": 0x9C, "shape": "upgrade-chain", "helper": "FUN_007a72e0"},
}

TBF_FIELDS = {
    "Twin Turbo": {"offset": 0x05, "shape": "bool", "helper": "FUN_007a6470"},
    "Sequential Turbo": {"offset": 0x06, "shape": "bool", "helper": "FUN_007a6470"},
    "WasteGate Opening": {"offset": 0xA4, "shape": "scalar", "helper": "FUN_007a67b0"},
    "WasteGate Closing": {"offset": 0xA8, "shape": "scalar", "helper": "FUN_007a67b0"},
    "GlobalUpgrades": {"offset": 0x9C, "shape": "upgrade-chain", "helper": "FUN_007a72e0"},
}

_TBF_TURBO_FIELDS = {
    "Size": {"relative_offset": 0x00, "conversion": "x0.01"},
    "Engine RPM": {"relative_offset": 0x00, "conversion": "x0.10471976"},
    "Turbine Optimum RPM": {"relative_offset": 0x08, "conversion": "x0.10471976"},
    "Inertia": {"relative_offset": 0x20, "conversion": "identity"},
    "Friction": {"relative_offset": 0x28, "conversion": "identity"},
    "Fuel Percentage": {"relative_offset": 0x4C, "conversion": "x0.01"},
}

_NUMBER_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")


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


def _flat_entries(text: str) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    for line_no, original in enumerate(text.splitlines(), 1):
        stripped = original.split("//", 1)[0].strip()
        if not stripped:
            continue
        if "=" not in stripped:
            warnings.append(f"line:{line_no}:unparsed:{original.strip()}")
            continue
        key, raw = (part.strip() for part in stripped.split("=", 1))
        rows.append({
            "name": key,
            "raw": raw,
            "value": _atom(raw),
            "line": line_no,
        })
    return rows, warnings


def _by_name(rows: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {str(row["name"]).lower(): row for row in rows}


def parse_turbo_bbf(
    data: str | bytes,
    *,
    boost_upgrade_nodes: Sequence[ModifierNode] = (),
    boost_time_upgrade_nodes: Sequence[ModifierNode] = (),
    max_value: float | None = None,
) -> dict[str, Any]:
    text = data.decode("utf-8", "replace") if isinstance(data, bytes) else str(data)
    entries, warnings = _flat_entries(text)
    lookup = _by_name(entries)
    fields = []

    values: dict[str, Any] = {}
    for name, spec in BBF_FIELDS.items():
        row = lookup.get(name.lower())
        if row is None:
            continue
        value = row["value"]
        values[name] = value
        fields.append({
            "name": name,
            "line": row["line"],
            "raw": row["raw"],
            "value": value,
            **spec,
        })

    boost = float(values.get("Boost", 0.0))
    boost_time = float(values.get("Boost Time", 0.0))
    if boost_upgrade_nodes:
        boost = float(evaluate_modifier_chain(boost, 0, tuple(boost_upgrade_nodes))["result"])
    if boost_time_upgrade_nodes:
        boost_time = float(evaluate_modifier_chain(boost_time, 0, tuple(boost_time_upgrade_nodes))["result"])

    active = abs(boost) >= EPSILON and abs(boost_time) >= EPSILON
    normalized = dict(values)
    if active and max_value is not None:
        for key in ("Fill Time", "Max Boost Time", "Ramp Down Time", "Min Level To Fire"):
            if key in normalized:
                normalized[key] = min(max(float(normalized[key]), 0.0), float(max_value))

    return {
        "format": FORMAT,
        "version": 1,
        "resource_type": "BBF",
        "status": "parsed" if not warnings else "parsed-with-warnings",
        "ready": not warnings,
        "fields": fields,
        "values": normalized,
        "postload": {
            "boost_after_upgrade": boost,
            "boost_time_after_upgrade": boost_time,
            "active": active,
            "clamp_applied": active and max_value is not None,
            "clamp_range": None if max_value is None else [0.0, float(max_value)],
            "clamped_fields": [
                key for key in ("Fill Time", "Max Boost Time", "Ramp Down Time", "Min Level To Fire")
                if active and max_value is not None and key in normalized
            ],
        },
        "upgrade_chain": {
            "boost": len(boost_upgrade_nodes),
            "boost_time": len(boost_time_upgrade_nodes),
        },
        "source": {
            "file": ".\\Source\\Vehicle\\Turbo.cpp",
            "loader": "FUN_007c6030",
            "boost_model_reader": "FUN_00747b00",
            "modifier_helper": "FUN_007a6be0",
            "clamp_helper": "FUN_007c5fd0",
        },
        "evidence": {
            "boost_offset": "0x34",
            "max_boost_offset": "0x20",
            "boost_time_offset": "0x08",
            "fill_time_offset": "0x04",
            "max_boost_time_offset": "0x1c",
            "ramp_down_time_offset": "0x48",
            "min_level_to_fire_offset": "0x4c",
            "active_flag_offset": "0x50",
            "global_upgrades_offset": "0x9c",
        },
        "warnings": warnings,
        "limitations": [
            "BBF text fields not present in the source file are preserved as absent rather than synthesized.",
            "Turbo upgrade-node contents are external inputs; this parser does not guess them.",
        ],
    }


def parse_turbo_tbf(
    data: str | bytes,
    *,
    boost_time_upgrade_nodes: Sequence[ModifierNode] = (),
    max_boost_upgrade_nodes: Sequence[ModifierNode] = (),
) -> dict[str, Any]:
    text = data.decode("utf-8", "replace") if isinstance(data, bytes) else str(data)
    entries, warnings = _flat_entries(text)
    lookup = _by_name(entries)

    values: dict[str, Any] = {}
    fields: list[dict[str, Any]] = []
    for name, spec in TBF_FIELDS.items():
        row = lookup.get(name.lower())
        if row is None:
            continue
        values[name] = row["value"]
        fields.append({
            "name": name,
            "line": row["line"],
            "raw": row["raw"],
            "value": row["value"],
            **spec,
        })

    turbo_rows = []
    for index in (1, 2):
        row_data: dict[str, Any] = {"index": index, "fields": {}}
        for field_name, spec in _TBF_TURBO_FIELDS.items():
            key = f"Turbo{index} {field_name}"
            row = lookup.get(key.lower())
            if row is None:
                continue
            raw_value = row["value"]
            numeric = float(raw_value)
            if field_name == "Size":
                value = numeric * SIZE_SCALE
            elif field_name in {"Engine RPM", "Turbine Optimum RPM"}:
                value = numeric * RPM_SCALE
            elif field_name == "Fuel Percentage":
                value = numeric * SIZE_SCALE
            else:
                value = numeric
            row_data["fields"][field_name] = {
                "line": row["line"],
                "raw": raw_value,
                "value": value,
                "conversion": spec["conversion"],
                "runtime_offset": spec["relative_offset"] + (index - 1) * 0x04,
            }
        turbo_rows.append(row_data)

    boost_time = float(
        values.get("Boost Time", 0.0)
    )
    max_boost = float(
        values.get("Max Boost", 0.0)
    )
    if boost_time_upgrade_nodes:
        boost_time = float(evaluate_modifier_chain(boost_time, 0, tuple(boost_time_upgrade_nodes))["result"])
    if max_boost_upgrade_nodes:
        max_boost = float(evaluate_modifier_chain(max_boost, 0, tuple(max_boost_upgrade_nodes))["result"])

    return {
        "format": FORMAT,
        "version": 1,
        "resource_type": "TBF",
        "status": "parsed" if not warnings else "parsed-with-warnings",
        "ready": not warnings,
        "fields": fields,
        "values": values,
        "turbos": turbo_rows,
        "postload": {
            "file_open_flag": 1,
            "boost_time_after_upgrade": boost_time,
            "max_boost_after_upgrade": max_boost,
            "return_scalar": boost_time + max_boost + 1.0,
        },
        "source": {
            "file": ".\\Source\\Vehicle\\Turbo.cpp",
            "loader": "FUN_007c6680",
            "modifier_helper": "FUN_007a6be0",
            "turbo_reader": "FUN_007a75a0/FUN_007a67b0",
        },
        "evidence": {
            "twin_turbo_offset": "0x05",
            "sequential_turbo_offset": "0x06",
            "wastegate_opening_offset": "0xa4",
            "wastegate_closing_offset": "0xa8",
            "global_upgrades_offset": "0x9c",
            "turbo1_size_storage": "local+0x08",
            "turbo2_size_storage": "local+0x1c",
            "engine_rpm_base": "this+0x30",
            "turbine_optimum_base": "this+0x38",
            "inertia_base": "this+0x50",
            "friction_base": "this+0x58",
            "fuel_percentage_base": "this+0x7c",
        },
        "conversions": {
            "size": SIZE_SCALE,
            "engine_rpm": RPM_SCALE,
            "turbine_optimum_rpm": RPM_SCALE,
            "fuel_percentage": SIZE_SCALE,
        },
        "warnings": warnings,
        "limitations": [
            "The external GlobalUpgrades object and linked modifier nodes are caller-provided evidence.",
            "No turbo physical-unit labels are assigned beyond source-visible conversions.",
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parse SHIFT Turbo BBF/TBF resources")
    parser.add_argument("type", choices=("bbf", "tbf"))
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    data = args.input.read_bytes()
    report = parse_turbo_bbf(data) if args.type == "bbf" else parse_turbo_tbf(data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "resource_type": report["resource_type"],
        "status": report["status"],
        "ready": report["ready"],
        "warnings": len(report["warnings"]),
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
