#!/usr/bin/env python3
"""Prove or close +0xca4 access in the exact resolved indirect render-manager entries."""
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

import analyze_player_vehicle_render_manager_method_ca4_access as _direct
import analyze_player_vehicle_renderables_runtime_alias as _alias
import analyze_register_relative_accesses as _accesses
import build_player_vehicle_render_manager_receiver_transfer_frontier as _v1

FORMAT = "SHIFT.PlayerVehicleRenderManagerIndirectMethodCa4Access/1"
INDIRECT_FORMAT = "SHIFT.PlayerVehicleRenderManagerIndirectDispatch/1"
SLICE_FORMAT = "SHIFT.GhidraInstructionSlice/1"
PROGRAM = _v1.PROGRAM
PE_MD5 = _v1.PE_MD5
CANDIDATE_GLOBAL = _v1.CANDIDATE_GLOBAL
FIELD_OFFSET = 0xCA4


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_no}: expected object")
        rows.append(value)
    if not rows:
        raise ValueError(f"{path}: empty instruction-slice export")
    return rows


def _validate_direct_negative(path: Path) -> dict[str, Any]:
    report = _load_json(path)
    if report.get("format") != _direct.FORMAT or report.get("ready") is not False:
        raise ValueError(f"{path}: expected negative {_direct.FORMAT}")
    retail = report.get("retail")
    if not isinstance(retail, Mapping) or retail.get("program") != PROGRAM or str(retail.get("md5") or "").lower() != PE_MD5:
        raise ValueError("direct +0xca4 retail identity drift")
    candidate = report.get("candidate_global")
    if not isinstance(candidate, Mapping) or candidate.get("render_manager_class_identity_proven") is not True:
        raise ValueError("direct +0xca4 artifact lost manager class identity")
    if _alias._addr(candidate.get("address"), field="candidate_global.address") != CANDIDATE_GLOBAL:
        raise ValueError("direct +0xca4 candidate-global drift")
    anchor = report.get("constructor_layout_anchor")
    if not isinstance(anchor, Mapping) or anchor.get("source_backed") is not True:
        raise ValueError("direct +0xca4 constructor layout anchor missing")
    if anchor.get("function") != "0x0045ef50" or anchor.get("field_offset") != "+0xca4" or anchor.get("allocation_label") != "mPlayerVehicleRenderables":
        raise ValueError("direct +0xca4 constructor layout anchor drift")
    provenance = report.get("provenance")
    if not isinstance(provenance, Mapping) or provenance.get("targeted_direct_callee_count") != 17:
        raise ValueError("direct +0xca4 artifact does not close the frozen 17-target branch")
    if provenance.get("exact_entry_pointer_ca4_read_count") != 0:
        raise ValueError("direct +0xca4 branch is not negative")
    return report


def _validate_indirect(path: Path) -> tuple[dict[str, Any], list[str]]:
    report = _load_json(path)
    if report.get("format") != INDIRECT_FORMAT or report.get("ready") is not True:
        raise ValueError(f"{path}: expected ready {INDIRECT_FORMAT}")
    retail = report.get("retail")
    if not isinstance(retail, Mapping) or retail.get("program") != PROGRAM or str(retail.get("md5") or "").lower() != PE_MD5:
        raise ValueError("indirect-dispatch retail identity drift")
    handoff = report.get("handoff")
    if not isinstance(handoff, Mapping):
        raise ValueError("indirect-dispatch handoff missing")
    for gate in ("candidate_global_manager_indirect_dispatch_resolved", "candidate_global_manager_indirect_method_worklist_ready"):
        if handoff.get(gate) is not True:
            raise ValueError(f"indirect-dispatch prerequisite gate is not ready: {gate}")
    worklist = report.get("targeted_instruction_worklist")
    if not isinstance(worklist, Mapping) or worklist.get("neighbors_added") is not False:
        raise ValueError("indirect-dispatch worklist missing or broadened")
    raw = worklist.get("functions")
    if not isinstance(raw, list) or not raw:
        raise ValueError("indirect-dispatch worklist empty")
    targets = [_alias._addr(item, field="indirect target") for item in raw]
    if worklist.get("function_count") != len(targets) or len(set(targets)) != len(targets):
        raise ValueError("indirect-dispatch worklist count/uniqueness drift")
    analysis = report.get("analysis")
    provenance = report.get("provenance")
    if not isinstance(analysis, Mapping) or not isinstance(provenance, Mapping):
        raise ValueError("indirect-dispatch provenance missing")
    calls = analysis.get("resolved_indirect_calls")
    if not isinstance(calls, list) or provenance.get("resolved_indirect_call_count") != len(calls) or len(calls) != 3:
        raise ValueError("indirect-dispatch must resolve the frozen three callsites")
    resolved_targets: set[str] = set()
    for call in calls:
        if not isinstance(call, Mapping):
            raise ValueError("malformed resolved indirect call")
        if call.get("manager_receiver_identity_proven") is not True or call.get("constructor_primary_table_identity_proven") is not True:
            raise ValueError("resolved indirect call lost manager/table identity")
        if call.get("static_slot_target_proven") is not True or call.get("straight_line_slot_load_proven") is not True:
            raise ValueError("resolved indirect call lost physical slot proof")
        if str(call.get("manager_receiver_register_at_call") or "").upper() != "ECX":
            raise ValueError("resolved indirect manager receiver is not ECX")
        resolved_targets.add(_alias._addr(call.get("resolved_target"), field="resolved_target"))
    if resolved_targets != set(targets):
        raise ValueError("resolved indirect targets disagree with worklist")
    return report, targets


def _load_slices(path: Path, targets: list[str]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(path):
        if row.get("format") != SLICE_FORMAT or row.get("program") != PROGRAM:
            raise ValueError(f"{path}: expected {SLICE_FORMAT} for {PROGRAM}")
        start = _alias._addr(row.get("start"), field="slice.start")
        if start in rows:
            raise ValueError(f"duplicate slice {start}")
        if row.get("exact_instruction_at_start") is not True:
            raise ValueError(f"{start}: no exact instruction at dispatch entry")
        instructions = row.get("instructions")
        if not isinstance(instructions, list) or not instructions:
            raise ValueError(f"{start}: empty instruction slice")
        if row.get("instruction_count") != len(instructions):
            raise ValueError(f"{start}: instruction count mismatch")
        first = _alias._addr(instructions[0].get("address"), field="first instruction") if isinstance(instructions[0], Mapping) else None
        if first != start:
            raise ValueError(f"{start}: first exported instruction does not equal dispatch entry")
        rows[start] = row
    if set(rows) != set(targets):
        raise ValueError(f"slice target set drift; expected={sorted(targets)}, got={sorted(rows)}")
    return rows


def _addr_or_none(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return _alias._addr(value)
    except ValueError:
        return None


def _cfg_complete(instructions: list[dict[str, Any]], incoming: Mapping[str, Any]) -> tuple[bool, list[dict[str, Any]]]:
    addresses = {_alias._addr(item.get("address"), field="instruction.address") for item in instructions}
    issues: list[dict[str, Any]] = []
    for item in instructions:
        address = _alias._addr(item.get("address"), field="instruction.address")
        if address not in incoming:
            continue
        mnemonic = str(item.get("mnemonic") or "").upper()
        if mnemonic in {"RET", "RETF", "IRET", "IRETD"}:
            continue
        fallthrough = _addr_or_none(item.get("fallthrough"))
        raw_flows = item.get("flows")
        flows = [_addr_or_none(value) for value in raw_flows] if isinstance(raw_flows, list) else []
        flows = [value for value in flows if value is not None]
        if mnemonic == "CALL":
            if fallthrough is None or fallthrough not in addresses:
                issues.append({"instruction": address, "reason": "call-fallthrough-outside-slice", "target": fallthrough})
            continue
        if flows:
            for target in flows:
                if target not in addresses:
                    issues.append({"instruction": address, "reason": "branch-target-outside-slice", "target": target})
            if mnemonic != "JMP" and (fallthrough is None or fallthrough not in addresses):
                issues.append({"instruction": address, "reason": "conditional-fallthrough-outside-slice", "target": fallthrough})
            continue
        if fallthrough is None or fallthrough not in addresses:
            issues.append({"instruction": address, "reason": "nonterminal-fallthrough-outside-slice", "target": fallthrough})
    return not issues, issues


def _candidate_accesses(entry: str, instructions: list[dict[str, Any]], incoming: Mapping[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in instructions:
        if not isinstance(item, Mapping):
            raise ValueError(f"{entry}: malformed instruction")
        address = _alias._addr(item.get("address"), field="instruction.address")
        state = incoming.get(address)
        if state is None:
            continue
        operands = item.get("operands")
        if not isinstance(operands, list) or any(not isinstance(value, str) for value in operands):
            raise ValueError(f"{entry}:{address}: operands must be strings")
        pcode = _accesses._validate_pcode(item.get("pcode"), address)
        kinds = _accesses._pcode_memory_kinds(pcode)
        access_kind = _accesses._access_kind(kinds)
        for index, operand in enumerate(operands):
            parsed = _accesses._parse_memory_operand(operand)
            if parsed is None:
                continue
            base, displacement = parsed
            if displacement != FIELD_OFFSET or base not in _v1._TRACKED:
                continue
            origins = _alias._register_engine._sorted_origins(state[base])
            exact = origins == ["entry:ECX"]
            pcode_backed = access_kind is not None
            read_access = access_kind in {"read", "read-write"}
            result.append({
                "entry": entry,
                "instruction": address,
                "instruction_text": item.get("text"),
                "operand_index": index,
                "operand": operand,
                "base_register": base,
                "base_origins_before_access": origins,
                "field_offset": FIELD_OFFSET,
                "field_offset_hex": "+0xca4",
                "access": access_kind,
                "pcode_memory_ops": sorted(kinds),
                "pcode_backed_memory_access": pcode_backed,
                "exact_entry_ecx_as_field_base": exact,
                "runtime_field_read": bool(exact and pcode_backed and read_access),
                "player_vehicle_renderables_field_identity_proven": bool(exact and pcode_backed),
                "field_value_owner_identity_proven": False,
            })
    return result


def analyze(direct_negative_path: Path, indirect_dispatch_path: Path, slice_export_path: Path) -> dict[str, Any]:
    direct = _validate_direct_negative(direct_negative_path)
    indirect, targets = _validate_indirect(indirect_dispatch_path)
    rows = _load_slices(slice_export_path, targets)

    target_reports: list[dict[str, Any]] = []
    all_accesses: list[dict[str, Any]] = []
    proven_accesses: list[dict[str, Any]] = []
    proven_reads: list[dict[str, Any]] = []
    complete_count = 0
    for target in targets:
        instructions = rows[target]["instructions"]
        incoming = _v1._incoming_states(instructions)
        complete, issues = _cfg_complete(instructions, incoming)
        if complete:
            complete_count += 1
        accesses = _candidate_accesses(target, instructions, incoming)
        all_accesses.extend(accesses)
        exact = [item for item in accesses if item["player_vehicle_renderables_field_identity_proven"]]
        reads = [item for item in exact if item["runtime_field_read"]]
        proven_accesses.extend(exact)
        proven_reads.extend(reads)
        target_reports.append({
            "entry": target,
            "slice_length": rows[target].get("length"),
            "reachable_instruction_count": len(incoming),
            "cfg_complete_for_negative_closure": complete,
            "cfg_completeness_issues": issues,
            "ca4_candidate_count": len(accesses),
            "proven_ca4_access_count": len(exact),
            "proven_ca4_read_count": len(reads),
        })

    ready = bool(proven_reads)
    negative_closed = not ready and complete_count == len(targets)
    if ready:
        status = "indirect-manager-method-ca4-read-ready"
    elif proven_accesses:
        status = "indirect-manager-method-ca4-write-only"
    elif negative_closed:
        status = "indirect-manager-method-ca4-access-not-found"
    else:
        status = "indirect-manager-method-ca4-acquisition-incomplete"

    blockers: list[dict[str, Any]] = []
    if not ready:
        blockers.append({
            "id": "indirect-manager-method-ca4-runtime-access-unproven",
            "evidence_state": "blocked" if negative_closed else "unknown",
            "required_evidence": (
                "a resolved indirect dispatch entry must contain a p-code-backed +0xca4 read whose base has "
                "exact all-path origin entry:ECX"
            ),
        })
    blockers.extend([
        {"id": "player-vehicle-renderables-to-render-owner-join-unproven", "evidence_state": "unknown", "required_evidence": "trace the exact loaded +0xca4 value into the SMS/RenderHierarchy owner lane"},
        {"id": "outer-vehicle-root-to-VHF-vehicle-root-frame-relation-unproven", "evidence_state": "unknown", "required_evidence": "join the proven render owner to canonical BMW VHF root/frame identity"},
    ])

    worklist = sorted({item["entry"] for item in proven_reads}, key=lambda value: int(value, 16))
    return {
        "format": FORMAT,
        "version": 1,
        "status": status,
        "ready": ready,
        "retail": {"program": PROGRAM, "md5": PE_MD5},
        "candidate_global": {"address": CANDIDATE_GLOBAL, "render_manager_class_identity_proven": True},
        "constructor_layout_anchor": direct["constructor_layout_anchor"],
        "inputs": {
            "direct_manager_method_ca4": {"format": direct["format"], "ready": False, "targeted_direct_callee_count": 17},
            "indirect_dispatch": {"format": indirect["format"], "ready": True, "target_count": len(targets)},
            "instruction_slices": {"format": SLICE_FORMAT, "target_count": len(rows)},
        },
        "provenance": {
            "resolved_indirect_target_count": len(targets),
            "cfg_complete_target_count": complete_count,
            "ca4_candidate_count": len(all_accesses),
            "exact_entry_ecx_ca4_access_count": len(proven_accesses),
            "exact_entry_ecx_ca4_read_count": len(proven_reads),
            "negative_branch_closed": negative_closed,
        },
        "analysis": {
            "targets": target_reports,
            "ca4_accesses": all_accesses,
            "proven_ca4_accesses": proven_accesses,
            "proven_ca4_reads": proven_reads,
        },
        "owner_trace_worklist": {
            "entries": worklist,
            "entry_count": len(worklist),
            "neighbors_added": False,
            "selection_rule": "only resolved indirect dispatch entries with a proven entry:ECX +0xca4 p-code-backed read",
        },
        "handoff": {
            "candidate_global_manager_indirect_method_ca4_access_ready": bool(proven_accesses),
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
            "resolved_dispatch_entries_used_as_machine_entry_identity": True,
            "ghidra_function_creation_required": False,
            "all_path_register_provenance_required": True,
            "pcode_load_store_required_for_ca4_access": True,
            "cfg_completeness_required_for_negative_closure": True,
            "direct_manager_method_branch_reopened": False,
            "field_value_owner_promoted": False,
            "VHF_root_or_frame_identity_promoted": False,
            "BODY0_bind_frame_promoted": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("direct_manager_method_ca4", type=Path)
    parser.add_argument("indirect_dispatch", type=Path)
    parser.add_argument("instruction_slices", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    try:
        report = analyze(args.direct_manager_method_ca4, args.indirect_dispatch, args.instruction_slices)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 2
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    print(f"format: {report['format']}")
    print(f"status: {report['status']}")
    print(f"ready: {str(report['ready']).lower()}")
    print(f"resolved targets: {report['provenance']['resolved_indirect_target_count']}")
    print(f"CFG-complete targets: {report['provenance']['cfg_complete_target_count']}")
    print(f"proven +0xca4 reads: {report['provenance']['exact_entry_ecx_ca4_read_count']}")
    if args.json_out:
        print(f"output: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
