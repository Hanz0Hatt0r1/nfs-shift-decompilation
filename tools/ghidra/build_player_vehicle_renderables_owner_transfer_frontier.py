#!/usr/bin/env python3
"""Build the first physical transfer frontier for mPlayerVehicleRenderables.

The input runtime-alias proof establishes only that a value loaded from the
candidate render-manager global is used as the base of a +0xca4 field access.
This pass starts at each proven *read* of that field, gives the loaded pointer a
unique taint token, and follows that exact value through the bounded selected
function with the existing all-path IA-32 register-provenance engine.

Only physical first-hop sinks are emitted: direct ECX/EDX call transfers,
simple dereferences, memory stores, stack pushes and return values.  No sink is
promoted to semantic owner, RenderHierarchy, VHF or frame identity.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import deque
from pathlib import Path
from typing import Any, Mapping

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import analyze_player_vehicle_renderables_runtime_alias as _alias
import analyze_register_relative_accesses as _accesses

FORMAT = "SHIFT.PlayerVehicleRenderablesOwnerTransferFrontier/1"
ALIAS_FORMAT = _alias.FORMAT
RANK_FORMAT = _alias.ROOT_POSE_RANK_FORMAT
INSTRUCTION_FORMAT = _alias.INSTRUCTION_FORMAT
PROGRAM = _alias.PROGRAM
PE_MD5 = _alias.PE_MD5
FIELD_OFFSET = _alias.FIELD_OFFSET
DEFAULT_MAX_DIRECT_TARGETS = 32
_TRACKED = tuple(_alias._register_engine._TRACKED)
_DIRECT_TARGET_RE = re.compile(r"^(?:0x|FUN_)?([0-9A-Fa-f]{6,8})$")


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _register(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip().upper()
    return token if token in _TRACKED else None


def _single_marker(values: Any, marker: str) -> bool:
    return isinstance(values, frozenset) and values == frozenset((marker,))


def _validate_alias(path: Path) -> dict[str, Any]:
    report = _load_json(path)
    if report.get("format") != ALIAS_FORMAT or report.get("ready") is not True:
        raise ValueError(f"{path}: expected ready {ALIAS_FORMAT}")
    retail = report.get("retail")
    if not isinstance(retail, Mapping):
        raise ValueError("runtime-alias retail identity missing")
    if retail.get("program") != PROGRAM or str(retail.get("md5") or "").lower() != PE_MD5:
        raise ValueError("runtime-alias retail identity drift")

    input_rank = report.get("input_rank")
    if not isinstance(input_rank, Mapping):
        raise ValueError("runtime-alias input_rank provenance missing")
    if input_rank.get("format") != RANK_FORMAT or input_rank.get("root_pose_aware_rank") is not True:
        raise ValueError("runtime-alias proof is not rooted in the current root-pose-aware rank")

    handoff = report.get("handoff")
    if not isinstance(handoff, Mapping):
        raise ValueError("runtime-alias handoff missing")
    for gate in (
        "candidate_global_to_ca4_runtime_field_base_alias_ready",
        "player_vehicle_renderables_field_runtime_access_ready",
    ):
        if handoff.get(gate) is not True:
            raise ValueError(f"runtime-alias prerequisite gate is not ready: {gate}")

    candidate = report.get("candidate_global")
    if not isinstance(candidate, Mapping):
        raise ValueError("runtime-alias candidate_global missing")
    _alias._addr(candidate.get("address"), field="runtime-alias candidate_global.address")

    analysis = report.get("analysis")
    if not isinstance(analysis, Mapping):
        raise ValueError("runtime-alias analysis missing")
    accesses = analysis.get("field_accesses")
    if not isinstance(accesses, list):
        raise ValueError("runtime-alias field_accesses missing")
    positive = [
        item
        for item in accesses
        if isinstance(item, Mapping)
        and item.get("exact_single_candidate_global_value_as_field_base") is True
    ]
    if not positive:
        raise ValueError("runtime-alias contains no exact positive +0xca4 access")
    return report


def _direct_call_target(instruction: Mapping[str, Any]) -> str | None:
    if str(instruction.get("mnemonic") or "").upper() != "CALL":
        return None
    operands = instruction.get("operands")
    if not isinstance(operands, list) or len(operands) != 1 or not isinstance(operands[0], str):
        return None
    token = operands[0].strip()
    match = _DIRECT_TARGET_RE.fullmatch(token)
    if match is None:
        return None
    operand_target = f"0x{int(match.group(1), 16):08x}"

    flows = instruction.get("flows")
    if not isinstance(flows, list):
        raise ValueError(f"{instruction.get('address')}: flows must be a list")
    normalized_flows: list[str] = []
    for raw in flows:
        if not isinstance(raw, str):
            continue
        try:
            normalized_flows.append(_alias._addr(raw, field="call flow"))
        except ValueError:
            continue
    if normalized_flows and operand_target not in normalized_flows:
        return None
    return operand_target


def _pcode_memory_kinds(instruction: Mapping[str, Any]) -> set[str]:
    address = str(instruction.get("address") or "<unknown>")
    pcode = _accesses._validate_pcode(instruction.get("pcode"), address)
    return _accesses._pcode_memory_kinds(pcode)


def _alias_seed(
    alias_item: Mapping[str, Any],
    row: Mapping[str, Any],
    incoming_states: Mapping[str, Any],
) -> tuple[str, str, dict[str, Any], str, dict[str, frozenset[str]]] | None:
    function = _alias._addr(alias_item.get("function"), field="alias.function")
    instruction_address = _alias._addr(alias_item.get("instruction"), field="alias.instruction")
    instructions = row.get("instructions")
    if not isinstance(instructions, list):
        raise ValueError(f"{function}: instructions missing")
    by_address = {
        _alias._addr(item.get("address"), field="instruction.address"): item
        for item in instructions
        if isinstance(item, dict)
    }
    instruction = by_address.get(instruction_address)
    if instruction is None:
        raise ValueError(f"{function}:{instruction_address}: positive alias instruction missing")

    if alias_item.get("access") not in {"read", "read-write"}:
        return None
    mnemonic = str(instruction.get("mnemonic") or "").upper()
    operands = instruction.get("operands")
    if mnemonic != "MOV" or not isinstance(operands, list) or len(operands) < 2:
        return None
    destination = _register(operands[0])
    if destination is None:
        return None
    parsed_source = _accesses._parse_memory_operand(str(operands[1]))
    expected_base = str(alias_item.get("base_register") or "").upper()
    if parsed_source != (expected_base, FIELD_OFFSET):
        return None

    before = incoming_states.get(instruction_address)
    if not isinstance(before, dict):
        raise ValueError(f"{function}:{instruction_address}: positive alias instruction unreachable")
    after = _alias._register_engine._transfer(instruction, before)
    origins = _alias._register_engine._sorted_origins(after[destination])
    if len(origins) != 1 or not origins[0].startswith("memory:"):
        return None

    marker = f"alias-field-value:{function}@{instruction_address}:+0xca4"
    seeded = dict(after)
    seeded[destination] = frozenset((marker,))
    return function, instruction_address, instruction, marker, seeded


def _record_sinks(
    function: str,
    marker: str,
    instruction: Mapping[str, Any],
    state: Mapping[str, frozenset[str]],
) -> list[dict[str, Any]]:
    address = _alias._addr(instruction.get("address"), field="sink.instruction")
    mnemonic = str(instruction.get("mnemonic") or "").upper()
    operands = instruction.get("operands")
    if not isinstance(operands, list) or any(not isinstance(value, str) for value in operands):
        raise ValueError(f"{function}:{address}: operands must be strings")

    sinks: list[dict[str, Any]] = []
    call_target = _direct_call_target(instruction)
    if call_target is not None:
        for register, position in (("ECX", "register-arg-ecx"), ("EDX", "register-arg-edx")):
            if _single_marker(state[register], marker):
                sinks.append(
                    {
                        "kind": "direct-call-register-transfer",
                        "function": function,
                        "instruction": address,
                        "instruction_text": instruction.get("text"),
                        "source_register": register,
                        "register_position": position,
                        "direct_target": call_target,
                        "callee_semantic_owner_identity_proven": False,
                        "callee_abi_role_proven_by_this_artifact": False,
                    }
                )

    pcode_kinds = _pcode_memory_kinds(instruction)
    for index, operand in enumerate(operands):
        parsed = _accesses._parse_memory_operand(operand)
        if parsed is None:
            continue
        base_register, displacement = parsed
        if base_register in state and _single_marker(state[base_register], marker) and pcode_kinds:
            sinks.append(
                {
                    "kind": "pointer-dereference",
                    "function": function,
                    "instruction": address,
                    "instruction_text": instruction.get("text"),
                    "base_register": base_register,
                    "operand_index": index,
                    "operand": operand,
                    "displacement": displacement,
                    "displacement_hex": _accesses._format_displacement(displacement),
                    "pcode_memory_ops": sorted(pcode_kinds),
                    "field_semantics_proven": False,
                }
            )

    if "STORE" in pcode_kinds and mnemonic == "MOV" and len(operands) >= 2:
        source_register = _register(operands[1])
        if source_register is not None and _single_marker(state[source_register], marker):
            destination_operand = operands[0]
            if "[" in destination_operand and "]" in destination_operand:
                parsed_destination = _accesses._parse_memory_operand(destination_operand)
                sink: dict[str, Any] = {
                    "kind": "memory-store",
                    "function": function,
                    "instruction": address,
                    "instruction_text": instruction.get("text"),
                    "source_register": source_register,
                    "destination_operand": destination_operand,
                    "destination_object_identity_proven": False,
                }
                if parsed_destination is not None:
                    sink.update(
                        {
                            "destination_base_register": parsed_destination[0],
                            "destination_displacement": parsed_destination[1],
                            "destination_displacement_hex": _accesses._format_displacement(
                                parsed_destination[1]
                            ),
                        }
                    )
                sinks.append(sink)

    if mnemonic == "PUSH" and operands:
        source_register = _register(operands[0])
        if source_register is not None and _single_marker(state[source_register], marker):
            sinks.append(
                {
                    "kind": "stack-push",
                    "function": function,
                    "instruction": address,
                    "instruction_text": instruction.get("text"),
                    "source_register": source_register,
                    "stack_argument_ordinal_proven": False,
                    "receiving_callee_proven": False,
                }
            )

    if mnemonic in {"RET", "RETF"} and _single_marker(state["EAX"], marker):
        sinks.append(
            {
                "kind": "return-value",
                "function": function,
                "instruction": address,
                "instruction_text": instruction.get("text"),
                "source_register": "EAX",
                "caller_identity_proven": False,
            }
        )
    return sinks


def _trace_seed(
    row: Mapping[str, Any],
    seed_address: str,
    marker: str,
    seeded_after: dict[str, frozenset[str]],
) -> list[dict[str, Any]]:
    instructions = row.get("instructions")
    if not isinstance(instructions, list) or not instructions:
        raise ValueError("instruction row is empty")
    by_address = {
        _alias._addr(item.get("address"), field="instruction.address"): item
        for item in instructions
        if isinstance(item, dict)
    }
    address_set = set(by_address)
    seed_instruction = by_address[seed_address]
    incoming: dict[str, dict[str, frozenset[str]]] = {}
    queue: deque[str] = deque()
    for successor in _alias._register_engine._successors(seed_instruction, address_set):
        merged, changed = _alias._register_engine._merge(incoming.get(successor), seeded_after)
        if changed:
            incoming[successor] = merged
            queue.append(successor)

    function = _alias._addr((row.get("function") or {}).get("address"), field="function.address")
    sinks: list[dict[str, Any]] = []
    iterations = 0
    max_iterations = max(64, len(instructions) * 64)
    while queue:
        address = queue.popleft()
        iterations += 1
        if iterations > max_iterations:
            raise ValueError(f"{function}:{seed_address}: taint provenance did not converge")
        state = incoming[address]
        instruction = by_address[address]
        for sink in _record_sinks(function, marker, instruction, state):
            sinks.append(sink)
        after = _alias._register_engine._transfer(instruction, state)
        for successor in _alias._register_engine._successors(instruction, address_set):
            # Re-entering the seed instruction would reload the field.  Stop that
            # loop edge rather than pretending the original loaded value survived
            # another memory read.
            if successor == seed_address:
                continue
            merged, changed = _alias._register_engine._merge(incoming.get(successor), after)
            if changed:
                incoming[successor] = merged
                queue.append(successor)
    return sinks


def build_frontier(
    runtime_alias_path: Path,
    rank_path: Path,
    instruction_export: Path,
    *,
    max_direct_targets: int = DEFAULT_MAX_DIRECT_TARGETS,
) -> dict[str, Any]:
    if max_direct_targets <= 0:
        raise ValueError("max_direct_targets must be positive")
    runtime_alias = _validate_alias(runtime_alias_path)
    rank, global_address, selected = _alias._load_rank(rank_path)
    if rank.get("format") != RANK_FORMAT:
        raise ValueError(f"rank must use current {RANK_FORMAT}")
    rows = _alias._load_instruction_rows(instruction_export, selected)

    alias_candidate = _alias._addr(
        (runtime_alias.get("candidate_global") or {}).get("address"),
        field="runtime-alias candidate global",
    )
    if alias_candidate != global_address:
        raise ValueError("runtime-alias candidate global disagrees with rank")
    if (runtime_alias.get("analysis") or {}).get("selected_function_count") != len(selected):
        raise ValueError("runtime-alias selected-function count disagrees with rank")

    states_by_function = {
        function: _alias._incoming_states(row["instructions"])
        for function, row in rows.items()
    }
    positive_aliases = [
        item
        for item in (runtime_alias.get("analysis") or {}).get("field_accesses") or []
        if isinstance(item, Mapping)
        and item.get("exact_single_candidate_global_value_as_field_base") is True
    ]

    seeds: list[dict[str, Any]] = []
    all_sinks: list[dict[str, Any]] = []
    skipped_positive_aliases: list[dict[str, Any]] = []
    for alias_item in positive_aliases:
        function = _alias._addr(alias_item.get("function"), field="alias.function")
        row = rows.get(function)
        if row is None:
            raise ValueError(f"positive runtime alias function not present in exact rank worklist: {function}")
        seed = _alias_seed(alias_item, row, states_by_function[function])
        if seed is None:
            skipped_positive_aliases.append(
                {
                    "function": function,
                    "instruction": _alias._addr(alias_item.get("instruction"), field="alias.instruction"),
                    "reason": "positive +0xca4 alias is not a simple pointer-sized MOV read into a tracked register",
                }
            )
            continue
        _, seed_address, instruction, marker, seeded_after = seed
        destination_register = _register((instruction.get("operands") or [None])[0])
        sinks = _trace_seed(row, seed_address, marker, seeded_after)
        seed_record = {
            "function": function,
            "instruction": seed_address,
            "instruction_text": instruction.get("text"),
            "destination_register": destination_register,
            "marker": marker,
            "sink_count": len(sinks),
            "sinks": sinks,
        }
        seeds.append(seed_record)
        for sink in sinks:
            all_sinks.append({"seed": {"function": function, "instruction": seed_address}, **sink})

    direct_targets = sorted(
        {
            str(sink["direct_target"])
            for sink in all_sinks
            if sink.get("kind") == "direct-call-register-transfer" and sink.get("direct_target")
        },
        key=lambda value: int(value, 16),
    )
    if len(direct_targets) > max_direct_targets:
        raise ValueError(
            f"exact direct-transfer worklist has {len(direct_targets)} targets, exceeding cap {max_direct_targets}"
        )

    ready = bool(all_sinks)
    blockers: list[dict[str, Any]] = []
    if skipped_positive_aliases:
        blockers.append(
            {
                "id": "positive-ca4-alias-not-pointer-load-seedable",
                "evidence_state": "blocked",
                "count": len(skipped_positive_aliases),
                "required_evidence": "a positive +0xca4 alias must be a simple pointer-sized MOV read into a tracked IA-32 register",
            }
        )
    if not all_sinks:
        blockers.append(
            {
                "id": "player-vehicle-renderables-first-hop-transfer-not-found",
                "evidence_state": "blocked",
                "required_evidence": "exact value loaded from the proven +0xca4 slot must reach a physical call/dereference/store/push/return sink in the bounded selected function",
            }
        )
    if ready and not direct_targets:
        blockers.append(
            {
                "id": "player-vehicle-renderables-direct-callee-transfer-not-found",
                "evidence_state": "unknown",
                "required_evidence": "continue from the exact non-call sink(s); do not guess neighboring callees",
            }
        )
    blockers.extend(
        [
            {
                "id": "player-vehicle-renderables-owner-join-unproven",
                "evidence_state": "unknown",
                "required_evidence": "prove that one exact first-hop transfer recipient/store consumer is the SMS/GraphicsEngine RenderHierarchy owner",
            },
            {
                "id": "outer-vehicle-root-to-VHF-vehicle-root-frame-relation-unproven",
                "evidence_state": "unknown",
                "required_evidence": "join the source-backed SMS/RenderHierarchy owner to the canonical BMW VHF vehicle-root or a fixed affine relation",
            },
        ]
    )

    sink_counts: dict[str, int] = {}
    for sink in all_sinks:
        kind = str(sink["kind"])
        sink_counts[kind] = sink_counts.get(kind, 0) + 1

    return {
        "format": FORMAT,
        "version": 1,
        "status": "first-hop-transfer-frontier-ready" if ready else "first-hop-transfer-frontier-blocked",
        "ready": ready,
        "retail": {"program": PROGRAM, "md5": PE_MD5},
        "subject": {
            "candidate_global": global_address,
            "field_offset": "+0xca4",
            "layout_label": "mPlayerVehicleRenderables",
        },
        "claim": {
            "first_hop_physical_transfer_sinks_extracted": ready,
            "semantic_owner_identity_proven": False,
            "VHF_frame_identity_proven": False,
        },
        "provenance": {
            "runtime_alias_format": ALIAS_FORMAT,
            "rank_format": RANK_FORMAT,
            "instruction_export_format": INSTRUCTION_FORMAT,
            "selected_function_count": len(selected),
            "positive_runtime_alias_count": len(positive_aliases),
            "seedable_pointer_load_count": len(seeds),
            "skipped_positive_alias_count": len(skipped_positive_aliases),
        },
        "analysis": {
            "sink_count": len(all_sinks),
            "sink_counts_by_kind": dict(sorted(sink_counts.items())),
            "seeds": seeds,
            "skipped_positive_aliases": skipped_positive_aliases,
            "all_sinks": all_sinks,
        },
        "targeted_instruction_worklist": {
            "format": INSTRUCTION_FORMAT,
            "functions": direct_targets,
            "max_functions": max_direct_targets,
            "selection_rule": "exact direct callees that receive the tainted +0xca4 field value in ECX or EDX",
            "neighbors_added": False,
        },
        "handoff": {
            "player_vehicle_renderables_first_hop_transfer_frontier_ready": ready,
            "player_vehicle_renderables_direct_transfer_worklist_ready": bool(direct_targets),
            "player_vehicle_renderables_owner_join_ready": False,
            "sms_vehicle_world_affine_RenderHierarchy_owner_join_ready": False,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "blockers": blockers,
        "limits": {
            "stack_push_linked_to_specific_callee": False,
            "memory_store_destination_object_identity_proven": False,
            "direct_call_register_position_promoted_to_semantic_parameter": False,
            "indirect_call_targets_guessed": False,
        },
        "consumer": {
            "process": 1,
            "next_proof": "physical first-hop recipient/store consumer -> SMS/GraphicsEngine RenderHierarchy owner -> canonical BMW VHF root",
        },
        "scope": {
            "original_game_executed": False,
            "runtime_capture_required": False,
            "all_path_register_provenance_required": True,
            "rank_proximity_promoted_to_pointer_identity": False,
            "first_hop_transfer_promoted_to_owner_identity": False,
            "indirect_targets_guessed": False,
            "frame_relation_claimed": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runtime_alias_artifact", type=Path)
    parser.add_argument("root_pose_rank_artifact", type=Path)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("--max-direct-targets", type=int, default=DEFAULT_MAX_DIRECT_TARGETS)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    try:
        report = build_frontier(
            args.runtime_alias_artifact,
            args.root_pose_rank_artifact,
            args.instruction_export,
            max_direct_targets=args.max_direct_targets,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 2
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
