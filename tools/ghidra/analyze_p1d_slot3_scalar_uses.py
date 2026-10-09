#!/usr/bin/env python3
"""Post-process exact scalar-use rows for P1.3D slot3 HDVehicle+0x28b8.

This is candidate inventory only. A matching 0x28b8 scalar does not prove that
an instruction addresses selected HDVehicle+0x28b8; receiver/root provenance
must be adjudicated separately.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

FORMAT = "SHIFT.P1D.Slot3ScalarUseInventory/1"
INPUT_FORMAT = "SHIFT.GhidraScalarUses/1"
TARGET = "0x28b8"


def read_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as stream:
        for line_no, raw in enumerate(stream, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSONL: {exc}") from exc
            if row.get("format") != INPUT_FORMAT:
                raise ValueError(f"{path}:{line_no}: unexpected format {row.get('format')!r}")
            if str(row.get("target_scalar", "")).lower() != TARGET:
                raise ValueError(
                    f"{path}:{line_no}: target scalar drift {row.get('target_scalar')!r}"
                )
            rows.append(row)
    return rows


def build_payload(rows: list[dict]) -> dict:
    classes = Counter(str(row.get("usage_class") or "unknown") for row in rows)
    grouped: dict[str, list[dict]] = defaultdict(list)
    outside_functions = 0

    for row in rows:
        function = row.get("function_name")
        function_address = row.get("function_address")
        if function is None or function_address is None:
            outside_functions += 1
            key = "<outside-function>"
        else:
            key = f"{function}@{function_address}"
        grouped[key].append(
            {
                "instruction_address": row.get("instruction_address"),
                "mnemonic": row.get("mnemonic"),
                "text": row.get("text"),
                "matching_operand_index": row.get("matching_operand_index"),
                "matching_operand_text": row.get("matching_operand_text"),
                "usage_class": row.get("usage_class"),
            }
        )

    function_rows = []
    for key in sorted(grouped):
        entries = sorted(
            grouped[key], key=lambda item: str(item.get("instruction_address") or "")
        )
        function_rows.append(
            {
                "function": key,
                "use_count": len(entries),
                "address_materializer_count": sum(
                    item.get("usage_class") == "address-materializer" for item in entries
                ),
                "uses": entries,
            }
        )

    address_materializers = [
        {
            "function_name": row.get("function_name"),
            "function_address": row.get("function_address"),
            "instruction_address": row.get("instruction_address"),
            "text": row.get("text"),
            "matching_operand_text": row.get("matching_operand_text"),
        }
        for row in rows
        if row.get("usage_class") == "address-materializer"
    ]

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "target": "HDVehicle+0x28b8",
        "target_scalar": TARGET,
        "input_format": INPUT_FORMAT,
        "inventory": {
            "exact_scalar_use_count": len(rows),
            "function_group_count": len(grouped),
            "outside_function_use_count": outside_functions,
            "usage_classes": dict(sorted(classes.items())),
            "address_materializer_count": len(address_materializers),
            "address_materializers": address_materializers,
            "functions": function_rows,
        },
        "adjudication": {
            "numeric_offset_equality_is_selected_hdvehicle_identity": False,
            "selected_root_provenance_complete": False,
            "slot3_writer_proven": False,
            "p1_3d_complete": False,
            "external_provider_count": 7,
        },
        "next_step": (
            "Adjudicate every address-materializer and forwarding candidate by exact receiver/root "
            "provenance and qword write/forwarding width; only then promote a selected "
            "HDVehicle+0x28b8 writer."
        ),
    }


def analyze(path: Path) -> dict:
    return build_payload(read_rows(path))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = analyze(args.input)
    except ValueError as exc:
        parser.error(str(exc))
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
