#!/usr/bin/env python3
"""Rank +0x138 wheel-runtime alias/callee/bulk-copy candidates for P1.3D.

Input is produced by ShiftWheelRuntimeAliasExporter.java. The output is a finite
candidate inventory only. A candidate is never promoted to the selected
HDVehicle+0x28b8 writer without exact receiver provenance and f64/qword write
proof.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

INPUT_FORMAT = "SHIFT.GhidraWheelRuntimeAliasUses/1"
FORMAT = "SHIFT.P1D.Slot3WheelRuntimeAliasInventory/1"
KNOWN_CONSUMER = "FUN_00755950"
KNOWN_CALLER = "FUN_00758b50"


def read_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        rec = json.loads(raw)
        if rec.get("format") != INPUT_FORMAT:
            raise ValueError(f"{path}:{line_no}: unexpected format {rec.get('format')!r}")
        if rec.get("field_offset") != "0x138":
            raise ValueError(f"{path}:{line_no}: unexpected field offset {rec.get('field_offset')!r}")
        rows.append(rec)
    return rows


def use_classes(rec: dict) -> set[str]:
    classes: set[str] = set()
    for use in rec.get("uses", []):
        ops = set(use.get("pcode_ops", []))
        mnemonic = str(use.get("mnemonic", "")).lower()
        if "STORE" in ops or mnemonic.startswith(("fst", "mov", "stos")):
            classes.add("store-like")
        if "LOAD" in ops:
            classes.add("load-like")
        if ops.intersection({"PTRADD", "PTRSUB", "INT_ADD", "INT_MULT"}) or mnemonic == "lea":
            classes.add("address-materializer")
        if ops.intersection({"COPY", "PIECE", "SUBPIECE"}):
            classes.add("copy-like")
        if ops.intersection({"CALL", "CALLIND"}) or mnemonic.startswith("call"):
            classes.add("call-use")
    if rec.get("has_call"):
        classes.add("function-has-call")
    if rec.get("has_indirect_call"):
        classes.add("function-has-indirect-call")
    if rec.get("has_copy_like"):
        classes.add("function-has-copy-like")
    return classes


def rank(rec: dict) -> tuple[int, list[str]]:
    reasons: list[str] = []
    score = 0
    classes = use_classes(rec)

    if rec.get("runtime_base_hint"):
        score += 3
        reasons.append("same-function +0x400 wheel-runtime base hint")
    if rec.get("stride_hint"):
        score += 4
        reasons.append("same-function +0xa80 wheel stride hint")
    if rec.get("slot3_absolute_hint"):
        score += 1
        reasons.append("same-function +0x28b8 scalar hint only")
    if "store-like" in classes:
        score += 6
        reasons.append("exact +0x138 use is store-like")
    if "address-materializer" in classes:
        score += 5
        reasons.append("exact +0x138 use participates in address arithmetic")
    if "call-use" in classes:
        score += 5
        reasons.append("exact +0x138 use reaches a call instruction")
    if "function-has-call" in classes:
        score += 2
        reasons.append("function containing +0x138 use also contains call p-code")
    if "function-has-indirect-call" in classes:
        score += 2
        reasons.append("function containing +0x138 use also contains indirect call")
    if "copy-like" in classes or "function-has-copy-like" in classes:
        score += 2
        reasons.append("copy-like p-code is present")

    return score, reasons


def analyze(path: Path) -> dict:
    rows = read_rows(path)
    ranked: list[dict] = []
    for rec in rows:
        score, reasons = rank(rec)
        classes = sorted(use_classes(rec))
        ranked.append(
            {
                "function_address": rec.get("function_address"),
                "function_name": rec.get("function_name"),
                "score": score,
                "reasons": reasons,
                "usage_classes": classes,
                "runtime_base_hint": bool(rec.get("runtime_base_hint")),
                "stride_hint": bool(rec.get("stride_hint")),
                "slot3_absolute_hint": bool(rec.get("slot3_absolute_hint")),
                "field_use_count": int(rec.get("field_use_count", 0)),
                "uses": rec.get("uses", []),
                "candidate_only": True,
                "selected_hdvehicle_root_proven": False,
                "f64_qword_write_proven": False,
            }
        )

    ranked.sort(key=lambda item: (-item["score"], item["function_address"] or ""))
    strong = [
        item for item in ranked
        if item["runtime_base_hint"] and item["stride_hint"]
        and set(item["usage_classes"]).intersection({"store-like", "address-materializer", "call-use"})
    ]
    known_consumer = [item for item in ranked if item["function_name"] == KNOWN_CONSUMER]
    known_caller = [item for item in ranked if item["function_name"] == KNOWN_CALLER]

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "scope": "selected HDVehicle+0x28b8 alias/callee/bulk-copy writer provenance",
        "input_format": INPUT_FORMAT,
        "target": {
            "per_wheel_field": "+0x138",
            "wheel_runtime_base": "+0x400",
            "wheel_stride": "+0xa80",
            "slot3_absolute": "+0x28b8",
            "known_consumer": KNOWN_CONSUMER,
            "known_consumer_caller": KNOWN_CALLER,
        },
        "counts": {
            "functions_with_exact_0x138_use": len(ranked),
            "strong_topology_candidates": len(strong),
            "known_consumer_rows": len(known_consumer),
            "known_caller_rows": len(known_caller),
        },
        "strong_topology_candidates": strong,
        "ranked_candidates": ranked,
        "adjudication": {
            "inventory_complete_for_exported_exact_0x138_uses": True,
            "scalar_or_topology_hints_prove_object_identity": False,
            "selected_hdvehicle_slot3_writer_proven": False,
            "retail_input_control_provenance_proven": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "promotion_requirements": [
            "prove the candidate base aliases the selected HDVehicle wheel-runtime root HDVehicle+0x400+slot*0xa80",
            "prove slot=3 reaches selected HDVehicle+0x28b8 rather than an unrelated +0x138 subobject",
            "prove an f64/qword write or a bulk-copy range that covers exactly the target field",
            "trace the written value backward to its exact PC-retail producer before assigning semantics",
        ],
        "next_step": (
            "Run the exporter on authoritative PC retail 1.02 Ghidra, inspect strong topology candidates first, "
            "then adjudicate exact receiver/base and write width. If no strong candidate writes the field, "
            "extend the machine trace through callees receiving a materialized +0x138 alias or copy ranges."
        ),
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
