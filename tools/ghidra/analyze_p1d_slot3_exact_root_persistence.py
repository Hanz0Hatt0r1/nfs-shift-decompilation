#!/usr/bin/env python3
"""Rank exact wheel-root persistence/escape candidates exported from bounded carrier windows.

The exporter windows are seeded only from already-merged retail machine proofs. This
analyzer remains candidate-only: a register mention, push, copy, or store is not
promoted to selected slot3 persistence without instruction-level adjudication of the
exact-root lifetime and destination/consumer.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

INPUT_FORMAT = "SHIFT.GhidraExactWheelRootPersistenceUses/1"
FORMAT = "SHIFT.P1D.Slot3ExactRootPersistenceFrontier/1"

EXPECTED = {
    "FUN_00758b50": ("0x00758b50", "ecx", "0x00758ccf", "0x00758d70"),
    "FUN_00755950": ("0x00755950", "edx", "0x00755956", "0x00755992"),
    "FUN_00755a60": ("0x00755a60", "esi", "0x00755a73", "0x00755f71"),
    "FUN_00752fc0": ("0x00752fc0", "ecx", "0x00752fc0", "0x00752fe5"),
    "FUN_00760b50": ("0x00760b50", "esi", "0x00760b6a", "0x00760d63"),
    "FUN_00755f80": ("0x00755f80", "esi", "0x00755f9a", "0x00756004"),
}

WEIGHTS = {
    "memory-store-root": 100,
    "push-root": 90,
    "register-copy-root": 60,
    "derived-address-root": 50,
    "call-boundary": 25,
    "root-based-memory-destination": 10,
    "root-based-memory-source": 5,
    "other-root-use": 1,
}


def read_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        row = json.loads(raw)
        if row.get("format") != INPUT_FORMAT:
            raise ValueError(f"{path}:{line_no}: unexpected format {row.get('format')!r}")
        rows.append(row)
    return rows


def validate(rows: list[dict]) -> dict[str, dict]:
    by_name: dict[str, dict] = {}
    for row in rows:
        name = str(row.get("function_name") or "")
        if name not in EXPECTED:
            raise ValueError(f"unexpected carrier in persistence export: {name!r}")
        if name in by_name:
            raise ValueError(f"duplicate carrier in persistence export: {name}")
        address, register, start, end = EXPECTED[name]
        observed = (
            str(row.get("function_address") or "").lower(),
            str(row.get("root_register") or "").lower(),
            str(row.get("window_start") or "").lower(),
            str(row.get("window_end_exclusive") or "").lower(),
        )
        expected = (address, register, start, end)
        if observed != expected:
            raise ValueError(f"{name}: exact-root window drift: {observed!r} != {expected!r}")
        by_name[name] = row
    missing = sorted(set(EXPECTED) - set(by_name))
    if missing:
        raise ValueError(f"missing exact-root carrier windows: {missing}")
    return by_name


def candidate_score(kinds: list[str]) -> int:
    return max((WEIGHTS.get(kind, 0) for kind in kinds), default=0)


def analyze(path: Path) -> dict:
    rows = read_rows(path)
    by_name = validate(rows)
    candidates: list[dict] = []
    totals = {
        "carrier_windows": len(by_name),
        "root_mentions": 0,
        "call_boundaries": 0,
        "memory_store_root": 0,
        "push_root": 0,
        "register_copy_root": 0,
        "derived_address_root": 0,
    }

    per_carrier: list[dict] = []
    for name in EXPECTED:
        row = by_name[name]
        totals["root_mentions"] += int(row.get("root_mention_count", 0))
        totals["call_boundaries"] += int(row.get("call_boundary_count", 0))
        totals["memory_store_root"] += int(row.get("memory_store_root_count", 0))
        totals["push_root"] += int(row.get("push_root_count", 0))
        totals["register_copy_root"] += int(row.get("register_copy_root_count", 0))
        totals["derived_address_root"] += int(row.get("derived_address_root_count", 0))

        uses = row.get("uses", [])
        for use in uses:
            kinds = [str(x) for x in use.get("candidate_kinds", [])]
            score = candidate_score(kinds)
            candidates.append({
                "function_name": name,
                "function_address": row["function_address"],
                "root_register": row["root_register"],
                "instruction_address": use.get("instruction_address"),
                "mnemonic": use.get("mnemonic"),
                "text": use.get("text"),
                "candidate_kinds": kinds,
                "score": score,
                "exact_root_register_mentioned": bool(use.get("exact_root_register_mentioned")),
                "pcode_ops": use.get("pcode_ops", []),
                "semantic_persistence_proven": False,
                "selected_slot3_destination_or_consumer_proven": False,
            })

        per_carrier.append({
            "function_name": name,
            "function_address": row["function_address"],
            "root_register": row["root_register"],
            "window_start": row["window_start"],
            "window_end_exclusive": row["window_end_exclusive"],
            "identity_note": row.get("identity_note"),
            "root_mention_count": int(row.get("root_mention_count", 0)),
            "call_boundary_count": int(row.get("call_boundary_count", 0)),
            "memory_store_root_count": int(row.get("memory_store_root_count", 0)),
            "push_root_count": int(row.get("push_root_count", 0)),
            "register_copy_root_count": int(row.get("register_copy_root_count", 0)),
            "derived_address_root_count": int(row.get("derived_address_root_count", 0)),
        })

    candidates.sort(
        key=lambda item: (
            -item["score"],
            item["function_address"],
            str(item["instruction_address"] or ""),
        )
    )
    high_priority = [item for item in candidates if item["score"] >= 50]

    return {
        "format": FORMAT,
        "version": 1,
        "ready": True,
        "owner": "Process 1D / P1.3D",
        "input_format": INPUT_FORMAT,
        "scope": "machine-proven exact wheel-root persistence/escape candidate frontier",
        "authority": {
            "export_windows_are_seeded_from_merged_machine_contracts": True,
            "exporter_or_analyzer_does_not_extend_semantic_root_lifetime": True,
            "candidate_classification_is_not_writer_or_escape_proof": True,
        },
        "counts": {
            **totals,
            "candidate_rows": len(candidates),
            "high_priority_rows": len(high_priority),
        },
        "carrier_windows": per_carrier,
        "high_priority_candidates": high_priority,
        "ranked_candidates": candidates,
        "adjudication": {
            "bounded_exact_root_window_inventory_complete": True,
            "persistence_candidates_ranked": True,
            "exact_root_persistent_store_proven": False,
            "exact_root_escape_to_stack_or_argument_proven": False,
            "derived_register_alias_persistence_proven": False,
            "machine_register_alias_storage_ruled_out": False,
            "callee_created_aliases_ruled_out": False,
            "callbacks_registered_outside_carriers_ruled_out": False,
            "stored_or_escaped_aliases_ruled_out": False,
            "slot3_writer_provenance_proven": False,
            "p1_3d_complete": False,
            "p1_3_control_producer_complete": False,
            "external_provider_count": 7,
        },
        "promotion_requirements": [
            "adjudicate each high-priority instruction against the exact-root register lifetime proven by machine code",
            "for memory stores, prove destination ownership and later loads/consumers before declaring persistence",
            "for push/call candidates, prove argument position and callee semantics before declaring escape",
            "for register copies or LEA-derived aliases, follow the derived value until kill/store/call and prove selected slot3 identity",
            "do not use register-name coincidence or numeric offsets as semantic selected-wheel identity",
        ],
        "next_step": (
            "Run ShiftExactWheelRootPersistenceExporter.java on authoritative PC retail 1.02, feed the JSONL here, "
            "then adjudicate memory-store-root and push-root candidates first."
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
