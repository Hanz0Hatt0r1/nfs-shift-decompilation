#!/usr/bin/env python3
"""Run memory-wrapper forwarding analysis with retail tail-call normalization.

The retail wrappers use direct terminal JMP instructions for several backend
transfers.  The base analyzer models backend CALL instructions and intra-function
JMP control flow conservatively; this driver presents external backend tail JMPs
as call-like transfers for the data-flow proof without changing the raw
instruction export.

The emitted artifact keeps the existing SHIFT-MEMORY-WRAPPER-FORWARDING/1
format and annotates every backend site with transfer_kind = call|tail-call.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

BASE_PATH = Path(__file__).with_name("analyze_memory_wrapper_forwarding.py")
SPEC = importlib.util.spec_from_file_location("_shift_memory_wrapper_forwarding_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load base analyzer: {BASE_PATH}")
base = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = base
SPEC.loader.exec_module(base)


def _read_rows(path: Path) -> list[dict[str, Any]]:
    return list(base._read_jsonl(path))


def _normalize_backend_tail_calls(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    normalized = copy.deepcopy(rows)
    tail_sites: dict[str, str] = {}
    for row in normalized:
        for instruction in row.get("instructions") or []:
            if not isinstance(instruction, dict):
                continue
            if str(instruction.get("mnemonic") or "").upper() != "JMP":
                continue
            target = base._call_target(instruction)
            if target not in base.BACKEND_SPECS:
                continue
            address = base._norm_address(instruction.get("address"))
            if address is None:
                continue
            tail_sites[address] = target
            # Analyze this terminal inter-function JMP as a call-like argument
            # transfer.  fallthrough remains null, so no return edge is invented.
            instruction["mnemonic"] = "CALL"
    return normalized, tail_sites


def analyze_memory_wrapper_forwarding_retail(path: Path) -> dict[str, Any]:
    rows = _read_rows(path)
    normalized, tail_sites = _normalize_backend_tail_calls(rows)

    with tempfile.TemporaryDirectory(prefix="shift-memory-forwarding-") as temp_dir:
        normalized_path = Path(temp_dir) / "normalized.jsonl"
        with normalized_path.open("w", encoding="utf-8") as handle:
            for row in normalized:
                handle.write(json.dumps(row, separators=(",", ":")) + "\n")
        report = base.analyze_memory_wrapper_forwarding(normalized_path)

    for wrapper in report.get("wrappers") or []:
        for site in wrapper.get("call_sites") or []:
            address = base._norm_address(site.get("instruction"))
            target = base._norm_address(site.get("target"))
            is_tail = address in tail_sites and tail_sites[address] == target
            site["transfer_kind"] = "tail-call" if is_tail else "call"

    report["instruction_export"] = str(path)
    report["tail_call_modeling"] = {
        "external_backend_tail_jmps_modeled": True,
        "tail_call_count": len(tail_sites),
        "tail_call_sites": [
            {"instruction": address, "target": target}
            for address, target in sorted(tail_sites.items())
        ],
        "raw_instruction_export_modified": False,
    }
    scope = report.setdefault("scope", {})
    scope["external_backend_tail_calls_modeled"] = True
    scope["ghidra_declared_parameter_semantics_trusted"] = False
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = analyze_memory_wrapper_forwarding_retail(args.instruction_export)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")

    print(f"format: {report['format']}")
    print(f"wrappers: {report['wrapper_count']}")
    print(f"confirmed forwarding: {report['confirmed_wrapper_forwarding_count']}")
    print(f"all forwarding confirmed: {report['all_wrapper_forwarding_confirmed']}")
    print(f"modeled tail calls: {report['tail_call_modeling']['tail_call_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
