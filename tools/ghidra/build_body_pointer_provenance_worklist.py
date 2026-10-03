#!/usr/bin/env python3
"""Build an exact instruction-level BODY pointer-provenance worklist.

This consumes the p-code BODY bridge candidates plus their proven-callgraph
frontier join.  It produces one audit task per participating instruction and a
minimal function target list for follow-up ABI/register-dataflow work.  It does
not infer pointer identity or integration semantics.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.BodyPointerProvenanceWorklist/1"
BRIDGE_FORMAT = "SHIFT.BodyWriterBridgeCandidates/1"
JOIN_FORMAT = "SHIFT.BodyWriterBridgeFrontierJoin/1"

_RELATION_ORDER = {
    "proven-slice-root": 0,
    "callgraph-frontier": 1,
    "outside-selected-frontier": 2,
}


def _load(path: Path, expected: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}")
    return value


def _hex_address(value: Any, *, field: str) -> int:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field}: missing hexadecimal address")
    try:
        return int(value, 0)
    except ValueError as exc:
        raise ValueError(f"{field}: invalid hexadecimal address {value!r}") from exc


def _key(row: dict[str, Any]) -> tuple[str, str, str]:
    function = row.get("function")
    base_register = row.get("base_register")
    kind = row.get("kind")
    if not all(isinstance(v, str) and v for v in (function, base_register, kind)):
        raise ValueError("candidate function/base_register/kind missing")
    return function, base_register.upper(), kind


def build_body_pointer_provenance_worklist(
    bridge_report: dict[str, Any],
    frontier_join: dict[str, Any],
) -> dict[str, Any]:
    if bridge_report.get("format") != BRIDGE_FORMAT:
        raise ValueError(f"expected {BRIDGE_FORMAT}")
    if frontier_join.get("format") != JOIN_FORMAT:
        raise ValueError(f"expected {JOIN_FORMAT}")

    bridge_rows = bridge_report.get("candidates")
    join_rows = frontier_join.get("candidates")
    if not isinstance(bridge_rows, list):
        raise ValueError("bridge candidates must be a list")
    if not isinstance(join_rows, list):
        raise ValueError("frontier join candidates must be a list")

    join_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    duplicate_join_keys: list[tuple[str, str, str]] = []
    for row in join_rows:
        if not isinstance(row, dict):
            continue
        key = _key(row)
        if key in join_by_key:
            duplicate_join_keys.append(key)
            continue
        join_by_key[key] = row

    work_items: list[dict[str, Any]] = []
    unmatched_candidates: list[dict[str, Any]] = []
    target_functions: set[str] = set()

    for index, candidate in enumerate(bridge_rows):
        if not isinstance(candidate, dict):
            unmatched_candidates.append({"index": index, "reason": "candidate is not an object"})
            continue
        key = _key(candidate)
        function, base_register, kind = key
        _hex_address(function, field=f"candidates[{index}].function")
        context = join_by_key.get(key)
        if context is None:
            unmatched_candidates.append(
                {
                    "index": index,
                    "function": function,
                    "base_register": base_register,
                    "kind": kind,
                    "reason": "no exact frontier-join row",
                }
            )
            continue

        target_functions.add(function)
        accesses: dict[int, dict[str, Any]] = {}
        for role, field in (("read", "read_evidence"), ("write", "write_evidence")):
            evidence = candidate.get(field)
            if not isinstance(evidence, list) or not evidence:
                raise ValueError(f"candidates[{index}].{field} must be a non-empty list")
            for evidence_index, row in enumerate(evidence):
                if not isinstance(row, dict):
                    raise ValueError(f"candidates[{index}].{field}[{evidence_index}] must be an object")
                instruction_text = row.get("instruction")
                instruction = _hex_address(
                    instruction_text,
                    field=f"candidates[{index}].{field}[{evidence_index}].instruction",
                )
                item = accesses.setdefault(
                    instruction,
                    {
                        "instruction": instruction_text,
                        "instruction_text": row.get("instruction_text"),
                        "roles": [],
                        "offsets": [],
                        "offsets_hex": [],
                        "lanes": [],
                        "pcode_memory_ops": [],
                    },
                )
                if role not in item["roles"]:
                    item["roles"].append(role)
                displacement = row.get("displacement")
                if isinstance(displacement, int) and displacement not in item["offsets"]:
                    item["offsets"].append(displacement)
                displacement_hex = row.get("displacement_hex")
                if isinstance(displacement_hex, str) and displacement_hex not in item["offsets_hex"]:
                    item["offsets_hex"].append(displacement_hex)
                for lane in row.get("lanes") or []:
                    if isinstance(lane, str) and lane not in item["lanes"]:
                        item["lanes"].append(lane)
                for op in row.get("pcode_memory_ops") or []:
                    if isinstance(op, str) and op not in item["pcode_memory_ops"]:
                        item["pcode_memory_ops"].append(op)

        relation = context.get("frontier_relation")
        min_depth = context.get("min_depth")
        instructions = [accesses[address] for address in sorted(accesses)]
        for item in instructions:
            item["roles"].sort()
            item["offsets"].sort()
            item["offsets_hex"] = sorted(set(item["offsets_hex"]))
            item["lanes"].sort()
            item["pcode_memory_ops"].sort()
            item["provenance_required"] = {
                "function": function,
                "base_register": base_register,
                "instruction_start": item["instruction"],
                "instruction_end": item["instruction"],
                "required_object_identity": "BODY",
                "status": "unresolved",
            }

        work_items.append(
            {
                "function": function,
                "function_name": candidate.get("function_name"),
                "base_register": base_register,
                "kind": kind,
                "frontier_relation": relation,
                "min_depth": min_depth,
                "connected_subsystems": list(context.get("connected_subsystems") or []),
                "adjacent_proven_slice_addresses": list(
                    context.get("adjacent_proven_slice_addresses") or []
                ),
                "slice_callers": list(context.get("slice_callers") or []),
                "ordered_slice_calls": list(context.get("ordered_slice_calls") or []),
                "multi_anchor_caller_candidate": context.get("multi_anchor_caller_candidate") is True,
                "indirect_call_sites": list(context.get("indirect_call_sites") or []),
                "instruction_count": len(instructions),
                "instructions": instructions,
                "proof_status": "needs-body-pointer-provenance",
                "persistent_writer_proven": False,
            }
        )

    work_items.sort(
        key=lambda row: (
            _RELATION_ORDER.get(str(row["frontier_relation"]), 99),
            row["min_depth"] if isinstance(row["min_depth"], int) else 1 << 30,
            int(row["function"], 0),
            row["base_register"],
            row["kind"],
        )
    )

    instruction_task_count = sum(row["instruction_count"] for row in work_items)
    by_function: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in work_items:
        by_function[row["function"]].append(row)
    function_worklist = [
        {
            "function": function,
            "candidate_kinds": sorted({row["kind"] for row in rows}),
            "base_registers": sorted({row["base_register"] for row in rows}),
            "instruction_count": sum(row["instruction_count"] for row in rows),
            "frontier_relations": sorted({str(row["frontier_relation"]) for row in rows}),
            "min_depth": min(
                (row["min_depth"] for row in rows if isinstance(row["min_depth"], int)),
                default=None,
            ),
        }
        for function, rows in sorted(by_function.items(), key=lambda pair: int(pair[0], 0))
    ]

    return {
        "format": FORMAT,
        "bridge_format": BRIDGE_FORMAT,
        "frontier_join_format": JOIN_FORMAT,
        "candidate_work_item_count": len(work_items),
        "function_work_item_count": len(function_worklist),
        "instruction_provenance_task_count": instruction_task_count,
        "unmatched_candidate_count": len(unmatched_candidates),
        "duplicate_join_key_count": len(set(duplicate_join_keys)),
        "function_targets": sorted(target_functions, key=lambda value: int(value, 0)),
        "functions": function_worklist,
        "candidates": work_items,
        "unmatched_candidates": unmatched_candidates,
        "duplicate_join_keys": [
            {"function": key[0], "base_register": key[1], "kind": key[2]}
            for key in sorted(set(duplicate_join_keys))
        ],
        "scope": {
            "instruction_level_pointer_provenance_required": True,
            "single_instruction_ranges_are_default": True,
            "frontier_relation_is_pointer_proof": False,
            "same_register_is_pointer_proof": False,
            "required_identity": "BODY",
            "persistent_state_writer_proven": False,
            "integration_semantics_proven": False,
            "frame_ordering_proven": False,
            "native_pose_port_ready": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bridge_candidates", type=Path)
    parser.add_argument("--frontier-join", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--targets-out", type=Path)
    parser.add_argument("--fail-on-unmatched", action="store_true")
    args = parser.parse_args()

    bridge = _load(args.bridge_candidates, BRIDGE_FORMAT)
    join = _load(args.frontier_join, JOIN_FORMAT)
    report = build_body_pointer_provenance_worklist(bridge, join)

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.targets_out:
        args.targets_out.parent.mkdir(parents=True, exist_ok=True)
        args.targets_out.write_text("\n".join(report["function_targets"]) + ("\n" if report["function_targets"] else ""), encoding="utf-8")

    print(f"format: {report['format']}")
    print(f"candidate work items: {report['candidate_work_item_count']}")
    print(f"function work items: {report['function_work_item_count']}")
    print(f"instruction provenance tasks: {report['instruction_provenance_task_count']}")
    print(f"unmatched candidates: {report['unmatched_candidate_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    if args.targets_out:
        print(f"targets: {args.targets_out}")
    if args.fail_on_unmatched and report["unmatched_candidate_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
