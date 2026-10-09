#!/usr/bin/env python3
"""Rank wheel-topology functions that may reach P1.3A slot0/slot1 without literal +0x538.

The input is produced by ShiftP13ASlot01TopologyAliasExporter.java. Every row
already has same-function +0x400 and +0xa80 scalar hints. Results remain
candidate-only until exact selected-HDVehicle root provenance and write-range
coverage are proven.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

INPUT_FORMAT = "SHIFT.GhidraP13ASlot01TopologyAliasCandidates/1"
FORMAT = "SHIFT.P1A.P13ASlot01TopologyAliasInventory/1"


def read_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        rec = json.loads(raw)
        if rec.get("format") != INPUT_FORMAT:
            raise ValueError(f"{path}:{line_no}: unexpected format {rec.get('format')!r}")
        if not rec.get("runtime_base_hint") or not rec.get("stride_hint"):
            raise ValueError(f"{path}:{line_no}: exporter row is missing required +0x400/+0xa80 topology")
        rows.append(rec)
    return rows


def operation_classes(rec: dict) -> set[str]:
    classes: set[str] = set()
    if rec.get("has_store"):
        classes.add("store-like")
    if rec.get("has_load"):
        classes.add("load-like")
    if rec.get("has_call"):
        classes.add("call-use")
    if rec.get("has_indirect_call"):
        classes.add("indirect-call")
    if rec.get("has_copy_like"):
        classes.add("copy-like")
    if rec.get("has_address_arithmetic"):
        classes.add("address-arithmetic")
    return classes


def rank(rec: dict) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    classes = operation_classes(rec)
    score += 7
    reasons.append("same-function +0x400 wheel-runtime and +0xa80 stride hints")
    if "store-like" in classes:
        score += 7
        reasons.append("function contains store p-code")
    if "copy-like" in classes:
        score += 6
        reasons.append("function contains copy/piece/subpiece p-code")
    if "call-use" in classes:
        score += 4
        reasons.append("function contains direct or indirect call p-code")
    if "indirect-call" in classes:
        score += 2
        reasons.append("function contains indirect call p-code")
    if "address-arithmetic" in classes:
        score += 4
        reasons.append("function contains address arithmetic p-code")
    if rec.get("slot0_absolute_hint"):
        score += 2
        reasons.append("same-function 0x938 scalar hint")
    if rec.get("slot1_absolute_hint"):
        score += 2
        reasons.append("same-function 0x13b8 scalar hint")
    if rec.get("exact_local_0x538_hint"):
        score -= 5
        reasons.append("contains literal +0x538 and belongs to the already-bounded exact-field subset")
    return score, reasons


def analyze(path: Path) -> dict:
    rows = read_rows(path)
    ranked: list[dict] = []
    for rec in rows:
        score, reasons = rank(rec)
        classes = sorted(operation_classes(rec))
        ranked.append({
            "function_address": rec.get("function_address"),
            "function_name": rec.get("function_name"),
            "score": score,
            "reasons": reasons,
            "operation_classes": classes,
            "exact_local_0x538_hint": bool(rec.get("exact_local_0x538_hint")),
            "slot0_absolute_hint": bool(rec.get("slot0_absolute_hint")),
            "slot1_absolute_hint": bool(rec.get("slot1_absolute_hint")),
            "events": rec.get("events", []),
            "candidate_only": True,
            "selected_hdvehicle_root_proven": False,
            "target_range_write_proven": False,
        })
    ranked.sort(key=lambda item: (-item["score"], item["function_address"] or ""))
    novel = [
        item for item in ranked
        if not item["exact_local_0x538_hint"]
        and set(item["operation_classes"]).intersection({"store-like", "copy-like", "call-use", "address-arithmetic"})
    ]
    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1A / P1.3A",
        "scope": "slot0 HDVehicle+0x938 and slot1 HDVehicle+0x13b8 base-plus-delta alias/callee/bulk-copy frontier",
        "input_format": INPUT_FORMAT,
        "known_topology": {
            "wheel_runtime_base": "+0x400",
            "wheel_stride": "+0xa80",
            "local_field": "+0x538",
            "slot0_absolute": "+0x938",
            "slot1_absolute": "+0x13b8"
        },
        "counts": {
            "topology_functions": len(ranked),
            "novel_nonliteral_0x538_candidates": len(novel),
            "already_exact_0x538_subset_rows": sum(1 for item in ranked if item["exact_local_0x538_hint"])
        },
        "novel_candidates": novel,
        "ranked_candidates": ranked,
        "adjudication": {
            "inventory_complete_for_exported_same_function_topology": True,
            "same_function_topology_proves_selected_hdvehicle_root": False,
            "nonliteral_alias_or_bulk_copy_writer_proven": False,
            "p13a_slot0_complete": False,
            "p13a_slot1_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7
        },
        "promotion_requirements": [
            "prove the candidate base derives from the selected HDVehicle root rather than an unrelated +0x400/+0xa80 object",
            "normalize the candidate address expression to slot0 HDVehicle+0x938 or slot1 HDVehicle+0x13b8",
            "prove an f64/qword store or a bulk-copy/memory-initialization destination range covering the target bytes",
            "trace callee forwarding and backward value provenance before assigning producer semantics"
        ],
        "next_step": "Run the exporter on authoritative PC retail 1.02 Ghidra, inspect novel_candidates before rows that contain literal +0x538, then adjudicate exact selected-root provenance and target-byte write coverage."
    }


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
