#!/usr/bin/env python3
"""Build the first proven render-manager receiver-transfer frontier.

This pass starts only after
SHIFT.PlayerVehicleRenderManagerGlobalConstructorIdentity/1 has made
DAT_00bc185c class identity positive. It consumes the exhaustive root-pose-aware
xref rank plus the exact instruction export selected by that rank, seeds a
unique taint token at every exact READ of DAT_00bc185c whose p-code proves a
tracked register receives the global value, and follows that same physical
pointer through the local CFG.

Only first-hop receiver transfers are emitted. Direct CALL targets reached with
the exact manager pointer in ECX/EDX become a finite targeted-instruction
worklist. Indirect receiver CALLs are recorded but deliberately unresolved.
Nothing here proves a +0xca4 runtime access, mPlayerVehicleRenderables ownership,
VHF identity, frame equality, or BODY0 closure.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from pathlib import Path
from typing import Any, Mapping

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import analyze_player_vehicle_renderables_runtime_alias as _alias
import analyze_register_relative_accesses as _accesses
import build_player_vehicle_renderables_owner_transfer_frontier as _owner

FORMAT = "SHIFT.PlayerVehicleRenderManagerReceiverTransferFrontier/1"
IDENTITY_FORMAT = "SHIFT.PlayerVehicleRenderManagerGlobalConstructorIdentity/1"
RANK_FORMAT = _alias.ROOT_POSE_RANK_FORMAT
INSTRUCTION_FORMAT = _alias.INSTRUCTION_FORMAT
PROGRAM = _alias.PROGRAM
PE_MD5 = _alias.PE_MD5
CANDIDATE_GLOBAL = "0x00bc185c"
DEFAULT_MAX_DIRECT_TARGETS = 64
_TRACKED = tuple(_alias._TRACKED)


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _validate_identity(path: Path) -> dict[str, Any]:
    report = _load_json(path)
    if report.get("format") != IDENTITY_FORMAT or report.get("ready") is not True:
        raise ValueError(f"{path}: expected ready {IDENTITY_FORMAT}")
    retail = report.get("retail")
    if not isinstance(retail, Mapping):
        raise ValueError("constructor-identity retail identity missing")
    if retail.get("program") != PROGRAM or str(retail.get("md5") or "").lower() != PE_MD5:
        raise ValueError("constructor-identity retail identity drift")
    candidate = report.get("candidate_global")
    if not isinstance(candidate, Mapping):
        raise ValueError("constructor-identity candidate_global missing")
    if _alias._addr(candidate.get("address"), field="candidate_global.address") != CANDIDATE_GLOBAL:
        raise ValueError("constructor-identity candidate-global drift")
    if candidate.get("all_write_xrefs_accounted_for") is not True:
        raise ValueError("constructor-identity does not account for all global writers")
    if candidate.get("non_null_values_are_FUN_0045ef50_receivers") is not True:
        raise ValueError("constructor-identity non-null receiver identity is not positive")
    handoff = report.get("handoff")
    if not isinstance(handoff, Mapping):
        raise ValueError("constructor-identity handoff missing")
    for gate in (
        "candidate_global_render_manager_class_identity_ready",
        "candidate_global_non_null_FUN_0045ef50_receiver_ready",
        "constructor_player_vehicle_renderables_layout_anchor_ready",
    ):
        if handoff.get(gate) is not True:
            raise ValueError(f"constructor-identity prerequisite gate is not ready: {gate}")
    for gate in (
        "player_vehicle_renderables_field_runtime_access_ready",
        "player_vehicle_renderables_owner_join_ready",
        "outer_vehicle_root_to_VHF_vehicle_root_ready",
        "BODY0_bind_frame_proof_ready",
    ):
        if handoff.get(gate) is not False:
            raise ValueError(f"constructor-identity unexpectedly preclaims downstream gate: {gate}")
    inputs = report.get("inputs")
    if not isinstance(inputs, Mapping):
        raise ValueError("constructor-identity inputs provenance missing")
    root_pose = inputs.get("root_pose_rank")
    if not isinstance(root_pose, Mapping):
        raise ValueError("constructor-identity root-pose rank provenance missing")
    if root_pose.get("format") != RANK_FORMAT:
        raise ValueError("constructor-identity was not rooted in the current root-pose rank")
    if root_pose.get("candidate_global_write_xrefs_exhaustive") is not True:
        raise ValueError("constructor-identity rank did not exhaust candidate-global writers")
    return report


def _validate_rank(path: Path, identity: Mapping[str, Any]) -> tuple[dict[str, Any], str, list[str]]:
    rank, global_address, selected = _alias._load_rank(path)
    if rank.get("format") != RANK_FORMAT:
        raise ValueError(f"{path}: expected current {RANK_FORMAT}")
    if global_address != CANDIDATE_GLOBAL:
        raise ValueError("rank candidate-global drift")
    root_pose = ((identity.get("inputs") or {}).get("root_pose_rank") or {})
    if not isinstance(root_pose, Mapping):
        raise ValueError("constructor-identity root-pose provenance malformed")
    if root_pose.get("selected_function_count") != len(selected):
        raise ValueError("rank selected-function count disagrees with positive constructor identity")
    ranking = rank.get("ranking")
    if not isinstance(ranking, Mapping):
        raise ValueError("rank ranking section missing")
    if root_pose.get("ranked_function_count") != ranking.get("ranked_function_count"):
        raise ValueError("rank ranked-function count disagrees with positive constructor identity")
    return rank, global_address, selected


def _reference_reads(rank: Mapping[str, Any], selected: list[str]) -> list[dict[str, Any]]:
    ranking = rank.get("ranking")
    if not isinstance(ranking, Mapping):
        raise ValueError("rank ranking section missing")
    selected_set = set(selected)
    reads: list[dict[str, Any]] = []
    for row in ranking.get("functions") or []:
        if not isinstance(row, Mapping):
            continue
        function = _alias._addr(row.get("function"), field="ranking.function")
        if function not in selected_set:
            continue
        for site in row.get("reference_sites") or []:
            if not isinstance(site, Mapping) or str(site.get("type") or "").upper() != "READ":
                continue
            reads.append(
                {
                    "function": function,
                    "instruction": _alias._addr(site.get("from"), field="reference_sites.from"),
                    "instruction_text": site.get("instruction"),
                }
            )
    reads.sort(key=lambda item: (int(item["function"], 16), int(item["instruction"], 16)))
    return reads


def _instruction_map(row: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in row.get("instructions") or []:
        if not isinstance(item, dict):
            raise ValueError("instruction row contains a non-object instruction")
        address = _alias._addr(item.get("address"), field="instruction.address")
        if address in result:
            raise ValueError(f"duplicate instruction {address}")
        result[address] = item
    return result


def _single_marker(values: Any, marker: str) -> bool:
    return isinstance(values, frozenset) and values == frozenset((marker,))


def _seed_from_read(
    read: Mapping[str, Any],
    row: Mapping[str, Any],
    incoming_states: Mapping[str, Any],
    global_address: str,
) -> tuple[str, str, dict[str, frozenset[str]], dict[str, Any]] | None:
    function = _alias._addr(read.get("function"), field="read.function")
    address = _alias._addr(read.get("instruction"), field="read.instruction")
    instruction = _instruction_map(row).get(address)
    if instruction is None:
        raise ValueError(f"{function}:{address}: exact rank READ instruction missing")
    before = incoming_states.get(address)
    if not isinstance(before, dict):
        raise ValueError(f"{function}:{address}: exact rank READ instruction unreachable")
    after = _alias._register_engine._transfer(instruction, before)

    raw_pcode = instruction.get("pcode")
    _accesses._validate_pcode(raw_pcode, address)
    if not isinstance(raw_pcode, list):
        raise ValueError(f"{address}: pcode must be a list")
    load_outputs: list[str] = []
    for op in raw_pcode:
        if not isinstance(op, Mapping):
            raise ValueError(f"{address}: pcode operation must be an object")
        if str(op.get("opcode") or "").upper() != "LOAD":
            continue
        output = op.get("output")
        if not isinstance(output, Mapping) or output.get("register") is not True:
            continue
        register = str(output.get("text") or "").strip().upper()
        if register in _TRACKED:
            load_outputs.append(register)
    candidates: list[tuple[str, list[str]]] = []
    for register in sorted(set(load_outputs)):
        origins = _alias._register_engine._sorted_origins(after[register])
        before_origins = _alias._register_engine._sorted_origins(before[register])
        if len(origins) != 1 or before_origins == origins:
            continue
        if _alias._origin_mentions_global(origins[0], global_address):
            candidates.append((register, origins))
    if len(candidates) != 1:
        return None
    destination, origins = candidates[0]
    marker = f"candidate-global-manager:{function}@{address}"
    seeded = dict(after)
    seeded[destination] = frozenset((marker,))
    return address, marker, seeded, {
        "function": function,
        "instruction": address,
        "instruction_text": instruction.get("text"),
        "destination_register": destination,
        "global_origins_after_read": origins,
        "marker": marker,
        "pcode_backed_global_load": True,
    }


def _call_sinks(
    function: str,
    marker: str,
    instruction: Mapping[str, Any],
    state: Mapping[str, frozenset[str]],
) -> list[dict[str, Any]]:
    if str(instruction.get("mnemonic") or "").upper() != "CALL":
        return []
    address = _alias._addr(instruction.get("address"), field="call.instruction")
    operands = instruction.get("operands")
    if not isinstance(operands, list) or any(not isinstance(value, str) for value in operands):
        raise ValueError(f"{function}:{address}: CALL operands must be strings")
    direct_target = _owner._direct_call_target(instruction)
    sinks: list[dict[str, Any]] = []
    for register, role in (("ECX", "this/arg-ecx"), ("EDX", "arg-edx")):
        if not _single_marker(state[register], marker):
            continue
        sinks.append(
            {
                "kind": (
                    "direct-call-manager-receiver-transfer"
                    if direct_target is not None
                    else "indirect-call-manager-receiver-transfer"
                ),
                "function": function,
                "instruction": address,
                "instruction_text": instruction.get("text"),
                "source_register": register,
                "register_role": role,
                "call_operand": operands[0] if len(operands) == 1 else None,
                "direct_target": direct_target,
                "manager_receiver_identity_proven": True,
                "callee_method_identity_proven": direct_target is not None,
                "callee_ca4_access_proven": False,
                "player_vehicle_renderables_owner_join_proven": False,
            }
        )
    return sinks


def _other_sinks(
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
    for index, operand in enumerate(operands):
        parsed = _accesses._parse_memory_operand(operand)
        if parsed is None:
            continue
        base_register, displacement = parsed
        if base_register in state and _single_marker(state[base_register], marker):
            sinks.append(
                {
                    "kind": "manager-pointer-dereference",
                    "function": function,
                    "instruction": address,
                    "instruction_text": instruction.get("text"),
                    "base_register": base_register,
                    "operand_index": index,
                    "operand": operand,
                    "displacement": displacement,
                    "displacement_hex": _accesses._format_displacement(displacement),
                    "field_semantics_proven": False,
                }
            )
    if mnemonic == "PUSH" and operands:
        register = operands[0].strip().upper()
        if register in state and _single_marker(state[register], marker):
            sinks.append(
                {
                    "kind": "manager-pointer-stack-push",
                    "function": function,
                    "instruction": address,
                    "instruction_text": instruction.get("text"),
                    "source_register": register,
                    "receiving_callee_proven": False,
                }
            )
    if mnemonic in {"RET", "RETF"} and _single_marker(state["EAX"], marker):
        sinks.append(
            {
                "kind": "manager-pointer-return-value",
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
    by_address = _instruction_map(row)
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
            raise ValueError(f"{function}:{seed_address}: manager taint did not converge")
        state = incoming[address]
        instruction = by_address[address]
        sinks.extend(_call_sinks(function, marker, instruction, state))
        sinks.extend(_other_sinks(function, marker, instruction, state))
        after = _alias._register_engine._transfer(instruction, state)
        for successor in _alias._register_engine._successors(instruction, address_set):
            if successor == seed_address:
                continue
            merged, changed = _alias._register_engine._merge(incoming.get(successor), after)
            if changed:
                incoming[successor] = merged
                queue.append(successor)
    return sinks


def build_frontier(
    constructor_identity_path: Path,
    rank_path: Path,
    instruction_export: Path,
    *,
    max_direct_targets: int = DEFAULT_MAX_DIRECT_TARGETS,
) -> dict[str, Any]:
    if max_direct_targets <= 0:
        raise ValueError("max_direct_targets must be positive")
    identity = _validate_identity(constructor_identity_path)
    rank, global_address, selected = _validate_rank(rank_path, identity)
    rows = _alias._load_instruction_rows(instruction_export, selected)
    reads = _reference_reads(rank, selected)
    states = {
        function: _alias._incoming_states(row["instructions"])
        for function, row in rows.items()
    }
    seeds: list[dict[str, Any]] = []
    skipped_reads: list[dict[str, Any]] = []
    all_sinks: list[dict[str, Any]] = []
    for read in reads:
        function = read["function"]
        seeded = _seed_from_read(read, rows[function], states[function], global_address)
        if seeded is None:
            skipped_reads.append(
                {**read, "reason": "read-does-not-yield-one-exact-pcode-backed-tracked-register"}
            )
            continue
        seed_address, marker, seeded_after, seed_info = seeded
        seeds.append(seed_info)
        all_sinks.extend(_trace_seed(rows[function], seed_address, marker, seeded_after))

    def _sink_key(item: Mapping[str, Any]) -> tuple[Any, ...]:
        return (
            str(item.get("kind") or ""),
            int(str(item.get("function") or "0x0"), 16),
            int(str(item.get("instruction") or "0x0"), 16),
            str(item.get("source_register") or item.get("base_register") or ""),
            str(item.get("direct_target") or ""),
            str(item.get("operand") or item.get("call_operand") or ""),
        )

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for sink in sorted(all_sinks, key=_sink_key):
        key = _sink_key(sink)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(sink)
    all_sinks = deduped
    call_transfers = [
        sink
        for sink in all_sinks
        if sink.get("kind") in {
            "direct-call-manager-receiver-transfer",
            "indirect-call-manager-receiver-transfer",
        }
    ]
    direct_transfers = [
        sink
        for sink in call_transfers
        if sink.get("kind") == "direct-call-manager-receiver-transfer"
        and isinstance(sink.get("direct_target"), str)
    ]
    indirect_transfers = [
        sink
        for sink in call_transfers
        if sink.get("kind") == "indirect-call-manager-receiver-transfer"
    ]
    direct_targets = sorted(
        {str(sink["direct_target"]) for sink in direct_transfers},
        key=lambda value: int(value, 16),
    )
    if len(direct_targets) > max_direct_targets:
        raise ValueError(
            f"direct manager-method worklist has {len(direct_targets)} targets, "
            f"exceeding safety cap {max_direct_targets}"
        )
    ready = bool(call_transfers)
    status = (
        "direct-manager-method-worklist-ready"
        if direct_targets
        else "indirect-manager-dispatch-frontier-ready"
        if indirect_transfers
        else "manager-receiver-transfer-not-found"
    )
    blockers: list[dict[str, Any]] = []
    if not call_transfers:
        blockers.append(
            {
                "id": "proven-manager-receiver-first-hop-call-transfer-not-found",
                "evidence_state": "blocked",
                "required_evidence": (
                    "one exact candidate-global read must physically survive to an ECX/EDX CALL site"
                ),
            }
        )
    if not direct_targets and indirect_transfers:
        blockers.append(
            {
                "id": "proven-manager-receiver-indirect-dispatch-target-unresolved",
                "evidence_state": "unknown",
                "required_evidence": (
                    "resolve the recorded indirect CALL operand/vtable slot before targeted callee export"
                ),
            }
        )
    blockers.extend(
        [
            {
                "id": "proven-manager-method-ca4-runtime-access-unproven",
                "evidence_state": "unknown",
                "required_evidence": (
                    "targeted callee instruction export must prove entry receiver -> +0xca4 access"
                ),
            },
            {
                "id": "player-vehicle-renderables-to-render-owner-join-unproven",
                "evidence_state": "unknown",
                "required_evidence": (
                    "trace the exact +0xca4 value into the SMS/RenderHierarchy owner lane"
                ),
            },
            {
                "id": "outer-vehicle-root-to-VHF-vehicle-root-frame-relation-unproven",
                "evidence_state": "unknown",
                "required_evidence": (
                    "join the proven render owner to canonical BMW VHF root/frame identity"
                ),
            },
        ]
    )
    return {
        "format": FORMAT,
        "version": 1,
        "status": status,
        "ready": ready,
        "retail": {"program": PROGRAM, "md5": PE_MD5},
        "candidate_global": {
            "address": global_address,
            "render_manager_class_identity_proven": True,
            "non_null_FUN_0045ef50_receiver_proven": True,
        },
        "inputs": {
            "constructor_identity": {"format": identity["format"], "ready": True},
            "root_pose_rank": {"format": rank["format"], "selected_function_count": len(selected)},
            "instruction_export": {"format": INSTRUCTION_FORMAT, "selected_function_count": len(rows)},
        },
        "provenance": {
            "exact_global_read_xref_count": len(reads),
            "seedable_global_read_count": len(seeds),
            "skipped_global_read_count": len(skipped_reads),
            "call_receiver_transfer_count": len(call_transfers),
            "direct_call_receiver_transfer_count": len(direct_transfers),
            "indirect_call_receiver_transfer_count": len(indirect_transfers),
        },
        "analysis": {
            "seeds": seeds,
            "skipped_reads": skipped_reads,
            "call_receiver_transfers": call_transfers,
            "all_sinks": all_sinks,
        },
        "targeted_instruction_worklist": {
            "functions": direct_targets,
            "function_count": len(direct_targets),
            "max_functions": max_direct_targets,
            "neighbors_added": False,
            "selection_rule": (
                "only direct CALL targets reached with the exact proven candidate-global "
                "manager pointer in ECX/EDX"
            ),
        },
        "handoff": {
            "candidate_global_manager_receiver_transfer_frontier_ready": ready,
            "candidate_global_manager_direct_method_worklist_ready": bool(direct_targets),
            "candidate_global_manager_indirect_dispatch_frontier_ready": bool(indirect_transfers),
            "player_vehicle_renderables_field_runtime_access_ready": False,
            "player_vehicle_renderables_owner_join_ready": False,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "blockers": blockers,
        "scope": {
            "original_game_executed": False,
            "runtime_capture_required": False,
            "broad_callgraph_neighbors_added": False,
            "candidate_global_class_identity_reproven": False,
            "direct_global_to_ca4_branch_reopened": False,
            "direct_call_target_promoted_to_ca4_owner": False,
            "indirect_call_promoted_to_resolved_method": False,
            "frame_identity_claimed": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("constructor_identity", type=Path)
    parser.add_argument("exhaustive_root_pose_rank", type=Path)
    parser.add_argument("exhaustive_instruction_export", type=Path)
    parser.add_argument("--max-direct-targets", type=int, default=DEFAULT_MAX_DIRECT_TARGETS)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    try:
        report = build_frontier(
            args.constructor_identity,
            args.exhaustive_root_pose_rank,
            args.exhaustive_instruction_export,
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
