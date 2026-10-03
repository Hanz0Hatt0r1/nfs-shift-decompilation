#!/usr/bin/env python3
"""Recover a fail-closed BODY/vehicle update schedule from direct Ghidra calls.

This tool narrows the broad subsystem frontier to the already proven Process B
BODY/vehicle anchors. It preserves only direct-call ordering and uses those
anchors to recover two anonymous orchestration candidates:

* the helper repeated between the two FUN_0076d100 passes which directly calls
  FUN_007b3f40 and FUN_007b4110;
* the FUN_0076d100 tail helper which directly calls FUN_007675f0 and
  FUN_007682c0 in that order.

Neither recovered function is semantically renamed. The report is target
selection and ordering evidence only; BODY pointer provenance and pose/motion
writers remain unresolved until targeted instruction/p-code evidence closes
those boundaries.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

FORMAT = "SHIFT.GhidraBodyUpdateScheduleFrontier/1"

# These are already source/machine-code-backed anchors in the Process B BODY
# persistent-state contract. Keeping the anonymous bridge/tail OUT of this map
# is intentional: the tool must recover them from callgraph structure.
ANCHORS = {
    "outer_update": "0x00770e80",
    "physics_pass": "0x0076d100",
    "wheel_shared_triplet_pass": "0x00763570",
    "wheel_shared_triplet_writer": "0x00755f80",
    "wheel_update": "0x00758b50",
    "contact_factor": "0x00765c40",
    "contact_response": "0x00766510",
    "contact_outer": "0x007675f0",
    "motion_read_gate": "0x007682c0",
    "sdf_solve": "0x007b3f40",
    "post_solve_writer": "0x007b4110",
}


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


def _single_direct_call(
    rows: list[dict[str, Any]], parent: str, target: str
) -> dict[str, Any]:
    matches = [row for row in rows if row.get("to") == target]
    if len(matches) != 1:
        raise ValueError(
            f"{parent}: expected exactly one direct call to {target}; found {len(matches)}"
        )
    return matches[0]


def _require_order(parent: str, rows: list[dict[str, Any]]) -> None:
    keys = [_address_key(row.get("instruction")) for row in rows]
    if keys != sorted(keys):
        raise ValueError(f"{parent}: required direct-call order is not preserved")


def build_body_update_schedule_frontier(root: Path) -> dict[str, Any]:
    required = ("binary.json", "functions.jsonl", "callgraph.jsonl")
    missing_files = [name for name in required if not (root / name).is_file()]
    if missing_files:
        raise FileNotFoundError(
            "missing required Ghidra files: " + ", ".join(missing_files)
        )

    binary = json.loads((root / "binary.json").read_text(encoding="utf-8"))
    functions = {
        row["address"]: row
        for row in read_jsonl(root / "functions.jsonl")
        if isinstance(row.get("address"), str)
    }

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
        rows.sort(key=lambda row: _address_key(row.get("instruction")))

    missing_anchors = [
        (name, address)
        for name, address in ANCHORS.items()
        if address not in functions
    ]
    if missing_anchors:
        raise ValueError(
            "required anchor function(s) absent: "
            + ", ".join(f"{name}={address}" for name, address in missing_anchors)
        )

    outer = ANCHORS["outer_update"]
    physics_pass = ANCHORS["physics_pass"]
    outer_rows = outgoing[outer]
    pass_calls = [row for row in outer_rows if row.get("to") == physics_pass]
    if len(pass_calls) != 2:
        raise ValueError(
            f"{outer} must contain exactly two direct calls to {physics_pass}; "
            f"found {len(pass_calls)}"
        )

    pass_indices = [outer_rows.index(row) for row in pass_calls]
    if pass_indices[0] >= pass_indices[1]:
        raise ValueError("physics-pass call order is not strictly increasing")

    first_between_pass_window = outer_rows[pass_indices[0] + 1 : pass_indices[1]]
    after_second_pass_window = outer_rows[pass_indices[1] + 1 :]
    repeated_targets = sorted(
        {row["to"] for row in first_between_pass_window}
        & {row["to"] for row in after_second_pass_window}
    )

    sdf_solve = ANCHORS["sdf_solve"]
    post_solve_writer = ANCHORS["post_solve_writer"]
    bridge_candidates = []
    for target in repeated_targets:
        callees = {row["to"] for row in outgoing.get(target, [])}
        if {sdf_solve, post_solve_writer}.issubset(callees):
            bridge_candidates.append(target)
    if len(bridge_candidates) != 1:
        raise ValueError(
            "expected exactly one repeated between-pass callee that directly calls "
            "both SDF solve and post-solve writer; found " + str(bridge_candidates)
        )
    between_pass_bridge = bridge_candidates[0]

    bridge_rows = outgoing[between_pass_bridge]
    bridge_required = [
        _single_direct_call(
            bridge_rows,
            between_pass_bridge,
            ANCHORS["wheel_shared_triplet_pass"],
        ),
        _single_direct_call(bridge_rows, between_pass_bridge, sdf_solve),
        _single_direct_call(bridge_rows, between_pass_bridge, post_solve_writer),
    ]
    _require_order(between_pass_bridge, bridge_required)

    pass_rows = outgoing[physics_pass]
    tail_candidates = []
    for row in pass_rows:
        target = row["to"]
        callees = {edge["to"] for edge in outgoing.get(target, [])}
        if {
            ANCHORS["contact_outer"],
            ANCHORS["motion_read_gate"],
        }.issubset(callees):
            tail_candidates.append(target)
    tail_candidates = sorted(set(tail_candidates))
    if len(tail_candidates) != 1:
        raise ValueError(
            "expected exactly one physics-pass callee that directly calls contact_outer "
            "and motion_read_gate; found " + str(tail_candidates)
        )
    physics_pass_tail = tail_candidates[0]

    pass_required = [
        _single_direct_call(pass_rows, physics_pass, ANCHORS["contact_factor"]),
        _single_direct_call(pass_rows, physics_pass, ANCHORS["wheel_update"]),
        _single_direct_call(pass_rows, physics_pass, ANCHORS["contact_response"]),
        _single_direct_call(pass_rows, physics_pass, physics_pass_tail),
    ]
    _require_order(physics_pass, pass_required)

    tail_rows = outgoing[physics_pass_tail]
    tail_required = [
        _single_direct_call(
            tail_rows, physics_pass_tail, ANCHORS["contact_outer"]
        ),
        _single_direct_call(
            tail_rows, physics_pass_tail, ANCHORS["motion_read_gate"]
        ),
    ]
    _require_order(physics_pass_tail, tail_required)

    repeated_rows = []
    for target in repeated_targets:
        target_rows = outgoing.get(target, [])
        repeated_rows.append(
            {
                "address": target,
                "name": (functions.get(target) or {}).get("name"),
                "calls_sdf_solve": any(
                    row.get("to") == sdf_solve for row in target_rows
                ),
                "calls_post_solve_writer": any(
                    row.get("to") == post_solve_writer for row in target_rows
                ),
                "selected_between_pass_bridge": target == between_pass_bridge,
            }
        )

    target_rows: list[dict[str, Any]] = []
    seen_targets: set[str] = set()

    def add_target(address: str, reason: str, parent: str | None = None) -> None:
        if address in seen_targets:
            return
        metadata = functions.get(address)
        if not metadata:
            return
        if metadata.get("external") is True or metadata.get("thunk") is True:
            return
        seen_targets.add(address)
        target_rows.append(
            {
                "address": address,
                "name": metadata.get("name"),
                "size": metadata.get("size"),
                "direct_incoming_count": len(incoming.get(address, [])),
                "direct_outgoing_count": len(outgoing.get(address, [])),
                "parent_context": parent,
                "reason": reason,
                "promoted": False,
            }
        )

    add_target(
        between_pass_bridge,
        "uniquely recovered repeated between-pass bridge",
        outer,
    )
    add_target(
        physics_pass_tail,
        "uniquely recovered physics-pass tail containing contact_outer -> motion_read_gate",
        physics_pass,
    )

    semantic_addresses = set(ANCHORS.values()) | {
        between_pass_bridge,
        physics_pass_tail,
    }
    for row in first_between_pass_window:
        target = row["to"]
        if target not in semantic_addresses:
            add_target(
                target,
                "repeated/adjacent outer-update helper between proven physics passes",
                outer,
            )

    for parent, rows in (
        (physics_pass, pass_rows),
        (between_pass_bridge, bridge_rows),
        (physics_pass_tail, tail_rows),
    ):
        for row in rows:
            target = row["to"]
            if target in semantic_addresses:
                continue
            # High-fan-in functions are usually generic support/runtime helpers. They
            # stay in the complete ordered call list but are not auto-selected for
            # the next targeted instruction export.
            if len(incoming.get(target, [])) > 4:
                continue
            add_target(
                target,
                "low-fan-in direct helper adjacent to recovered BODY update schedule",
                parent,
            )

    target_rows = target_rows[:32]

    blockers = []
    observed_for_indirect = sorted(
        set(ANCHORS.values()) | {between_pass_bridge, physics_pass_tail}
    )
    for function in observed_for_indirect:
        for row in indirect.get(function, []):
            blockers.append(
                {
                    "from_function": function,
                    "instruction": row.get("instruction"),
                    "status": "unresolved-indirect-call-target",
                    "promoted": False,
                }
            )
    blockers.sort(
        key=lambda row: (
            row["from_function"],
            _address_key(row.get("instruction")),
        )
    )

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
        "anchors": ANCHORS,
        "recovered": {
            "between_pass_bridge": {
                "address": between_pass_bridge,
                "name": functions[between_pass_bridge].get("name"),
                "status": (
                    "repeated-between-two-physics-passes-and-calls-"
                    "sdf-solve-plus-post-solve-writer"
                ),
                "promoted": False,
            },
            "physics_pass_tail": {
                "address": physics_pass_tail,
                "name": functions[physics_pass_tail].get("name"),
                "status": (
                    "physics-pass-callee-calling-contact-outer-then-motion-read-gate"
                ),
                "promoted": False,
            },
        },
        "outer_update": {
            "function": outer,
            "ordered_direct_calls": [_edge(row) for row in outer_rows],
            "physics_pass_calls": [_edge(row) for row in pass_calls],
            "repeated_between_or_after_pass_targets": repeated_rows,
        },
        "between_pass_bridge": {
            "function": between_pass_bridge,
            "ordered_direct_calls": [_edge(row) for row in bridge_rows],
            "required_order": [_edge(row) for row in bridge_required],
        },
        "physics_pass": {
            "function": physics_pass,
            "ordered_direct_calls": [_edge(row) for row in pass_rows],
            "required_order": [_edge(row) for row in pass_required],
        },
        "physics_pass_tail": {
            "function": physics_pass_tail,
            "ordered_direct_calls": [_edge(row) for row in tail_rows],
            "required_order": [_edge(row) for row in tail_required],
        },
        "indirect_blocker_count": len(blockers),
        "indirect_blockers": blockers,
        "instruction_export_targets": target_rows,
        "instruction_export_addresses": [row["address"] for row in target_rows],
        "scope": {
            "direct_call_order_proven": True,
            "between_pass_bridge_semantics_proven": False,
            "physics_pass_tail_semantics_proven": False,
            "pose_integration_writer_proven": False,
            "motion_triplet_writer_proven": False,
            "object_pointer_provenance_from_callgraph": False,
            "automatic_function_renaming_performed": False,
            "note": (
                "The report proves only direct-call ordering around already proven "
                "BODY/vehicle anchors. Recovered anonymous helpers remain instruction-"
                "export targets until pointer provenance and STORE/LOAD evidence close "
                "their object/state semantics."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument(
        "--targets-out",
        type=Path,
        help="write prioritized targeted instruction-export addresses",
    )
    args = parser.parse_args()

    report = build_body_update_schedule_frontier(args.ghidra_export)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    if args.targets_out:
        args.targets_out.parent.mkdir(parents=True, exist_ok=True)
        args.targets_out.write_text(
            "".join(
                address + "\n" for address in report["instruction_export_addresses"]
            ),
            encoding="utf-8",
        )

    print(f"format: {report['format']}")
    print(
        "between-pass bridge: "
        + report["recovered"]["between_pass_bridge"]["address"]
    )
    print(
        "physics-pass tail: "
        + report["recovered"]["physics_pass_tail"]["address"]
    )
    print(
        "instruction-export targets: "
        + str(len(report["instruction_export_addresses"]))
    )
    if args.json_out:
        print(f"output: {args.json_out}")
    if args.targets_out:
        print(f"targets: {args.targets_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
