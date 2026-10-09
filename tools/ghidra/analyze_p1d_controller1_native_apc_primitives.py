#!/usr/bin/env python3
"""Classify machine primitives relevant to manual API resolution and direct native APC paths.

Input is the JSONL produced by ShiftNativeResolutionPrimitiveExporter.java.
This is a bounded navigation/adjudication aid, not a universal no-APC theorem.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

FORMAT = "SHIFT.P1D.Controller1NativeApcPrimitiveFrontier/1"
ROW_FORMAT = "SHIFT.GhidraNativeResolutionPrimitiveInventory/1"

PEB_RE = re.compile(r"fs\s*:\s*\[[^\]]*(?:0x)?0*30(?:h)?\]", re.I)
EXPORT_RVA_RE = re.compile(r"(?:0x)?0*78(?:h)?\b", re.I)
ELFANEW_RE = re.compile(r"(?:0x)?0*3c(?:h)?\b", re.I)


def read_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
        if row.get("format") != ROW_FORMAT:
            raise ValueError(f"{path}:{line_no}: unexpected format {row.get('format')!r}")
        rows.append(row)
    return rows


def classify(rows: list[dict]) -> dict:
    by_function: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_function[str(row.get("function", "<unknown>"))].append(row)

    candidates: list[dict] = []
    for function in sorted(by_function):
        group = by_function[function]
        texts = [str(row.get("text", "")) for row in group]
        peb = [row for row in group if bool(row.get("fs_access")) and PEB_RE.search(str(row.get("text", "")))]
        sysenter = [row for row in group if bool(row.get("sysenter"))]
        int2e = [row for row in group if bool(row.get("int2e"))]
        has_e_lfanew = any(ELFANEW_RE.search(text) for text in texts)
        has_export_rva = any(EXPORT_RVA_RE.search(text) for text in texts)
        manual_export_walk_candidate = bool(peb) and has_e_lfanew and has_export_rva
        direct_native_call_candidate = bool(sysenter or int2e)
        if not (manual_export_walk_candidate or direct_native_call_candidate):
            continue
        candidates.append(
            {
                "function": function,
                "function_address": group[0].get("function_address"),
                "manual_export_walk_candidate": manual_export_walk_candidate,
                "direct_native_call_candidate": direct_native_call_candidate,
                "peb_access_sites": [row.get("address") for row in peb],
                "sysenter_sites": [row.get("address") for row in sysenter],
                "int2e_sites": [row.get("address") for row in int2e],
                "has_e_lfanew_hint": has_e_lfanew,
                "has_export_directory_rva_hint": has_export_rva,
            }
        )

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "scope": "Controller #1 indirect/native APC timing",
        "input_row_count": len(rows),
        "candidate_function_count": len(candidates),
        "candidate_functions": candidates,
        "adjudication": {
            "manual_export_walk_surface_inventory_complete_for_emitted_primitives": True,
            "direct_sysenter_int2e_surface_inventory_complete_for_emitted_primitives": True,
            "candidate_presence_proves_apc_injection": False,
            "candidate_absence_is_universal_no_apc_proof": False,
            "manual_export_walking_ruled_out": False,
            "native_or_syscall_apc_injection_ruled_out": False,
            "controller1_thread_handle_join_complete": False,
            "controller1_timing_exhaustive": False,
            "p1_3d_complete": False,
            "external_provider_count": 7,
        },
        "limits": [
            "PEB/export constants are navigation hints until local data flow proves a real export walk.",
            "SYSENTER/INT 0x2e presence does not identify an APC syscall number or target thread.",
            "Absence from this inventory does not rule out indirect calls through imported/native stubs, generated code, wow64 transitions or other syscall mechanisms.",
            "Every positive candidate must be joined to Controller #1 worker/thread-handle identity before affecting timing gates.",
        ],
        "next_step": (
            "Adjudicate every candidate function by exact local machine flow. For export-walk candidates, prove or reject module/export traversal and resolved target identity. "
            "For direct-native candidates, recover the syscall/service identity and target thread handle. Only then may Controller #1 APC timing advance."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = classify(read_rows(args.input))
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
