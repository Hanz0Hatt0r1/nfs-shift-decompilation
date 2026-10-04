#!/usr/bin/env python3
"""Trace physical ECX origins at the finite outer Vehicle transform fan-out.

Consumes ``SHIFT.OuterVehicleVHFRootRelationFrontier/1`` plus a targeted
``SHIFT.GhidraFunctionInstructions/2`` row for ``FUN_007927c0``.  The all-path
IA-32 register provenance engine already used by the BODY0/SDF receiver proofs
is reused unchanged.

This stage answers only a pointer-routing question: which physical ECX value is
present at each transform/state sink call.  For ``__thiscall`` callees ECX is the
physical receiver; for ``FUN_00787160`` it is only the first fastcall argument.
Matching origin expressions are reported but are not promoted to class, frame or
VHF hierarchy identity.  Stack transform arguments are deliberately deferred
until this pass has eliminated unrelated owner domains.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import analyze_bmw_body0_bind_callsite_register_provenance as _callsite
import build_outer_vehicle_vhf_root_relation_frontier as _frontier_builder

FORMAT = "SHIFT.OuterVehicleTransformSinkReceiverProvenance/1"
FRONTIER_FORMAT = _frontier_builder.FORMAT
INSTRUCTION_FORMAT = "SHIFT.GhidraFunctionInstructions/2"
OUTER_SETTER = _frontier_builder.OUTER_SETTER
HDVEHICLE_SETTER = _frontier_builder.HDVEHICLE_SETTER
ECX = "ECX"

# The two no-this computational helper candidates are intentionally absent.
# Every row below has a meaningful physical ECX channel at the ABI boundary.
SINK_CALLS = (
    {
        "callsite": "0x0079280e",
        "callee": "0x007876e0",
        "physical_ecx_role": "thiscall-receiver",
        "candidate_class": "transform-state-owner-candidate",
    },
    {
        "callsite": "0x00792828",
        "callee": "0x007afb60",
        "physical_ecx_role": "thiscall-receiver",
        "candidate_class": "vector-triplet-owner-candidate",
    },
    {
        "callsite": "0x00792884",
        "callee": "0x00787160",
        "physical_ecx_role": "fastcall-first-argument",
        "candidate_class": "fastcall-state-pointer-candidate",
    },
    {
        "callsite": "0x007928e3",
        "callee": HDVEHICLE_SETTER,
        "physical_ecx_role": "thiscall-receiver",
        "candidate_class": "proven-HDVehicle-physics-control",
    },
    {
        "callsite": "0x007928f0",
        "callee": "0x007ac2f0",
        "physical_ecx_role": "thiscall-receiver",
        "candidate_class": "post-transform-owner-candidate",
    },
)


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _address(value: Any, *, field: str) -> str:
    return _callsite._address(value, field=field)


def _validate_frontier(path: Path) -> dict[str, Any]:
    report = _load_json(path)
    if report.get("format") != FRONTIER_FORMAT:
        raise ValueError(f"{path}: expected {FRONTIER_FORMAT}")
    if report.get("ready") is not True or report.get("status") != "frontier-ready":
        raise ValueError("outer Vehicle/VHF root frontier is not ready")
    handoff = report.get("handoff")
    if not isinstance(handoff, Mapping):
        raise ValueError("frontier handoff missing")
    if handoff.get("outer_vehicle_spawn_path_static_frontier_ready") is not True:
        raise ValueError("frontier spawn path is not ready")
    if handoff.get("outer_vehicle_transform_fanout_static_frontier_ready") is not True:
        raise ValueError("frontier outer setter fan-out is not ready")
    if handoff.get("outer_vehicle_root_to_VHF_vehicle_root_ready") is not False:
        raise ValueError("frontier unexpectedly preclaims outer Vehicle/VHF root identity")
    if handoff.get("outer_vehicle_root_to_VHF_fixed_affine_delta_ready") is not False:
        raise ValueError("frontier unexpectedly preclaims outer Vehicle/VHF affine delta")

    retail = report.get("retail")
    calls = retail.get("outer_vehicle_setter_direct_calls") if isinstance(retail, Mapping) else None
    if not isinstance(calls, list):
        raise ValueError("frontier outer Vehicle setter call inventory missing")
    observed = {
        (
            _address(row.get("instruction"), field="frontier.call.instruction"),
            _address(row.get("callee"), field="frontier.call.callee"),
        )
        for row in calls
        if isinstance(row, Mapping)
    }
    expected = set(_frontier_builder.OUTER_SETTER_CALLS)
    if observed != expected:
        raise ValueError("frontier outer Vehicle setter fan-out drift")

    scope = report.get("scope")
    if not isinstance(scope, Mapping):
        raise ValueError("frontier scope missing")
    if scope.get("callgraph_adjacency_used_as_frame_identity") is not False:
        raise ValueError("frontier scope permits callgraph frame-identity inference")
    if scope.get("outer_vehicle_root_equated_to_VHF_root") is not False:
        raise ValueError("frontier scope already equates outer Vehicle/VHF root")
    return report


def _call_has_target(instruction: Mapping[str, Any], target: str) -> bool:
    for raw in list(instruction.get("flows") or []) + list(instruction.get("operands") or []):
        if not isinstance(raw, str):
            continue
        try:
            if _address(raw, field="call target") == target:
                return True
        except ValueError:
            continue
    return False


def _classify(origins: list[str]) -> str:
    flags = _callsite._origin_flags(origins)
    if origins == ["entry:ECX"]:
        return "exact-outer-setter-entry-ECX"
    if flags["origin_count"] != 1 or flags["contains_unknown_or_derived"]:
        return "ambiguous-or-derived"
    if flags["contains_memory_origin"]:
        return "exact-memory-origin-expression"
    if flags["contains_entry_origin"]:
        return "exact-other-entry-register"
    return "exact-nonentry-origin-expression"


def _origin_key(origins: list[str]) -> str:
    return " | ".join(origins)


def analyze_outer_vehicle_transform_sink_receiver_provenance(
    frontier_path: Path,
    instruction_export: Path,
) -> dict[str, Any]:
    frontier = _validate_frontier(frontier_path)
    rows = _callsite._index_instruction_rows(instruction_export)
    if OUTER_SETTER not in rows:
        raise ValueError(f"instruction export missing required function {OUTER_SETTER}")
    instructions = rows[OUTER_SETTER]
    by_address = {
        _address(row.get("address"), field="instruction.address"): row
        for row in instructions
    }
    incoming, iterations = _callsite._analyze_incoming_states(instructions)

    analyses: list[dict[str, Any]] = []
    for spec in SINK_CALLS:
        callsite = spec["callsite"]
        callee = spec["callee"]
        call = by_address.get(callsite)
        if call is None:
            raise ValueError(f"{OUTER_SETTER}: missing required callsite {callsite}")
        if str(call.get("mnemonic") or "").upper() != "CALL":
            raise ValueError(f"{OUTER_SETTER}:{callsite}: required instruction is not CALL")
        if not _call_has_target(call, callee):
            raise ValueError(f"{OUTER_SETTER}:{callsite}: expected direct target {callee}")
        state = incoming.get(callsite)
        if state is None:
            raise ValueError(f"{OUTER_SETTER}:{callsite}: callsite is unreachable")
        origins = _callsite._register_engine._sorted_origins(state[ECX])
        flags = _callsite._origin_flags(origins)
        analyses.append(
            {
                **spec,
                "callee_name": _frontier_builder.TARGETS[callee]["name"],
                "callee_calling_convention": _frontier_builder.TARGETS[callee]["calling_convention"],
                "ECX_origins_before_call": origins,
                "ECX_origin_flags": flags,
                "ECX_origin_classification": _classify(origins),
                "ECX_origin_deterministic": (
                    flags["exact_single_origin"] is True
                    and flags["contains_unknown_or_derived"] is False
                ),
                "ECX_equals_outer_setter_entry_ECX_on_all_reachable_paths": origins == ["entry:ECX"],
                "lexical_pre_call_window": _callsite._lexical_window(instructions, callsite),
                "lexical_window_is_path_proof": False,
            }
        )

    control = next(row for row in analyses if row["callee"] == HDVEHICLE_SETTER)
    control_origins = list(control["ECX_origins_before_call"])
    for row in analyses:
        row["same_ECX_origin_expression_set_as_HDVehicle_sink"] = (
            row["ECX_origins_before_call"] == control_origins
        )
        row["same_ECX_origin_expression_is_pointer_equality"] = False
        row["same_ECX_origin_expression_is_frame_identity"] = False

    groups: dict[str, dict[str, Any]] = {}
    for row in analyses:
        key = _origin_key(row["ECX_origins_before_call"])
        bucket = groups.setdefault(
            key,
            {
                "origin_expression_set": list(row["ECX_origins_before_call"]),
                "calls": [],
                "contains_HDVehicle_control": False,
            },
        )
        bucket["calls"].append(
            {
                "callsite": row["callsite"],
                "callee": row["callee"],
                "callee_name": row["callee_name"],
                "physical_ecx_role": row["physical_ecx_role"],
            }
        )
        if row["callee"] == HDVEHICLE_SETTER:
            bucket["contains_HDVehicle_control"] = True

    group_rows = sorted(
        groups.values(),
        key=lambda row: (
            0 if row["contains_HDVehicle_control"] else 1,
            _origin_key(row["origin_expression_set"]),
        ),
    )
    ambiguous = [
        row for row in analyses
        if row["ECX_origin_deterministic"] is not True
    ]
    thiscall_candidates = [
        row for row in analyses
        if row["physical_ecx_role"] == "thiscall-receiver"
        and row["callee"] != HDVEHICLE_SETTER
    ]

    blockers: list[dict[str, Any]] = []
    if ambiguous:
        blockers.append(
            {
                "id": "outer-setter-sink-ECX-origin-ambiguity",
                "callsites": [row["callsite"] for row in ambiguous],
                "required_evidence": (
                    "resolve every reachable ECX producer for the ambiguous sink callsites; "
                    "do not select one lexical predecessor"
                ),
            }
        )
    blockers.append(
        {
            "id": "outer-setter-owner-to-vhf-hierarchy-owner-join-unproven",
            "required_evidence": (
                "for each surviving deterministic thiscall receiver domain, prove concrete "
                "callee writes/forwards and join its owner-producing path to the canonical "
                "BMW VHF hierarchy load owner"
            ),
        }
    )

    return {
        "format": FORMAT,
        "version": 1,
        "status": "receiver-frontier-ready" if not ambiguous else "receiver-frontier-ambiguous",
        "ready": True,
        "inputs": {
            "frontier": str(frontier_path),
            "instruction_export": str(instruction_export),
            "instruction_format": INSTRUCTION_FORMAT,
        },
        "outer_vehicle_setter": {
            "address": OUTER_SETTER,
            "name": _frontier_builder.TARGETS[OUTER_SETTER]["name"],
            "instruction_count": len(instructions),
            "reachable_instruction_count": len(incoming),
            "fixed_point_iterations": iterations,
        },
        "sink_receiver_analyses": analyses,
        "ECX_origin_groups": group_rows,
        "HDVehicle_control": {
            "callsite": control["callsite"],
            "callee": control["callee"],
            "ECX_origins_before_call": control_origins,
            "ECX_origin_deterministic": control["ECX_origin_deterministic"],
        },
        "next_owner_candidates": [
            {
                "callsite": row["callsite"],
                "callee": row["callee"],
                "callee_name": row["callee_name"],
                "ECX_origins_before_call": row["ECX_origins_before_call"],
                "ECX_origin_deterministic": row["ECX_origin_deterministic"],
                "same_ECX_origin_expression_set_as_HDVehicle_sink": row[
                    "same_ECX_origin_expression_set_as_HDVehicle_sink"
                ],
            }
            for row in thiscall_candidates
        ],
        "fastcall_ECX_candidate": next(
            {
                "callsite": row["callsite"],
                "callee": row["callee"],
                "callee_name": row["callee_name"],
                "ECX_origins_before_call": row["ECX_origins_before_call"],
                "ECX_origin_deterministic": row["ECX_origin_deterministic"],
            }
            for row in analyses
            if row["physical_ecx_role"] == "fastcall-first-argument"
        ),
        "handoff": {
            "outer_setter_sink_ECX_provenance_evaluated": True,
            "outer_setter_sink_ECX_provenance_unambiguous": not ambiguous,
            "outer_vehicle_root_to_VHF_vehicle_root_ready": False,
            "outer_vehicle_root_to_VHF_fixed_affine_delta_ready": False,
            "BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready": False,
            "BODY0_bind_frame_proof_ready": False,
            "vehicle_world_transform_ready": False,
        },
        "blockers": blockers,
        "next_proof": {
            "target": "concrete writes/forwards and owner provenance for deterministic thiscall receiver domains",
            "stack_transform_argument_provenance_deferred_until_owner_candidates_narrowed": True,
            "required_VHF_join": "candidate owner -> canonical BMW VHF hierarchy vehicle-root loader/owner",
        },
        "scope": {
            "frontier_consumed_without_preclaim": frontier.get("format") == FRONTIER_FORMAT,
            "all_path_register_provenance_used": True,
            "lexical_window_used_as_path_proof": False,
            "matching_origin_expression_promoted_to_pointer_equality": False,
            "matching_origin_expression_promoted_to_frame_identity": False,
            "fastcall_ECX_promoted_to_this_receiver": False,
            "callgraph_adjacency_used_as_frame_identity": False,
            "outer_vehicle_root_equated_to_VHF_root": False,
            "new_runtime_capture_required": False,
            "original_game_executed": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("frontier", type=Path)
    parser.add_argument("instruction_export", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    report = analyze_outer_vehicle_transform_sink_receiver_provenance(
        args.frontier,
        args.instruction_export,
    )
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.json_out is None:
        print(text, end="")
    else:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
