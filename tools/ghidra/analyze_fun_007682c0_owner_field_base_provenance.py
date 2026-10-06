#!/usr/bin/env python3
"""Prove the base provenance of a +0x339c FUN_007682c0 receiver candidate.

This is a second-stage consumer of
SHIFT.Fun007682c0AccumulatorDestinationReceiverProvenance/1.  The first-stage
register engine intentionally records a memory load as an opaque physical origin
such as ``memory:[esi+0x339c]``.  That is sufficient to identify a candidate
BODY-owner field displacement, but it is not sufficient to join the load to the
proven global vehicle base.

This pass closes exactly that physical gap.  For each of the two outer
FUN_00770e80 -> FUN_0076d100 callsites it enumerates every reachable simple MOV
load of ``[base+0x339c]`` on a path to the call and proves the base register's
all-path origin at the load.  A positive result requires every such candidate
base to be exactly ``entry:ECX``.  The positive global-vehicle/BODY-owner
identity contract then permits the narrow statement that the downstream
FUN_007682c0 receiver is the pointer loaded from global vehicle +0x339c.

That still does *not* prove that this owner pointer is the selected BMW BODY0
record.  The typed Phase 696 delta consumer therefore remains external until a
separate owner-pointer -> exact destination-record join is source-backed.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import analyze_fun_00765470_body_owner_receiver as _reg
import analyze_fun_007682c0_destination_receiver_provenance as _receiver

FORMAT = "SHIFT.Fun007682c0OwnerFieldBaseProvenance/1"
UPSTREAM_FORMAT = _receiver.FORMAT
OWNER_OFFSET = _receiver.BODY_OWNER_FIELD_OFFSET
OUTER_FUNCTION = "0x00770e80"
PASS_LINK_IDS = (
    "outer-update-to-physics-pass-0",
    "outer-update-to-physics-pass-1",
)

_SIMPLE_OWNER_FIELD_RE = re.compile(
    r"^(?:byte\s+ptr\s+|word\s+ptr\s+|dword\s+ptr\s+|qword\s+ptr\s+)?"
    r"\[\s*(EAX|EBX|ECX|EDX|ESI|EDI|EBP|ESP)\s*\+\s*0x339c\s*\]$",
    re.IGNORECASE,
)


def _address(value: Any) -> str:
    return _reg._normalize_address(value)


def _owner_field_base_register(operand: Any) -> str | None:
    if not isinstance(operand, str):
        return None
    match = _SIMPLE_OWNER_FIELD_RE.fullmatch(operand.strip())
    return None if match is None else match.group(1).upper()


def _reverse_reachable_to(
    instructions: list[dict[str, Any]], target: str
) -> set[str]:
    by_address = {_address(row["address"]): row for row in instructions}
    address_set = set(by_address)
    reverse: dict[str, set[str]] = defaultdict(set)
    for address, instruction in by_address.items():
        for successor in _reg._successors(instruction, address_set):
            reverse[successor].add(address)

    result = {target}
    queue: deque[str] = deque((target,))
    while queue:
        current = queue.popleft()
        for predecessor in reverse.get(current, ()):
            if predecessor in result:
                continue
            result.add(predecessor)
            queue.append(predecessor)
    return result


def _candidate_owner_loads_for_call(
    instructions: list[dict[str, Any]],
    incoming: dict[str, Any],
    callsite: str,
) -> list[dict[str, Any]]:
    can_reach_call = _reverse_reachable_to(instructions, callsite)
    candidates: list[dict[str, Any]] = []
    for instruction in instructions:
        address = _address(instruction.get("address"))
        if address == callsite or address not in incoming or address not in can_reach_call:
            continue
        if str(instruction.get("mnemonic") or "").upper() != "MOV":
            continue
        operands = instruction.get("operands")
        if not isinstance(operands, list) or len(operands) < 2:
            continue
        destination = _reg._register(operands[0])
        base = _owner_field_base_register(operands[1])
        if destination not in _reg._TRACKED or base not in _reg._TRACKED:
            continue
        base_origins = _reg._sorted_origins(incoming[address][base])
        candidates.append(
            {
                "instruction": address,
                "text": instruction.get("text"),
                "destination_register": destination,
                "base_register": base,
                "base_origins_before_load": base_origins,
                "base_is_outer_entry_ECX": base_origins == ["entry:ECX"],
            }
        )
    candidates.sort(key=lambda row: int(row["instruction"], 0))
    return candidates


def analyze_fun_007682c0_owner_field_base_provenance(
    ghidra_export: Path,
    instruction_export: Path,
    global_identity_path: Path,
) -> dict[str, Any]:
    upstream = _receiver.analyze_fun_007682c0_destination_receiver_provenance(
        ghidra_export,
        instruction_export,
        global_identity_path,
    )
    instruction_rows = _receiver._callsite_engine._index_instruction_rows(
        instruction_export
    )
    outer_instructions = instruction_rows.get(OUTER_FUNCTION)
    if outer_instructions is None:
        raise ValueError(f"instruction export missing required function {OUTER_FUNCTION}")
    incoming, iterations = _receiver._callsite_engine._analyze_incoming_states(
        outer_instructions
    )

    links = {
        str(row.get("id")): row
        for row in upstream.get("receiver_links", [])
        if isinstance(row, dict)
    }
    pass_reports: list[dict[str, Any]] = []
    for link_id in PASS_LINK_IDS:
        link = links.get(link_id)
        if link is None:
            raise ValueError(f"upstream receiver report missing {link_id}")
        callsite = str(link["callsite"])
        origins = list(link.get("receiver_origins_before_call") or [])
        owner_field_origin = (
            len(origins) == 1 and _receiver._mentions_owner_field(origins[0])
        )
        candidates = _candidate_owner_loads_for_call(
            outer_instructions,
            incoming,
            callsite,
        )
        all_candidate_bases_are_entry_ecx = bool(candidates) and all(
            row["base_is_outer_entry_ECX"] is True for row in candidates
        )
        pass_reports.append(
            {
                "id": link_id,
                "callsite": callsite,
                "receiver_origins_before_call": origins,
                "owner_field_origin_observed": owner_field_origin,
                "owner_field_load_candidates_on_paths_to_call": candidates,
                "candidate_count": len(candidates),
                "all_candidate_load_bases_are_outer_entry_ECX": (
                    all_candidate_bases_are_entry_ecx
                ),
                "owner_field_base_to_outer_entry_ECX_proven": (
                    owner_field_origin and all_candidate_bases_are_entry_ecx
                ),
            }
        )

    both_pass_bases_proven = all(
        row["owner_field_base_to_outer_entry_ECX_proven"] is True
        for row in pass_reports
    )
    analysis = upstream.get("analysis")
    if not isinstance(analysis, dict):
        raise ValueError("upstream receiver analysis missing")
    downstream_entry_continuity = (
        analysis.get("physics_pass_to_tail_entry_ECX_continuity_proven") is True
        and analysis.get("tail_to_FUN_007682c0_entry_ECX_continuity_proven") is True
    )
    effect_receiver_is_global_owner_pointer = (
        both_pass_bases_proven and downstream_entry_continuity
    )

    blockers: list[dict[str, Any]] = []
    if not both_pass_bases_proven:
        blockers.append(
            {
                "id": "owner-field-base-to-outer-entry-unproven",
                "evidence_state": "unknown",
                "required_evidence": (
                    "for both outer physics-pass callsites, prove every reachable "
                    "simple +0x339c load that can reach the call uses a base register "
                    "whose all-path origin is FUN_00770e80 entry ECX"
                ),
            }
        )
    if both_pass_bases_proven and not downstream_entry_continuity:
        blockers.append(
            {
                "id": "owner-pointer-through-tail-continuity-unproven",
                "evidence_state": "unknown",
                "required_evidence": (
                    "preserve the proven global+0x339c pointer through the exact "
                    "FUN_0076d100 -> FUN_00769ef0 -> FUN_007682c0 receiver chain"
                ),
            }
        )
    if effect_receiver_is_global_owner_pointer:
        blockers.append(
            {
                "id": "owner-pointer-to-exact-delta-destination-record-unproven",
                "evidence_state": "unknown",
                "required_evidence": (
                    "join the proven global vehicle +0x339c BODY-array owner pointer "
                    "to the exact record receiving FUN_007682c0 +0x50; do not equate "
                    "the owner pointer with BMW BODY0 solely because BODY index 0 is selected"
                ),
            }
        )

    return {
        "format": FORMAT,
        "version": 1,
        "status": (
            "owner-field-pointer-proven-record-join-blocked"
            if effect_receiver_is_global_owner_pointer
            else "blocked"
        ),
        "ready": effect_receiver_is_global_owner_pointer,
        "inputs": {
            "upstream_receiver_format": UPSTREAM_FORMAT,
            "ghidra_export": str(ghidra_export),
            "instruction_export": str(instruction_export),
            "global_vehicle_BODY_owner_identity": str(global_identity_path),
        },
        "outer_function": OUTER_FUNCTION,
        "owner_field_offset": OWNER_OFFSET,
        "fixed_point_iterations": iterations,
        "pass_owner_field_base_provenance": pass_reports,
        "analysis": {
            "both_outer_pass_owner_field_bases_are_entry_ECX": both_pass_bases_proven,
            "outer_entry_is_proven_global_vehicle_base": (
                analysis.get("outer_entry_is_proven_global_vehicle_base") is True
            ),
            "downstream_entry_ECX_continuity_proven": downstream_entry_continuity,
            "FUN_007682c0_receiver_is_global_vehicle_plus_0x339c_pointer": (
                effect_receiver_is_global_owner_pointer
            ),
            "FUN_007682c0_receiver_is_retail_BMW_BODY0": False,
            "owner_pointer_to_exact_delta_destination_record_join_proven": False,
        },
        "blocking_reasons": blockers,
        "handoff": {
            "FUN_007682c0_owner_field_base_provenance_ready": both_pass_bases_proven,
            "FUN_007682c0_owner_pointer_receiver_ready": effect_receiver_is_global_owner_pointer,
            "FUN_007682c0_delta_consumer_internalization_ready": False,
            "phase696_typed_delta_consumer_must_remain_external": True,
        },
        "scope": {
            "memory_displacement_alone_used_as_identity": False,
            "base_register_origin_proven_on_all_candidate_loads": both_pass_bases_proven,
            "BODY_owner_pointer_relabelled_as_BODY0": False,
            "provider_semantics_promoted": False,
            "runtime_capture_used": False,
            "original_game_executed": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("global_vehicle_body_owner_identity", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    try:
        report = analyze_fun_007682c0_owner_field_base_provenance(
            args.ghidra_export,
            args.instruction_export,
            args.global_vehicle_body_owner_identity,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
