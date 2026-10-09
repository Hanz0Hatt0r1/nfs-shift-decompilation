#!/usr/bin/env python3
"""Build a direct retail caller inventory for the two release wrappers.

The inventory is derived only from the structured Ghidra direct callgraph. It is
used to drive a later targeted instruction export of caller functions, avoiding
any dependency on decompiler C output.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT-MEMORY-RELEASE-WRAPPER-CALLERS/1"
WRAPPERS = {
    "0x00886930": "FUN_00886930",
    "0x00886950": "FUN_00886950",
}


def _norm_address(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip().lower()
    if token.startswith("fun_"):
        token = token[4:]
    if token.startswith("0x"):
        token = token[2:]
    try:
        return f"0x{int(token, 16):08x}"
    except ValueError:
        return None


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            yield row


def build_release_wrapper_caller_inventory(
    ghidra_export: Path,
    max_callers: int = 500,
) -> dict[str, Any]:
    if max_callers < 1:
        raise ValueError("max_callers must be >= 1")
    callgraph = ghidra_export / "callgraph.jsonl"
    if not callgraph.is_file():
        raise FileNotFoundError(f"missing required Ghidra file: {callgraph}")

    grouped: dict[str, list[dict[str, Any]]] = {}
    edge_count = 0
    for row in _read_jsonl(callgraph):
        if row.get("indirect") is not False:
            continue
        target = _norm_address(row.get("to"))
        if target not in WRAPPERS:
            continue
        caller = _norm_address(row.get("from_function"))
        instruction = _norm_address(row.get("instruction"))
        if caller is None or instruction is None:
            continue
        edge_count += 1
        grouped.setdefault(caller, []).append(
            {
                "instruction": instruction,
                "wrapper_address": target,
                "wrapper": WRAPPERS[target],
                "to_name": row.get("to_name"),
            }
        )

    caller_addresses = sorted(grouped)
    total_caller_count = len(caller_addresses)
    selected_addresses = caller_addresses[:max_callers]
    truncated = total_caller_count > len(selected_addresses)
    callers = [
        {
            "address": address,
            "call_count": len(grouped[address]),
            "calls": sorted(
                grouped[address],
                key=lambda item: (item["instruction"], item["wrapper_address"]),
            ),
        }
        for address in selected_addresses
    ]

    selected_edge_count = sum(row["call_count"] for row in callers)
    return {
        "format": FORMAT,
        "ghidra_export": str(ghidra_export),
        "wrappers": [
            {"address": address, "name": name}
            for address, name in WRAPPERS.items()
        ],
        "max_callers": max_callers,
        "total_caller_count": total_caller_count,
        "selected_caller_count": len(callers),
        "total_direct_edge_count": edge_count,
        "selected_direct_edge_count": selected_edge_count,
        "truncated": truncated,
        "caller_targets": selected_addresses,
        "callers": callers,
        "scope": {
            "direct_callgraph_used": True,
            "caller_instruction_arguments_proven": False,
            "release_byte_role_proven": False,
            "note": (
                "This inventory identifies direct caller functions and call instructions only. "
                "Argument values require a targeted caller instruction export."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("--max-callers", type=int, default=500)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--targets-out", type=Path)
    args = parser.parse_args()

    report = build_release_wrapper_caller_inventory(args.ghidra_export, args.max_callers)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    if args.targets_out:
        args.targets_out.parent.mkdir(parents=True, exist_ok=True)
        args.targets_out.write_text(
            "".join(address + "\n" for address in report["caller_targets"]),
            encoding="utf-8",
        )
    print(f"format: {report['format']}")
    print(f"direct release-wrapper edges: {report['total_direct_edge_count']}")
    print(
        f"callers selected: {report['selected_caller_count']}/"
        f"{report['total_caller_count']}"
    )
    print(f"truncated: {report['truncated']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    if args.targets_out:
        print(f"targets: {args.targets_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
