#!/usr/bin/env python3
"""Build a fail-closed caller/ownership frontier above FUN_00770e80.

The persistent BODY integration path is now proven below FUN_00770e80. This
analyzer moves upward without assigning new semantics: it inventories direct
callers of the proven outer-update anchor, preserves each caller's ordered
direct-call sequence, measures shared call-shape, and walks a bounded number of
direct incoming edges to select the next instruction-level targets.

Direct-call proximity and shared call-shape are target-selection evidence only.
They do not prove frame scheduling, vehicle ownership, input ownership, or
object identity. Missing direct incoming edges remain an explicit ownership
blocker rather than being guessed from vtables or function pointers.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.GhidraVehicleOuterUpdateCallerFrontier/1"
OUTER_UPDATE = "0x00770e80"


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
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


def _address_key(value: Any) -> tuple[int, str]:
    if isinstance(value, str):
        try:
            return int(value, 16), value
        except ValueError:
            pass
    return (1 << 63), str(value or "")


def _edge(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "from_function": row.get("from_function"),
        "from_name": row.get("from_name"),
        "instruction": row.get("instruction"),
        "to": row.get("to"),
        "to_name": row.get("to_name"),
        "indirect": row.get("indirect"),
    }


def _function_record(function: dict[str, Any]) -> dict[str, Any]:
    return {
        "address": function.get("address"),
        "name": function.get("name"),
        "size": function.get("size"),
        "external": function.get("external"),
        "thunk": function.get("thunk"),
        "calling_convention": function.get("calling_convention"),
        "signature": function.get("signature"),
        "mnemonic_sha256": function.get("mnemonic_sha256"),
    }


def _common_prefix(sequences: list[list[str]]) -> list[str]:
    if not sequences:
        return []
    prefix: list[str] = []
    for values in zip(*sequences):
        first = values[0]
        if any(value != first for value in values[1:]):
            break
        prefix.append(first)
    return prefix


def build_vehicle_outer_update_caller_frontier(
    root: Path,
    *,
    upstream_depth: int = 2,
    max_targets: int = 32,
) -> dict[str, Any]:
    if upstream_depth < 0:
        raise ValueError("upstream_depth must be >= 0")
    if max_targets < 1:
        raise ValueError("max_targets must be >= 1")

    required = ("binary.json", "functions.jsonl", "callgraph.jsonl", "switches.jsonl")
    missing = [name for name in required if not (root / name).is_file()]
    if missing:
        raise FileNotFoundError("missing required Ghidra files: " + ", ".join(missing))

    binary = json.loads((root / "binary.json").read_text(encoding="utf-8"))
    if not isinstance(binary, dict):
        raise ValueError("binary.json must contain an object")

    functions: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(root / "functions.jsonl"):
        address = row.get("address")
        if not isinstance(address, str):
            continue
        if address in functions:
            raise ValueError(f"duplicate function address {address}")
        functions[address] = row

    if OUTER_UPDATE not in functions:
        raise ValueError(f"outer-update anchor absent from functions.jsonl: {OUTER_UPDATE}")

    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    indirect: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in read_jsonl(root / "callgraph.jsonl"):
        source = row.get("from_function")
        target = row.get("to")
        if row.get("indirect") is True:
            if isinstance(source, str):
                indirect[source].append(row)
            continue
        if row.get("indirect") is not False:
            continue
        if not isinstance(source, str) or not isinstance(target, str):
            continue
        outgoing[source].append(row)
        incoming[target].append(row)

    for rows in outgoing.values():
        rows.sort(key=lambda row: _address_key(row.get("instruction")))
    for rows in incoming.values():
        rows.sort(key=lambda row: (_address_key(row.get("from_function")), _address_key(row.get("instruction"))))
    for rows in indirect.values():
        rows.sort(key=lambda row: _address_key(row.get("instruction")))

    switches_by_function: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in read_jsonl(root / "switches.jsonl"):
        function = row.get("function")
        if isinstance(function, str):
            switches_by_function[function].append(row)
    for rows in switches_by_function.values():
        rows.sort(key=lambda row: _address_key(row.get("instruction")))

    anchor_incoming = incoming.get(OUTER_UPDATE, [])
    caller_addresses = sorted(
        {row["from_function"] for row in anchor_incoming}, key=lambda value: int(value, 0)
    )
    if not caller_addresses:
        raise ValueError(f"no direct callers found for {OUTER_UPDATE}")

    caller_rows: list[dict[str, Any]] = []
    caller_sequences: list[list[str]] = []
    for address in caller_addresses:
        metadata = functions.get(address)
        if metadata is None:
            raise ValueError(f"direct caller missing from functions.jsonl: {address}")
        if metadata.get("external") is True:
            raise ValueError(f"direct caller unexpectedly external: {address}")

        anchor_calls = [row for row in outgoing.get(address, []) if row.get("to") == OUTER_UPDATE]
        if len(anchor_calls) != 1:
            raise ValueError(
                f"{address}: expected exactly one direct call to {OUTER_UPDATE}; "
                f"found {len(anchor_calls)}"
            )

        ordered = outgoing.get(address, [])
        sequence = [row["to"] for row in ordered]
        caller_sequences.append(sequence)
        anchor_index = ordered.index(anchor_calls[0])
        upstream = incoming.get(address, [])
        caller_rows.append(
            {
                **_function_record(metadata),
                "outer_update_call": _edge(anchor_calls[0]),
                "outer_update_call_index": anchor_index,
                "ordered_direct_calls": [_edge(row) for row in ordered],
                "direct_incoming_calls": [_edge(row) for row in upstream],
                "direct_incoming_count": len(upstream),
                "direct_outgoing_count": len(ordered),
                "indirect_call_sites": [_edge(row) for row in indirect.get(address, [])],
                "computed_jump_candidates": list(switches_by_function.get(address, [])),
                "ownership_status": (
                    "has-direct-upstream-caller" if upstream else "no-direct-upstream-caller"
                ),
                "promoted": False,
            }
        )

    shared_prefix = _common_prefix(caller_sequences)
    shared_prefix_rows = []
    for index, target in enumerate(shared_prefix):
        shared_prefix_rows.append(
            {
                "index": index,
                "target": target,
                "target_name": (functions.get(target) or {}).get("name"),
            }
        )

    upstream_distance: dict[str, int] = {address: 0 for address in caller_addresses}
    queue = deque(caller_addresses)
    while queue:
        current = queue.popleft()
        depth = upstream_distance[current]
        if depth >= upstream_depth:
            continue
        for edge in incoming.get(current, []):
            parent = edge.get("from_function")
            if not isinstance(parent, str) or parent in upstream_distance:
                continue
            upstream_distance[parent] = depth + 1
            queue.append(parent)

    upstream_rows: list[dict[str, Any]] = []
    for address, depth in sorted(
        ((address, depth) for address, depth in upstream_distance.items() if depth > 0),
        key=lambda pair: (pair[1], int(pair[0], 0)),
    ):
        metadata = functions.get(address)
        upstream_rows.append(
            {
                "address": address,
                "name": metadata.get("name") if metadata else None,
                "function_metadata_present": metadata is not None,
                "external": metadata.get("external") if metadata else None,
                "thunk": metadata.get("thunk") if metadata else None,
                "calling_convention": metadata.get("calling_convention") if metadata else None,
                "signature": metadata.get("signature") if metadata else None,
                "size": metadata.get("size") if metadata else None,
                "upstream_depth": depth,
                "direct_incoming_count": len(incoming.get(address, [])),
                "direct_outgoing_count": len(outgoing.get(address, [])),
                "ordered_direct_calls": [_edge(row) for row in outgoing.get(address, [])],
                "indirect_call_sites": [_edge(row) for row in indirect.get(address, [])],
                "computed_jump_candidates": list(switches_by_function.get(address, [])),
                "promoted": False,
            }
        )

    blocker_rows: list[dict[str, Any]] = []
    for row in caller_rows:
        if row["direct_incoming_count"] == 0:
            blocker_rows.append(
                {
                    "function": row["address"],
                    "status": "no-direct-upstream-caller-in-export",
                    "note": (
                        "Direct callgraph evidence does not identify this caller's owner. "
                        "Indirect dispatch, callback tables, or an external entry remain possible."
                    ),
                }
            )

    observed = set(caller_addresses) | set(upstream_distance)
    for address in sorted(observed, key=lambda value: int(value, 0)):
        for edge in indirect.get(address, []):
            blocker_rows.append(
                {
                    "function": address,
                    "instruction": edge.get("instruction"),
                    "status": "unresolved-indirect-call-target",
                }
            )

    target_rows: list[dict[str, Any]] = []
    for row in caller_rows:
        if row.get("thunk") is True:
            continue
        target_rows.append(
            {
                "address": row["address"],
                "name": row["name"],
                "priority": 0,
                "reason": "direct caller of proven FUN_00770e80 outer-update anchor",
                "promoted": False,
            }
        )
    for row in upstream_rows:
        if not row["function_metadata_present"] or row.get("external") is True or row.get("thunk") is True:
            continue
        target_rows.append(
            {
                "address": row["address"],
                "name": row["name"],
                "priority": row["upstream_depth"],
                "reason": f"direct upstream caller depth {row['upstream_depth']} above FUN_00770e80 caller frontier",
                "promoted": False,
            }
        )

    deduped_targets: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in sorted(target_rows, key=lambda row: (row["priority"], int(row["address"], 0))):
        if row["address"] in seen:
            continue
        seen.add(row["address"])
        deduped_targets.append(row)
    deduped_targets = deduped_targets[:max_targets]

    return {
        "format": FORMAT,
        "ghidra_export": str(root),
        "source": {
            "program": binary.get("program_name"),
            "executable_md5": binary.get("executable_md5"),
            "language_id": binary.get("language_id"),
            "image_base": binary.get("image_base"),
            "pointer_size": binary.get("pointer_size"),
        },
        "outer_update_anchor": OUTER_UPDATE,
        "direct_caller_count": len(caller_rows),
        "direct_callers": caller_rows,
        "shared_ordered_direct_callee_prefix_count": len(shared_prefix_rows),
        "shared_ordered_direct_callee_prefix": shared_prefix_rows,
        "all_callers_invoke_outer_update_at_same_direct_call_index": len(
            {row["outer_update_call_index"] for row in caller_rows}
        ) == 1,
        "upstream_depth": upstream_depth,
        "upstream_candidate_count": len(upstream_rows),
        "upstream_candidates": upstream_rows,
        "blocker_count": len(blocker_rows),
        "blockers": blocker_rows,
        "instruction_export_target_count": len(deduped_targets),
        "instruction_export_targets": deduped_targets,
        "instruction_export_addresses": [row["address"] for row in deduped_targets],
        "scope": {
            "outer_update_semantics_imported_from_existing_contract": True,
            "direct_calls_only_for_ownership_frontier": True,
            "shared_call_prefix_is_semantic_identity": False,
            "direct_caller_is_vehicle_owner_proof": False,
            "direct_caller_is_rendered_frame_scheduler_proof": False,
            "missing_direct_incoming_edge_is_root_proof": False,
            "input_control_ownership_proven": False,
            "computed_jump_targets_are_dispatch_ownership_proof": False,
            "automatic_function_renaming_performed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("--upstream-depth", type=int, default=2)
    parser.add_argument("--max-targets", type=int, default=32)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--targets-out", type=Path)
    parser.add_argument("--fail-on-ownership-blocker", action="store_true")
    args = parser.parse_args()

    report = build_vehicle_outer_update_caller_frontier(
        args.ghidra_export,
        upstream_depth=args.upstream_depth,
        max_targets=args.max_targets,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    if args.targets_out:
        args.targets_out.parent.mkdir(parents=True, exist_ok=True)
        args.targets_out.write_text(
            "".join(address + "\n" for address in report["instruction_export_addresses"]),
            encoding="utf-8",
        )

    print(f"format: {report['format']}")
    print(f"direct callers: {report['direct_caller_count']}")
    print(
        "shared direct-callee prefix: "
        f"{report['shared_ordered_direct_callee_prefix_count']}"
    )
    print(f"upstream candidates: {report['upstream_candidate_count']}")
    print(f"ownership/control-flow blockers: {report['blocker_count']}")
    print(f"instruction-export targets: {report['instruction_export_target_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    if args.targets_out:
        print(f"targets: {args.targets_out}")

    if args.fail_on_ownership_blocker and report["blocker_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
