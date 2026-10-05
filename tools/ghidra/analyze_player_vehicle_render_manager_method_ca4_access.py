#!/usr/bin/env python3
"""Prove direct manager-callee entry-register continuity into +0xca4 field reads.

This pass starts only after
SHIFT.PlayerVehicleRenderManagerReceiverTransferFrontier/2 has proven that the
candidate DAT_00bc185c manager pointer reaches a finite set of direct callees in
ECX and/or EDX. It consumes an exact targeted instruction export for that
worklist and asks one narrow question:

    does the proven call-entry register physically remain the sole all-path
    origin of the base register used by a p-code-backed +0xca4 memory access?

A positive read joins the independently proven render-manager class identity and
FUN_0045ef50 layout anchor to one runtime access of the
mPlayerVehicleRenderables field. It does not identify the field value's owner,
VHF root/frame identity, BODY0 bind-frame equality, or a vehicle world
transform.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import analyze_player_vehicle_renderables_runtime_alias as _alias
import analyze_register_relative_accesses as _accesses
import build_player_vehicle_render_manager_receiver_transfer_frontier as _v1
import build_player_vehicle_render_manager_receiver_transfer_frontier_v2 as _frontier

FORMAT = "SHIFT.PlayerVehicleRenderManagerMethodCa4Access/1"
FRONTIER_FORMAT = _frontier.FORMAT
INSTRUCTION_FORMAT = _v1.INSTRUCTION_FORMAT
PROGRAM = _v1.PROGRAM
PE_MD5 = _v1.PE_MD5
CANDIDATE_GLOBAL = _v1.CANDIDATE_GLOBAL
FIELD_OFFSET = 0xCA4
_ENTRY_REGISTERS = frozenset(("ECX", "EDX"))


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _validate_frontier(
    path: Path,
    identity: Mapping[str, Any],
) -> tuple[dict[str, Any], list[str], dict[str, set[str]]]:
    report = _load_json(path)
    if report.get("format") != FRONTIER_FORMAT or report.get("ready") is not True:
        raise ValueError(f"{path}: expected ready {FRONTIER_FORMAT}")
    if report.get("status") != "direct-manager-method-worklist-ready":
        raise ValueError("receiver frontier does not expose a direct-manager worklist")

    retail = report.get("retail")
    if not isinstance(retail, Mapping):
        raise ValueError("receiver frontier retail identity missing")
    if retail.get("program") != PROGRAM or str(retail.get("md5") or "").lower() != PE_MD5:
        raise ValueError("receiver frontier retail identity drift")

    candidate = report.get("candidate_global")
    if not isinstance(candidate, Mapping):
        raise ValueError("receiver frontier candidate_global missing")
    if _alias._addr(candidate.get("address"), field="candidate_global.address") != CANDIDATE_GLOBAL:
        raise ValueError("receiver frontier candidate-global drift")
    if candidate.get("render_manager_class_identity_proven") is not True:
        raise ValueError("receiver frontier lost render-manager class identity")
    if candidate.get("non_null_FUN_0045ef50_receiver_proven") is not True:
        raise ValueError("receiver frontier lost constructor receiver identity")

    inputs = report.get("inputs")
    if not isinstance(inputs, Mapping):
        raise ValueError("receiver frontier input provenance missing")
    constructor_input = inputs.get("constructor_identity")
    if not isinstance(constructor_input, Mapping):
        raise ValueError("receiver frontier constructor-identity provenance missing")
    if constructor_input.get("format") != _v1.IDENTITY_FORMAT or constructor_input.get("ready") is not True:
        raise ValueError("receiver frontier constructor-identity provenance drift")
    if identity.get("format") != constructor_input.get("format") or identity.get("ready") is not True:
        raise ValueError("supplied constructor identity disagrees with receiver frontier")

    handoff = report.get("handoff")
    if not isinstance(handoff, Mapping):
        raise ValueError("receiver frontier handoff missing")
    for gate in (
        "candidate_global_manager_receiver_transfer_frontier_ready",
        "candidate_global_manager_direct_method_worklist_ready",
    ):
        if handoff.get(gate) is not True:
            raise ValueError(f"receiver frontier prerequisite gate is not ready: {gate}")
    for gate in (
        "player_vehicle_renderables_field_runtime_access_ready",
        "player_vehicle_renderables_owner_join_ready",
        "outer_vehicle_root_to_VHF_vehicle_root_ready",
        "BODY0_bind_frame_proof_ready",
    ):
        if handoff.get(gate) is not False:
            raise ValueError(f"receiver frontier unexpectedly preclaims downstream gate: {gate}")

    worklist = report.get("targeted_instruction_worklist")
    if not isinstance(worklist, Mapping):
        raise ValueError("receiver frontier targeted worklist missing")
    raw_targets = worklist.get("functions")
    if not isinstance(raw_targets, list) or not raw_targets:
        raise ValueError("receiver frontier targeted worklist is empty")
    targets = [_alias._addr(value, field="targeted function") for value in raw_targets]
    if len(set(targets)) != len(targets):
        raise ValueError("receiver frontier targeted worklist contains duplicates")
    if worklist.get("function_count") != len(targets):
        raise ValueError("receiver frontier targeted worklist count mismatch")
    if worklist.get("neighbors_added") is not False:
        raise ValueError("receiver frontier unexpectedly broadened the direct worklist")

    provenance = report.get("provenance")
    analysis = report.get("analysis")
    if not isinstance(provenance, Mapping) or not isinstance(analysis, Mapping):
        raise ValueError("receiver frontier transfer provenance missing")
    transfers = analysis.get("call_receiver_transfers")
    if not isinstance(transfers, list):
        raise ValueError("receiver frontier call transfer list missing")

    direct = [
        item
        for item in transfers
        if isinstance(item, Mapping)
        and item.get("kind") == "direct-call-manager-receiver-transfer"
    ]
    if provenance.get("direct_call_receiver_transfer_count") != len(direct):
        raise ValueError("receiver frontier direct-transfer count mismatch")
    if not direct:
        raise ValueError("receiver frontier has no direct transfers")

    entry_registers: dict[str, set[str]] = defaultdict(set)
    for item in direct:
        if item.get("manager_receiver_identity_proven") is not True:
            raise ValueError("direct transfer lacks manager-pointer identity")
        if item.get("callee_method_identity_proven") is not True:
            raise ValueError("direct transfer lacks callee identity")
        target = _alias._addr(item.get("direct_target"), field="direct_target")
        register = str(item.get("source_register") or "").upper()
        if register not in _ENTRY_REGISTERS:
            raise ValueError(f"unsupported direct-transfer entry register: {register!r}")
        entry_registers[target].add(register)

    if set(entry_registers) != set(targets):
        missing = sorted(set(targets) - set(entry_registers), key=lambda value: int(value, 16))
        extra = sorted(set(entry_registers) - set(targets), key=lambda value: int(value, 16))
        raise ValueError(
            f"direct-transfer targets disagree with worklist; missing={missing}, extra={extra}"
        )
    return report, targets, entry_registers


def analyze(
    constructor_identity_path: Path,
    receiver_frontier_path: Path,
    targeted_instruction_export: Path,
) -> dict[str, Any]:
    identity = _v1._validate_identity(constructor_identity_path)
    frontier, targets, entry_registers = _validate_frontier(receiver_frontier_path, identity)
    rows = _alias._load_instruction_rows(targeted_instruction_export, targets)
    access_report = _accesses.analyze_register_relative_accesses(targeted_instruction_export)

    states = {
        function: _v1._incoming_states(row["instructions"])
        for function, row in rows.items()
    }
    candidates = [
        item
        for item in access_report.get("accesses") or []
        if isinstance(item, Mapping) and int(item.get("displacement", -1)) == FIELD_OFFSET
    ]

    analyses: list[dict[str, Any]] = []
    proven_accesses: list[dict[str, Any]] = []
    proven_reads: list[dict[str, Any]] = []
    for access in candidates:
        function = _alias._addr(access.get("function"), field="access.function")
        instruction = _alias._addr(access.get("instruction"), field="access.instruction")
        base = str(access.get("base_register") or "").upper()
        if base not in _v1._TRACKED:
            continue
        state = states[function].get(instruction)
        if state is None:
            raise ValueError(f"{function}:{instruction}: +0xca4 access is unreachable")
        origins = _alias._register_engine._sorted_origins(state[base])
        expected = sorted(entry_registers[function])
        matching = [register for register in expected if origins == [f"entry:{register}"]]
        exact = len(matching) == 1
        read_access = str(access.get("access") or "") in {"read", "read-write"}
        item = {
            "function": function,
            "function_name": access.get("function_name"),
            "instruction": instruction,
            "instruction_text": access.get("instruction_text"),
            "access": access.get("access"),
            "base_register": base,
            "field_offset": FIELD_OFFSET,
            "field_offset_hex": "+0xca4",
            "allowed_manager_entry_registers": expected,
            "base_origins_before_access": origins,
            "matching_manager_entry_registers": matching,
            "exact_single_manager_entry_pointer_as_field_base": exact,
            "runtime_field_read": exact and read_access,
            "pcode_memory_ops": access.get("pcode_memory_ops"),
            "constructor_layout_anchor": "FUN_0045ef50 receiver + 0xca4 = mPlayerVehicleRenderables",
            "player_vehicle_renderables_field_identity_proven": exact,
            "field_value_owner_identity_proven": False,
            "VHF_root_or_frame_identity_proven": False,
        }
        analyses.append(item)
        if exact:
            proven_accesses.append(item)
            if read_access:
                proven_reads.append(item)

    ready = bool(proven_reads)
    if proven_reads:
        status = "manager-method-ca4-read-ready"
    elif proven_accesses:
        status = "manager-method-ca4-write-only"
    else:
        status = "manager-method-ca4-access-not-found"

    blockers: list[dict[str, Any]] = []
    if not proven_accesses:
        blockers.append(
            {
                "id": "proven-manager-method-ca4-runtime-access-unproven",
                "evidence_state": "blocked",
                "required_evidence": (
                    "one targeted direct callee must contain a p-code-backed +0xca4 memory access "
                    "whose base has exactly one all-path origin from the proven call-entry ECX/EDX"
                ),
            }
        )
    elif not proven_reads:
        blockers.append(
            {
                "id": "proven-manager-method-ca4-runtime-read-unproven",
                "evidence_state": "blocked",
                "required_evidence": (
                    "the proven +0xca4 field relation must include a LOAD/read path before its "
                    "field value can be traced into the render-owner lane"
                ),
            }
        )
    blockers.extend(
        [
            {
                "id": "player-vehicle-renderables-to-render-owner-join-unproven",
                "evidence_state": "unknown",
                "required_evidence": (
                    "trace the exact value loaded from the proven manager +0xca4 field into the "
                    "SMS/RenderHierarchy owner lane"
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

    functions_with_reads = sorted(
        {item["function"] for item in proven_reads}, key=lambda value: int(value, 16)
    )
    return {
        "format": FORMAT,
        "version": 1,
        "status": status,
        "ready": ready,
        "retail": {"program": PROGRAM, "md5": PE_MD5},
        "candidate_global": {
            "address": CANDIDATE_GLOBAL,
            "render_manager_class_identity_proven": True,
            "non_null_FUN_0045ef50_receiver_proven": True,
        },
        "constructor_layout_anchor": {
            "function": "0x0045ef50",
            "field_offset": "+0xca4",
            "allocation_label": "mPlayerVehicleRenderables",
            "source_backed": True,
        },
        "inputs": {
            "constructor_identity": {"format": identity["format"], "ready": True},
            "receiver_transfer_frontier": {
                "format": frontier["format"],
                "ready": True,
                "direct_target_count": len(targets),
            },
            "instruction_export": {
                "format": INSTRUCTION_FORMAT,
                "selected_function_count": len(rows),
            },
        },
        "provenance": {
            "targeted_direct_callee_count": len(targets),
            "ca4_syntactic_pcode_backed_access_count": len(candidates),
            "exact_entry_pointer_ca4_access_count": len(proven_accesses),
            "exact_entry_pointer_ca4_read_count": len(proven_reads),
        },
        "analysis": {
            "entry_registers_by_target": {
                target: sorted(registers)
                for target, registers in sorted(
                    entry_registers.items(), key=lambda item: int(item[0], 16)
                )
            },
            "ca4_accesses": analyses,
            "proven_ca4_accesses": proven_accesses,
            "proven_ca4_reads": proven_reads,
        },
        "owner_trace_worklist": {
            "functions": functions_with_reads,
            "function_count": len(functions_with_reads),
            "neighbors_added": False,
            "selection_rule": (
                "only targeted direct callees with a p-code-backed +0xca4 read whose base has "
                "one all-path origin from the proven call-entry manager register"
            ),
        },
        "handoff": {
            "candidate_global_manager_method_ca4_access_ready": bool(proven_accesses),
            "player_vehicle_renderables_field_runtime_access_ready": ready,
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
            "targeted_instruction_set_must_exactly_match_frontier_worklist": True,
            "callsite_register_to_callee_entry_register_continuity_used": True,
            "all_path_register_provenance_required": True,
            "pcode_load_store_required_for_ca4_access": True,
            "constructor_layout_anchor_revalidated": True,
            "field_value_owner_promoted": False,
            "VHF_root_or_frame_identity_promoted": False,
            "BODY0_bind_frame_promoted": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("constructor_identity", type=Path)
    parser.add_argument("receiver_transfer_frontier_v2", type=Path)
    parser.add_argument("targeted_callee_instruction_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    try:
        report = analyze(
            args.constructor_identity,
            args.receiver_transfer_frontier_v2,
            args.targeted_callee_instruction_export,
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
