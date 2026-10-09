#!/usr/bin/env python3
"""Plan a deterministic targeted instruction export from subsystem frontier evidence.

The planner consumes the one-hop method frontier and selects functions for the
existing targeted Ghidra instruction exporter. Selection is operational only:
it prioritizes functions with more independent direct links into an established
subsystem slice, but never promotes or renames them.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

from build_subsystem_method_frontier import build_subsystem_method_frontier

FORMAT = "SHIFT.GhidraSubsystemFrontierInstructionPlan/1"
DEFAULT_MAX_TARGETS = 32


def _selection_key(row: dict[str, Any]) -> tuple[Any, ...]:
    connected = row.get("connected_slice_addresses") or []
    links = row.get("direct_links") or []
    return (
        str(row.get("subsystem") or ""),
        -len(connected),
        -len(links),
        str(row.get("address") or ""),
    )


def _normalize_subsystems(values: Iterable[str] | None) -> list[str] | None:
    if values is None:
        return None
    result = sorted({str(value).strip() for value in values if str(value).strip()})
    return result or None


def build_instruction_plan(
    root: Path,
    *,
    subsystems: Iterable[str] | None = None,
    max_targets: int = DEFAULT_MAX_TARGETS,
) -> dict[str, Any]:
    if max_targets < 1:
        raise ValueError("max_targets must be >= 1")

    frontier = build_subsystem_method_frontier(root)
    selected_subsystems = _normalize_subsystems(subsystems)
    available_subsystems = sorted((frontier.get("subsystems") or {}).keys())
    if selected_subsystems is not None:
        unknown = sorted(set(selected_subsystems) - set(available_subsystems))
        if unknown:
            raise ValueError("unknown subsystem(s): " + ", ".join(unknown))

    candidates = [
        row
        for row in (frontier.get("frontier_candidates") or [])
        if row.get("frontier_candidate") is True
        and row.get("promoted") is not True
        and isinstance(row.get("address"), str)
        and isinstance(row.get("subsystem"), str)
        and (
            selected_subsystems is None
            or row["subsystem"] in selected_subsystems
        )
    ]
    candidates.sort(key=_selection_key)

    selected = candidates[:max_targets]
    omitted = candidates[max_targets:]
    plan_rows: list[dict[str, Any]] = []
    for index, row in enumerate(selected):
        links = row.get("direct_links") or []
        connected = row.get("connected_slice_addresses") or []
        directions = sorted(
            {
                str(link.get("direction"))
                for link in links
                if isinstance(link, dict) and link.get("direction") is not None
            }
        )
        plan_rows.append(
            {
                "selection_order": index,
                "address": row["address"],
                "ghidra_name": row.get("ghidra_name"),
                "method_name": row.get("method_name"),
                "subsystem": row["subsystem"],
                "direct_link_count": len(links),
                "connected_slice_count": len(connected),
                "connected_slice_addresses": list(connected),
                "direct_link_directions": directions,
                "calling_convention": row.get("calling_convention"),
                "size": row.get("size"),
                "mnemonic_sha256": row.get("mnemonic_sha256"),
                "reason": "one-hop exact-method frontier candidate",
                "promoted": False,
            }
        )

    targets = [row["address"] for row in plan_rows]
    return {
        "format": FORMAT,
        "ghidra_export": str(root),
        "frontier_format": frontier.get("format"),
        "source": frontier.get("source"),
        "requested_subsystems": selected_subsystems,
        "available_subsystems": available_subsystems,
        "max_targets": max_targets,
        "eligible_candidate_count": len(candidates),
        "selected_target_count": len(plan_rows),
        "omitted_target_count": len(omitted),
        "targets": targets,
        "selections": plan_rows,
        "scope": {
            "frontier_candidates_only": True,
            "direct_call_evidence_only": True,
            "selection_is_semantic_promotion": False,
            "automatic_function_renaming_performed": False,
            "instruction_semantics_proven": False,
            "note": (
                "The plan is a deterministic work queue for targeted instruction export. "
                "Ordering uses subsystem, distinct connected slice functions, direct-link "
                "count and address. It is not a confidence score and does not change any "
                "semantic evidence state."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument(
        "--subsystem",
        action="append",
        dest="subsystems",
        help="limit to one subsystem; may be repeated",
    )
    parser.add_argument(
        "--max-targets",
        type=int,
        default=DEFAULT_MAX_TARGETS,
        help=f"maximum selected functions (default: {DEFAULT_MAX_TARGETS})",
    )
    parser.add_argument("--json-out", type=Path)
    parser.add_argument(
        "--targets-out",
        type=Path,
        help="optional newline-delimited address list for run_shift_function_instructions.sh",
    )
    args = parser.parse_args()

    report = build_instruction_plan(
        args.ghidra_export,
        subsystems=args.subsystems,
        max_targets=args.max_targets,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    if args.targets_out:
        args.targets_out.parent.mkdir(parents=True, exist_ok=True)
        args.targets_out.write_text(
            "".join(f"{address}\n" for address in report["targets"]),
            encoding="utf-8",
        )

    print(f"format: {report['format']}")
    print(f"eligible frontier candidates: {report['eligible_candidate_count']}")
    print(f"selected targets: {report['selected_target_count']}")
    print(f"omitted targets: {report['omitted_target_count']}")
    for row in report["selections"]:
        print(f"{row['selection_order']:02d} {row['subsystem']} {row['address']} {row['method_name']}")
    if args.json_out:
        print(f"plan: {args.json_out}")
    if args.targets_out:
        print(f"targets: {args.targets_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
