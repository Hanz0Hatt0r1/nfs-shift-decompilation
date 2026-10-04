#!/usr/bin/env python3
"""Trace the retail receiver reaching the FUN_007682c0 +0x50 application.

This pass narrows one remaining external-physics boundary without promoting a
semantic identity that the current static evidence does not prove.  Existing
contracts already establish:

* FUN_00770e80 entry ECX is the global vehicle component base 0x00c13700;
* that base owns the BODY-array pointer through field +0x339c;
* the retail BMW main/chassis BODY is BODY index 0;
* FUN_007682c0 reads the source-visible motion triplet at +0x78/+0x80/+0x88
  and applies its visible scalar delta at +0x50.

What is still missing is the physical receiver provenance across the two
FUN_00770e80 physics-pass calls and their recovered tail:

    FUN_00770e80
      -> 0x00770f8f / 0x00770fbf : FUN_0076d100
      -> 0x0076d2c1              : FUN_00769ef0
      -> 0x0076a1e8              : FUN_007682c0

The analyzer consumes the ordinary saved Ghidra evidence database, the positive
retail SHIFT.GlobalVehicleBodyOwnerIdentity/1 artifact, and a targeted
SHIFT.GhidraFunctionInstructions/2 export for FUN_00770e80, FUN_0076d100 and
FUN_00769ef0.  It reuses the finite all-path register-provenance engine already
used by the BODY0 bind and SDF receiver proofs.

A deterministic receiver origin is *not* automatically a BODY0 identity.  In
particular, a memory origin mentioning +0x339c is reported only as a candidate
match until the base-register origin is independently proven to be the
FUN_00770e80 entry receiver.  This keeps the Phase 696 typed delta consumer
external until the exact destination record is proven.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import analyze_bmw_body0_bind_callsite_register_provenance as _callsite_engine

FORMAT = "SHIFT.Fun007682c0AccumulatorDestinationReceiverProvenance/1"
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
GLOBAL_IDENTITY_FORMAT = "SHIFT.GlobalVehicleBodyOwnerIdentity/1"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
RECEIVER_REGISTER = "ECX"
GLOBAL_VEHICLE_ADDRESS = "0x00c13700"
BODY_OWNER_FIELD_OFFSET = "0x339c"
BMW_CHASSIS_BODY_INDEX = 0
BMW_CHASSIS_BODY_NAME = "body"

TARGETS: dict[str, dict[str, str]] = {
    "0x00770e80": {
        "name": "FUN_00770e80",
        "mnemonic_sha256": "509d932c8a3c397f69fe91acecadef2bc148a05237a947c226d9ff039860514e",
        "calling_convention": "__thiscall",
        "role": "outer vehicle update with proven global-vehicle entry receiver",
    },
    "0x0076d100": {
        "name": "FUN_0076d100",
        "mnemonic_sha256": "ab1d8a14406c88e02240c03b0a636b7433df72e9dfaec4654746d19e6ba6de5c",
        "calling_convention": "__thiscall",
        "role": "two-pass physics update",
    },
    "0x00769ef0": {
        "name": "FUN_00769ef0",
        "mnemonic_sha256": "1ee3fee50472079154d2029eb4c861b3d1b1eda895347c531316678b7e15d1bf",
        "calling_convention": "__fastcall",
        "role": "recovered physics-pass tail",
    },
    "0x007682c0": {
        "name": "FUN_007682c0",
        "mnemonic_sha256": "f60c733cc0d0b3c755b3104953d1dc1d623d15f33978a6cbe50de7947b7f5d34",
        "calling_convention": "__thiscall",
        "role": "motion-read / +0x50 scalar-delta application",
    },
}

CALLS = (
    {
        "caller": "0x00770e80",
        "callsite": "0x00770f8f",
        "callee": "0x0076d100",
        "id": "outer-update-to-physics-pass-0",
        "pass_index": 0,
    },
    {
        "caller": "0x00770e80",
        "callsite": "0x00770fbf",
        "callee": "0x0076d100",
        "id": "outer-update-to-physics-pass-1",
        "pass_index": 1,
    },
    {
        "caller": "0x0076d100",
        "callsite": "0x0076d2c1",
        "callee": "0x00769ef0",
        "id": "physics-pass-to-tail",
    },
    {
        "caller": "0x00769ef0",
        "callsite": "0x0076a1e8",
        "callee": "0x007682c0",
        "id": "tail-to-motion-read-application",
    },
)

INSTRUCTION_FUNCTIONS = ("0x00770e80", "0x0076d100", "0x00769ef0")


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            text = raw.strip()
            if not text:
                continue
            try:
                value = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            rows.append(value)
    return rows


def _address(value: Any, *, field: str) -> str:
    try:
        return _callsite_engine._address(value, field=field)
    except ValueError as exc:
        raise ValueError(f"{field}: {exc}") from exc


def _sorted_origins(values: Iterable[str]) -> list[str]:
    return sorted(set(str(value) for value in values))


def _validate_retail_export(root: Path) -> dict[str, Any]:
    binary_path = root / "binary.json"
    functions_path = root / "functions.jsonl"
    callgraph_path = root / "callgraph.jsonl"
    for path in (binary_path, functions_path, callgraph_path):
        if not path.is_file():
            raise ValueError(f"missing Ghidra evidence file: {path}")

    binary = _load_json(binary_path)
    if binary.get("program_name") != PROGRAM:
        raise ValueError(f"unexpected Ghidra program: {binary.get('program_name')!r}")
    if binary.get("executable_md5") != PE_MD5:
        raise ValueError("unexpected retail executable MD5")

    found: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(functions_path):
        raw = row.get("address")
        if not isinstance(raw, str):
            continue
        address = _address(raw, field="functions.address")
        if address not in TARGETS:
            continue
        if address in found:
            raise ValueError(f"duplicate function row {address}")
        found[address] = row

    missing = sorted(set(TARGETS) - set(found))
    if missing:
        raise ValueError("missing required retail function(s): " + ", ".join(missing))
    for address, expected in TARGETS.items():
        row = found[address]
        if row.get("external") is True or row.get("thunk") is True:
            raise ValueError(f"{address}: expected concrete retail function")
        if row.get("name") != expected["name"]:
            raise ValueError(f"{address}: function name drift")
        if row.get("mnemonic_sha256") != expected["mnemonic_sha256"]:
            raise ValueError(f"{address}: mnemonic fingerprint drift")
        if row.get("calling_convention") != expected["calling_convention"]:
            raise ValueError(f"{address}: calling convention drift")

    edges: set[tuple[str, str, str]] = set()
    for row in _read_jsonl(callgraph_path):
        if row.get("indirect") is True:
            continue
        raw_from = row.get("from_function")
        raw_instruction = row.get("instruction")
        raw_to = row.get("to")
        if not all(isinstance(value, str) for value in (raw_from, raw_instruction, raw_to)):
            continue
        edges.add(
            (
                _address(raw_from, field="callgraph.from_function"),
                _address(raw_instruction, field="callgraph.instruction"),
                _address(raw_to, field="callgraph.to"),
            )
        )

    missing_edges = [
        (row["caller"], row["callsite"], row["callee"])
        for row in CALLS
        if (row["caller"], row["callsite"], row["callee"]) not in edges
    ]
    if missing_edges:
        raise ValueError(
            "missing required direct call edge(s): "
            + ", ".join(f"{a}:{i}->{b}" for a, i, b in missing_edges)
        )

    return {
        "program_name": PROGRAM,
        "executable_md5": PE_MD5,
        "functions": [
            {
                "address": address,
                "name": TARGETS[address]["name"],
                "role": TARGETS[address]["role"],
                "calling_convention": TARGETS[address]["calling_convention"],
                "mnemonic_sha256": TARGETS[address]["mnemonic_sha256"],
            }
            for address in TARGETS
        ],
        "required_direct_edges": [dict(row) for row in CALLS],
    }


def _validate_global_identity(path: Path) -> dict[str, Any]:
    value = _load_json(path)
    if value.get("format") != GLOBAL_IDENTITY_FORMAT:
        raise ValueError(f"global BODY-owner identity must be {GLOBAL_IDENTITY_FORMAT}")
    join = value.get("identity_join")
    handoff = value.get("handoff")
    if not isinstance(join, Mapping) or not isinstance(handoff, Mapping):
        raise ValueError("global BODY-owner identity missing identity_join/handoff")
    blockers = value.get("blockers")
    if blockers not in ([], None):
        raise ValueError("global BODY-owner identity has blockers")
    if str(join.get("global_vehicle_address") or "").lower() != GLOBAL_VEHICLE_ADDRESS:
        raise ValueError("global vehicle address drift")
    if join.get("global_vehicle_component_base_identity_ready") is not True:
        raise ValueError("global vehicle component-base identity is not ready")
    if join.get("BODY_array_owner_pointer_loaded_from_global_vehicle_base") is not True:
        raise ValueError("BODY-array owner field edge is not ready")
    if join.get("BODY_array_owner_is_global_vehicle_base") is not False:
        raise ValueError("BODY-array owner/global-vehicle separation drift")
    if str(join.get("BODY_array_owner_pointer_field_offset") or "").lower() != BODY_OWNER_FIELD_OFFSET:
        raise ValueError("BODY-array owner pointer field offset drift")
    if join.get("main_chassis_BODY_selected") is not True:
        raise ValueError("BMW main/chassis BODY selection is not ready")
    if join.get("main_chassis_BODY_name") != BMW_CHASSIS_BODY_NAME:
        raise ValueError("BMW main/chassis BODY name drift")
    if int(join.get("main_chassis_BODY_index", -1)) != BMW_CHASSIS_BODY_INDEX:
        raise ValueError("BMW main/chassis BODY index drift")
    if join.get("global_vehicle_BODY_owner_identity_ready") is not True:
        raise ValueError("global vehicle BODY-owner identity is not ready")
    if handoff.get("vehicle_BODY_selection_ready") is not True:
        raise ValueError("vehicle BODY selection handoff is not ready")
    if int(handoff.get("selected_BODY_index", -1)) != BMW_CHASSIS_BODY_INDEX:
        raise ValueError("vehicle BODY handoff index drift")
    if handoff.get("phase700_runtime_handoff_admissible") is not True:
        raise ValueError("Phase 700 BODY handoff is not admissible")

    return {
        "format": GLOBAL_IDENTITY_FORMAT,
        "ready": True,
        "global_vehicle_address": GLOBAL_VEHICLE_ADDRESS,
        "BODY_array_owner_pointer_field_offset": BODY_OWNER_FIELD_OFFSET,
        "BODY_array_owner_is_global_vehicle_base": False,
        "selected_BODY_index": BMW_CHASSIS_BODY_INDEX,
        "selected_BODY_name": BMW_CHASSIS_BODY_NAME,
    }


def _call_target(instruction: Mapping[str, Any], target: str) -> bool:
    normalized: list[str] = []
    flows = instruction.get("flows")
    if isinstance(flows, list):
        for value in flows:
            if not isinstance(value, str):
                continue
            try:
                normalized.append(_address(value, field="call flow"))
            except ValueError:
                pass
    if target in normalized:
        return True
    operands = instruction.get("operands")
    if isinstance(operands, list):
        for value in operands:
            if not isinstance(value, str):
                continue
            try:
                if _address(value, field="call operand") == target:
                    return True
            except ValueError:
                continue
    return False


def _classify_origins(origins: list[str]) -> tuple[str, bool]:
    if origins == [f"entry:{RECEIVER_REGISTER}"]:
        return "exact-entry-receiver", True
    flags = _callsite_engine._origin_flags(origins)
    resolved = flags["origin_count"] == 1 and not flags["contains_unknown_or_derived"]
    if not resolved:
        return "ambiguous", False
    if flags["contains_memory_origin"]:
        return "resolved-memory-origin", True
    return "resolved-nonentry-origin", True


def _analyze_call(
    instructions: list[dict[str, Any]],
    *,
    caller: str,
    callsite: str,
    callee: str,
    link_id: str,
    pass_index: int | None = None,
) -> dict[str, Any]:
    by_address = {
        _address(instruction.get("address"), field="instruction.address"): instruction
        for instruction in instructions
    }
    call = by_address.get(callsite)
    if call is None:
        raise ValueError(f"{caller}: missing required callsite {callsite}")
    if str(call.get("mnemonic") or "").upper() != "CALL":
        raise ValueError(f"{caller}:{callsite}: required instruction is not CALL")
    if not _call_target(call, callee):
        raise ValueError(f"{caller}:{callsite}: expected direct target {callee}")

    incoming, iterations = _callsite_engine._analyze_incoming_states(instructions)
    state = incoming.get(callsite)
    if state is None:
        raise ValueError(f"{caller}:{callsite}: callsite is unreachable from function entry")
    origins = _sorted_origins(state[RECEIVER_REGISTER])
    classification, resolved = _classify_origins(origins)
    row: dict[str, Any] = {
        "id": link_id,
        "caller": caller,
        "callsite": callsite,
        "callee": callee,
        "physical_receiver_register": RECEIVER_REGISTER,
        "receiver_origins_before_call": origins,
        "receiver_origin_cardinality": len(origins),
        "receiver_provenance_resolved_on_all_reachable_paths": resolved,
        "receiver_equals_caller_entry_ECX_on_all_reachable_paths": (
            origins == [f"entry:{RECEIVER_REGISTER}"]
        ),
        "classification": classification,
        "fixed_point_iterations": iterations,
        "reachable_instruction_count": len(incoming),
        "function_instruction_count": len(instructions),
        "lexical_window": _callsite_engine._lexical_window(instructions, callsite),
    }
    if pass_index is not None:
        row["pass_index"] = pass_index
    return row


def _normalized_origin(origin: str) -> str:
    return re.sub(r"\s+", "", origin.lower())


def _mentions_owner_field(origin: str) -> bool:
    normalized = _normalized_origin(origin)
    return normalized.startswith("memory:") and BODY_OWNER_FIELD_OFFSET in normalized


def analyze_fun_007682c0_destination_receiver_provenance(
    ghidra_export: Path,
    instruction_export: Path,
    global_identity_path: Path,
) -> dict[str, Any]:
    retail = _validate_retail_export(ghidra_export)
    global_identity = _validate_global_identity(global_identity_path)
    instruction_rows = _callsite_engine._index_instruction_rows(instruction_export)
    missing = [address for address in INSTRUCTION_FUNCTIONS if address not in instruction_rows]
    if missing:
        raise ValueError(
            "instruction export missing required function(s): " + ", ".join(missing)
        )

    links = [
        _analyze_call(
            instruction_rows[row["caller"]],
            caller=row["caller"],
            callsite=row["callsite"],
            callee=row["callee"],
            link_id=row["id"],
            pass_index=row.get("pass_index"),
        )
        for row in CALLS
    ]
    pass_links = links[:2]
    tail_link = links[2]
    effect_link = links[3]

    provenance_ready = all(
        row["receiver_provenance_resolved_on_all_reachable_paths"] is True
        for row in links
    )
    pass_origin_sets_equal = (
        provenance_ready
        and pass_links[0]["receiver_origins_before_call"]
        == pass_links[1]["receiver_origins_before_call"]
    )
    downstream_entry_continuity = (
        tail_link["receiver_equals_caller_entry_ECX_on_all_reachable_paths"] is True
        and effect_link["receiver_equals_caller_entry_ECX_on_all_reachable_paths"] is True
    )
    outer_to_effect_origin: list[str] | None = None
    if pass_origin_sets_equal and downstream_entry_continuity:
        outer_to_effect_origin = list(pass_links[0]["receiver_origins_before_call"])

    owner_field_candidate = bool(
        outer_to_effect_origin
        and len(outer_to_effect_origin) == 1
        and _mentions_owner_field(outer_to_effect_origin[0])
    )
    direct_global_vehicle_chain = outer_to_effect_origin == ["entry:ECX"]

    # A +0x339c memory expression is not sufficient by itself: the base register
    # used by that memory expression must still be proven to originate from the
    # FUN_00770e80 entry receiver on all reachable paths.  The generic origin
    # engine intentionally stops at the memory boundary, so this frontier never
    # promotes BODY0 solely from the textual displacement match.
    body0_join_proven = False

    blockers: list[dict[str, Any]] = []
    for row in links:
        if row["receiver_provenance_resolved_on_all_reachable_paths"] is True:
            continue
        blockers.append(
            {
                "id": row["id"] + "-receiver-provenance-ambiguous",
                "evidence_state": "ambiguous",
                "caller": row["caller"],
                "callsite": row["callsite"],
                "callee": row["callee"],
                "observed_origins": row["receiver_origins_before_call"],
                "required_evidence": (
                    "resolve every reachable ECX producer at this direct callsite "
                    "to one concrete origin"
                ),
            }
        )
    if provenance_ready and not pass_origin_sets_equal:
        blockers.append(
            {
                "id": "physics-pass-receivers-differ",
                "evidence_state": "verified-nonidentity",
                "pass_0_origins": pass_links[0]["receiver_origins_before_call"],
                "pass_1_origins": pass_links[1]["receiver_origins_before_call"],
                "required_evidence": "prove which pass receiver owns the FUN_007682c0 application",
            }
        )
    if provenance_ready and pass_origin_sets_equal and not downstream_entry_continuity:
        blockers.append(
            {
                "id": "pass-receiver-to-fun-007682c0-entry-continuity-unproven",
                "evidence_state": "verified-derived-receiver",
                "physics_pass_to_tail_origins": tail_link["receiver_origins_before_call"],
                "tail_to_effect_origins": effect_link["receiver_origins_before_call"],
                "required_evidence": (
                    "compose the exact derived receiver origin through FUN_0076d100/FUN_00769ef0 "
                    "rather than assuming entry-ECX continuity"
                ),
            }
        )
    if outer_to_effect_origin is not None and not body0_join_proven:
        if owner_field_candidate:
            required = (
                "prove the base register of the observed +0x339c memory load equals the "
                "FUN_00770e80 entry ECX/global vehicle base on all reachable paths"
            )
        elif direct_global_vehicle_chain:
            required = (
                "resolve why FUN_007682c0 receives the global-vehicle entry receiver while the "
                "proven BODY-array owner is a distinct pointer loaded from global+0x339c; do not "
                "relabel the global vehicle base as BODY0"
            )
        else:
            required = (
                "join the exact outer-to-effect receiver origin to the proven global+0x339c "
                "BODY-array owner and BMW chassis BODY index 0"
            )
        blockers.append(
            {
                "id": "fun-007682c0-receiver-to-retail-BODY0-semantic-join-unproven",
                "evidence_state": "unknown",
                "observed_outer_entry_relative_origins": outer_to_effect_origin,
                "owner_field_displacement_candidate_observed": owner_field_candidate,
                "required_evidence": required,
            }
        )

    status = "receiver-provenance-ready-semantic-join-blocked" if provenance_ready else "blocked"
    return {
        "format": FORMAT,
        "version": 1,
        "status": status,
        "ready": provenance_ready,
        "inputs": {
            "ghidra_export": str(ghidra_export),
            "instruction_export": str(instruction_export),
            "instruction_format": INSTRUCTION_FORMAT,
            "global_vehicle_BODY_owner_identity": str(global_identity_path),
            "global_vehicle_BODY_owner_identity_format": GLOBAL_IDENTITY_FORMAT,
        },
        "retail_identity": retail,
        "proven_BODY_owner_identity": global_identity,
        "receiver_links": links,
        "analysis": {
            "receiver_provenance_ready": provenance_ready,
            "both_physics_pass_receivers_same_origin": pass_origin_sets_equal,
            "physics_pass_to_tail_entry_ECX_continuity_proven": (
                tail_link["receiver_equals_caller_entry_ECX_on_all_reachable_paths"] is True
            ),
            "tail_to_FUN_007682c0_entry_ECX_continuity_proven": (
                effect_link["receiver_equals_caller_entry_ECX_on_all_reachable_paths"] is True
            ),
            "outer_entry_relative_FUN_007682c0_receiver_origins": outer_to_effect_origin,
            "outer_entry_is_proven_global_vehicle_base": True,
            "BODY_owner_pointer_field_offset": BODY_OWNER_FIELD_OFFSET,
            "owner_field_displacement_candidate_observed": owner_field_candidate,
            "direct_global_vehicle_receiver_chain_observed": direct_global_vehicle_chain,
            "receiver_to_retail_BMW_chassis_BODY0_join_proven": body0_join_proven,
        },
        "blocking_reasons": blockers,
        "handoff": {
            "FUN_007682c0_accumulator_destination_receiver_provenance_ready": provenance_ready,
            "FUN_007682c0_accumulator_destination_is_retail_BMW_BODY0": body0_join_proven,
            "FUN_007682c0_delta_consumer_internalization_ready": body0_join_proven,
            "phase696_typed_delta_consumer_must_remain_external": not body0_join_proven,
            "selected_retail_BODY_index": BMW_CHASSIS_BODY_INDEX,
        },
        "source_semantics": {
            "FUN_007682c0_motion_triplet_offsets": ["+0x78", "+0x80", "+0x88"],
            "FUN_007682c0_accumulator_delta_offset": "+0x50",
            "physical_field_name_or_units_claimed": False,
        },
        "scope": {
            "callgraph_adjacency_used_as_receiver_identity": False,
            "memory_displacement_match_used_as_BODY_identity": False,
            "global_vehicle_base_relabelled_as_BODY_owner": False,
            "BODY_owner_pointer_equals_global_vehicle_base_assumed": False,
            "complete_FUN_0076d100_semantics_claimed": False,
            "complete_FUN_00769ef0_semantics_claimed": False,
            "complete_FUN_007682c0_semantics_claimed": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
        "next_targeted_instruction_export": {
            "functions": list(INSTRUCTION_FUNCTIONS),
            "names": [TARGETS[address]["name"] for address in INSTRUCTION_FUNCTIONS],
            "command_suffix": "FUN_00770e80 FUN_0076d100 FUN_00769ef0",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ghidra_export", type=Path)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument(
        "global_vehicle_body_owner_identity",
        type=Path,
        help=f"positive retail {GLOBAL_IDENTITY_FORMAT} JSON",
    )
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    try:
        report = analyze_fun_007682c0_destination_receiver_provenance(
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
