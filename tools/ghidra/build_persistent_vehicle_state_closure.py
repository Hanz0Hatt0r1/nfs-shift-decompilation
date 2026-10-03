#!/usr/bin/env python3
"""Join the proven BODY schedule with the static caller/ABI frontier.

This is a fail-closed composition layer.  It does not discover new physical
semantics from callgraph proximity.  Instead it cross-checks three independently
produced static reports and emits one current persistent-vehicle-state graph with
explicit evidence states and the remaining ownership/scheduling blockers.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.PersistentVehicleStateClosure/1"
BODY_SCHEDULE_FORMAT = "SHIFT.GhidraBodyUpdateScheduleFrontier/2"
CALLER_FRONTIER_FORMAT = "SHIFT.GhidraVehicleOuterUpdateCallerFrontier/1"
OUTER_CALLSITE_FORMAT = "SHIFT.OuterUpdateCallsiteStatic/1"
BODY_INTEGRATION_CONTRACT = "SHIFT.BodyFrameIntegrationStatic/1"

OUTER_UPDATE = "0x00770e80"
PHYSICS_PASS = "0x0076d100"
HALF_STEP_ORCHESTRATOR = "0x00765470"
BODY_ARRAY_LOOP = "0x007b2270"
BODY_INTEGRATOR = "0x007bab70"
DIRECT_CALLERS = ("0x00794a30", "0x0079b2d0")
UPSTREAM_BATCH = "0x00713050"
UPSTREAM_OWNER = "0x00715380"
OUTER_RECEIVER = "DAT_00c13700"

EVIDENCE_STATES = {"proven", "verified", "inferred", "ambiguous", "unknown"}


def _load_report(path: Path, expected_format: str) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        raise ValueError(f"{path}: expected JSON object")
    actual = report.get("format")
    if actual != expected_format:
        raise ValueError(f"{path}: expected {expected_format}, found {actual}")
    return report


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _hex_offset(value: Any) -> str:
    if isinstance(value, str):
        int(value, 0)
        return hex(int(value, 0))
    if isinstance(value, int):
        return hex(value)
    raise ValueError(f"invalid offset value: {value!r}")


def _direct_call_targets(row: dict[str, Any]) -> list[str]:
    result: list[str] = []
    for edge in row.get("ordered_direct_calls") or []:
        target = edge.get("to")
        if isinstance(target, str):
            result.append(target)
    return result


def _direct_callers(row: dict[str, Any]) -> list[str]:
    result: list[str] = []
    for edge in row.get("direct_incoming_calls") or []:
        source = edge.get("from_function")
        if isinstance(source, str):
            result.append(source)
    return sorted(set(result), key=lambda value: int(value, 0))


def _caller_row(report: dict[str, Any], address: str) -> dict[str, Any]:
    matches = [row for row in report.get("direct_callers") or [] if row.get("address") == address]
    if len(matches) != 1:
        raise ValueError(f"caller frontier: expected one row for {address}; found {len(matches)}")
    return matches[0]


def _callsite_row(report: dict[str, Any], address: str) -> dict[str, Any]:
    matches = [row for row in report.get("direct_callsites") or [] if row.get("caller") == address]
    if len(matches) != 1:
        raise ValueError(f"outer callsite contract: expected one row for {address}; found {len(matches)}")
    return matches[0]


def _candidate(
    *,
    address: str,
    callers: list[str],
    callees: list[str],
    read_offsets: list[str],
    write_offsets: list[str],
    pointer_evidence: str,
    exact_evidence: list[str],
    subsystem: str,
    state: str,
    blockers: list[str],
) -> dict[str, Any]:
    _require(state in EVIDENCE_STATES, f"invalid evidence state {state}")
    return {
        "address": address,
        "callers": callers,
        "callees": callees,
        "read_offsets": sorted(set(read_offsets), key=lambda value: int(value, 0)),
        "write_offsets": sorted(set(write_offsets), key=lambda value: int(value, 0)),
        "pointer_base_register_evidence": pointer_evidence,
        "exact_instruction_or_source_evidence": exact_evidence,
        "subsystem": subsystem,
        "evidence_state": state,
        "unresolved_blockers": blockers,
        "promoted_semantic_name": False,
    }


def build_persistent_vehicle_state_closure(
    body_schedule_path: Path,
    caller_frontier_path: Path,
    outer_callsite_path: Path,
) -> dict[str, Any]:
    schedule = _load_report(body_schedule_path, BODY_SCHEDULE_FORMAT)
    caller_frontier = _load_report(caller_frontier_path, CALLER_FRONTIER_FORMAT)
    callsite = _load_report(outer_callsite_path, OUTER_CALLSITE_FORMAT)

    schedule_outer = schedule.get("outer_update") or {}
    schedule_physics = schedule.get("physics_pass") or {}
    integration = schedule.get("body_integration") or {}
    recovered = schedule.get("recovered") or {}

    _require(schedule_outer.get("function") == OUTER_UPDATE, "body schedule outer-update anchor changed")
    _require(schedule_physics.get("function") == PHYSICS_PASS, "body schedule physics-pass anchor changed")
    _require(
        (recovered.get("between_pass_bridge") or {}).get("address") == HALF_STEP_ORCHESTRATOR,
        "body schedule half-step orchestrator changed",
    )
    _require(integration.get("array_loop") == BODY_ARRAY_LOOP, "BODY array-loop anchor changed")
    _require(integration.get("persistent_integrator") == BODY_INTEGRATOR, "BODY integrator anchor changed")
    _require(integration.get("semantic_contract") == BODY_INTEGRATION_CONTRACT, "BODY integration semantic contract changed")
    _require(integration.get("schedule_link_proven") is True, "BODY integration schedule link is not proven")

    _require(caller_frontier.get("outer_update_anchor") == OUTER_UPDATE, "caller frontier outer-update anchor changed")
    caller_addresses = sorted(
        [row.get("address") for row in caller_frontier.get("direct_callers") or [] if isinstance(row.get("address"), str)]
    )
    _require(caller_addresses == sorted(DIRECT_CALLERS), f"direct caller set changed: {caller_addresses}")

    outer = callsite.get("outer_update") or {}
    _require(outer.get("function") == OUTER_UPDATE, "outer callsite function changed")
    _require(outer.get("receiver_at_callsites") == OUTER_RECEIVER, "outer-update receiver identity changed")
    _require(outer.get("physics_pass_target") == PHYSICS_PASS, "outer-update physics-pass target changed")
    _require(outer.get("physics_pass_count") == 2, "outer-update physics-pass count changed")

    callsite_callers = sorted(
        [row.get("caller") for row in callsite.get("direct_callsites") or [] if isinstance(row.get("caller"), str)]
    )
    _require(callsite_callers == caller_addresses, "caller frontier and source/callsite contract disagree")

    batch = callsite.get("upstream_batch_path") or {}
    owner = callsite.get("upstream_owner_path") or {}
    _require(batch.get("function") == UPSTREAM_BATCH, "upstream batch anchor changed")
    _require(owner.get("function") == UPSTREAM_OWNER, "upstream owner anchor changed")

    caller_a = _caller_row(caller_frontier, DIRECT_CALLERS[0])
    caller_b = _caller_row(caller_frontier, DIRECT_CALLERS[1])
    callsite_a = _callsite_row(callsite, DIRECT_CALLERS[0])
    callsite_b = _callsite_row(callsite, DIRECT_CALLERS[1])

    _require(callsite_a.get("channels_written_from_function_arguments_before_call") is True, "first caller no longer proves channel writes before outer update")
    _require(callsite_b.get("channels_read_from_caller_object") is True, "second caller no longer proves channel reads")
    _require(caller_b.get("direct_incoming_count") == 0, "second caller acquired a direct upstream edge; ownership frontier must be re-audited")
    _require(callsite_b.get("direct_incoming_call_count") == 0, "source/callsite contract no longer records second caller as ownerless")

    a_channel_a = _hex_offset(callsite_a.get("caller_channel_a_offset"))
    a_channel_b = _hex_offset(callsite_a.get("caller_channel_b_offset"))
    b_channel_a = _hex_offset(callsite_b.get("caller_channel_a_offset"))
    b_channel_b = _hex_offset(callsite_b.get("caller_channel_b_offset"))
    _require((a_channel_a, a_channel_b) == (b_channel_a, b_channel_b), "direct callers disagree on channel offsets")

    batch_reads = [
        _hex_offset(batch.get("record_pointer_array_offset")),
        _hex_offset(batch.get("record_count_offset")),
        _hex_offset(batch.get("channel_a_seed_offset")),
        _hex_offset(batch.get("accumulator_offset")),
    ]

    candidates = [
        _candidate(
            address=DIRECT_CALLERS[0],
            callers=_direct_callers(caller_a),
            callees=_direct_call_targets(caller_a),
            read_offsets=["0x234"],
            write_offsets=[a_channel_a, a_channel_b],
            pointer_evidence="source uses one caller object for gate/channel stores; class identity is not promoted",
            exact_evidence=[
                "source contract: caller +0x1aa8/+0x1ab0 written from function arguments before FUN_00770e80",
                "Ghidra contract: exactly one direct call to FUN_00770e80",
            ],
            subsystem="vehicle-update caller frontier",
            state="verified",
            blockers=["final class identity", "input/control argument provenance", "rendered-frame cadence"],
        ),
        _candidate(
            address=DIRECT_CALLERS[1],
            callers=_direct_callers(caller_b),
            callees=_direct_call_targets(caller_b),
            read_offsets=["0x34", "0x234", b_channel_a, b_channel_b],
            write_offsets=[],
            pointer_evidence="source reads gate/channel fields from one caller object; no direct upstream caller exists in the saved callgraph",
            exact_evidence=[
                "source contract: case-zero path forwards caller +0x1aa8/+0x1ab0 to FUN_00770e80",
                "Ghidra frontier: direct incoming count is zero",
                "switches export: internal computed-jump candidate retained separately from external ownership",
            ],
            subsystem="vehicle-update alternate caller frontier",
            state="ambiguous",
            blockers=["external/indirect owner or dispatcher", "final class identity", "rendered-frame cadence"],
        ),
        _candidate(
            address=UPSTREAM_BATCH,
            callers=[UPSTREAM_OWNER],
            callees=[DIRECT_CALLERS[0]],
            read_offsets=batch_reads,
            write_offsets=[],
            pointer_evidence="source-backed container traversal reaches child object as *record + 0x340; child class identity remains unknown",
            exact_evidence=[
                f"record base/count offsets {batch.get('record_pointer_array_offset')}/{batch.get('record_count_offset')}",
                f"record stride {batch.get('record_stride')}; child adjustment {batch.get('child_object_pointer_adjustment')}",
                "three source/direct-callgraph-correlated calls to FUN_00794a30",
            ],
            subsystem="vehicle-update batch/container frontier",
            state="verified",
            blockers=["record/container class identity", "source of caller arguments above the batch", "frame scheduling ownership"],
        ),
        _candidate(
            address=UPSTREAM_OWNER,
            callers=[],
            callees=[UPSTREAM_BATCH],
            read_offsets=[],
            write_offsets=[],
            pointer_evidence="only the direct source/callgraph edge into FUN_00713050 is imported by this closure layer",
            exact_evidence=["source + Ghidra direct edge FUN_00715380 -> FUN_00713050"],
            subsystem="upper vehicle-update ownership frontier",
            state="inferred",
            blockers=["caller/lifecycle provenance above FUN_00715380", "object identity", "rendered-frame cadence"],
        ),
    ]

    graph = [
        {
            "from": UPSTREAM_OWNER,
            "to": UPSTREAM_BATCH,
            "relation": "direct-call",
            "evidence_state": "verified",
            "evidence": "source and Ghidra callgraph cross-check",
        },
        {
            "from": UPSTREAM_BATCH,
            "to": DIRECT_CALLERS[0],
            "relation": "three-direct-calls",
            "evidence_state": "verified",
            "evidence": "source and Ghidra callgraph cross-check",
        },
        {
            "from": DIRECT_CALLERS[0],
            "to": OUTER_UPDATE,
            "relation": "direct-call",
            "evidence_state": "proven",
            "evidence": f"source/callgraph callsite; receiver {OUTER_RECEIVER}",
        },
        {
            "from": DIRECT_CALLERS[1],
            "to": OUTER_UPDATE,
            "relation": "direct-call-owner-unresolved",
            "evidence_state": "proven",
            "evidence": f"source/callgraph callsite; receiver {OUTER_RECEIVER}",
        },
        {
            "from": OUTER_UPDATE,
            "to": PHYSICS_PASS,
            "relation": "two-pass-update",
            "evidence_state": "proven",
            "evidence": "source callsite contract plus Ghidra BODY schedule",
        },
        {
            "from": OUTER_UPDATE,
            "to": HALF_STEP_ORCHESTRATOR,
            "relation": "after-each-physics-pass",
            "evidence_state": "proven",
            "evidence": "direct-call schedule frontier",
        },
        {
            "from": HALF_STEP_ORCHESTRATOR,
            "to": BODY_ARRAY_LOOP,
            "relation": "post-solve-body-array-integration",
            "evidence_state": "proven",
            "evidence": "FUN_007b3f40 -> FUN_007b4110 -> FUN_007b2270 order is required by the schedule frontier",
        },
        {
            "from": BODY_ARRAY_LOOP,
            "to": BODY_INTEGRATOR,
            "relation": "persistent-body-integration",
            "evidence_state": "proven",
            "evidence": BODY_INTEGRATION_CONTRACT,
        },
        {
            "from": "input/control ownership",
            "to": UPSTREAM_OWNER,
            "relation": "unresolved-upstream-boundary",
            "evidence_state": "unknown",
            "evidence": "no source/callgraph proof in the composed reports",
        },
        {
            "from": OUTER_UPDATE,
            "to": "rendered-frame cadence",
            "relation": "schedule-frequency-boundary",
            "evidence_state": "unknown",
            "evidence": "outer-update execution is proven, rendered-frame frequency is not",
        },
    ]

    blockers = [
        {
            "id": "input-control-owner",
            "evidence_state": "unknown",
            "addresses": [UPSTREAM_OWNER, UPSTREAM_BATCH, DIRECT_CALLERS[0]],
            "required_evidence": "caller/argument provenance tying an identified input/control owner to the static update chain",
        },
        {
            "id": "alternate-caller-dispatch-owner",
            "evidence_state": "unknown",
            "addresses": [DIRECT_CALLERS[1]],
            "required_evidence": "code/data reference, callback table, vtable slot, or other static dispatch evidence naming the incoming owner",
        },
        {
            "id": "rendered-frame-cadence",
            "evidence_state": "unknown",
            "addresses": [UPSTREAM_OWNER, OUTER_UPDATE],
            "required_evidence": "static scheduler path proving the relationship between update invocation and rendered-frame cadence",
        },
        {
            "id": "upper-object-lifecycle",
            "evidence_state": "ambiguous",
            "addresses": [UPSTREAM_OWNER, UPSTREAM_BATCH, *DIRECT_CALLERS],
            "required_evidence": "constructor/vtable/destructor or registration evidence that closes object identity without relying on callgraph adjacency",
        },
    ]

    target_plan = [
        {
            "address": DIRECT_CALLERS[1],
            "priority": 0,
            "exports": ["references", "instructions+pcode", "vtable/static-table references"],
            "reason": "resolve the direct-incoming-call gap without treating the function as a root",
        },
        {
            "address": UPSTREAM_OWNER,
            "priority": 1,
            "exports": ["callers", "instructions+pcode", "strings", "constructor/vtable references"],
            "reason": "extend ownership/lifecycle proof above the verified batch path",
        },
        {
            "address": UPSTREAM_BATCH,
            "priority": 1,
            "exports": ["instructions+pcode", "caller argument provenance"],
            "reason": "trace source values feeding the two 64-bit channels and child +0x340 object",
        },
        {
            "address": DIRECT_CALLERS[0],
            "priority": 2,
            "exports": ["instructions+pcode", "caller argument provenance"],
            "reason": "tie the verified channel stores to an upstream owner/input source",
        },
    ]

    return {
        "format": FORMAT,
        "inputs": {
            "body_schedule": str(body_schedule_path),
            "caller_frontier": str(caller_frontier_path),
            "outer_callsite": str(outer_callsite_path),
        },
        "anchors": {
            "outer_update": OUTER_UPDATE,
            "physics_pass": PHYSICS_PASS,
            "half_step_orchestrator": HALF_STEP_ORCHESTRATOR,
            "body_array_loop": BODY_ARRAY_LOOP,
            "body_integrator": BODY_INTEGRATOR,
            "outer_receiver": OUTER_RECEIVER,
        },
        "closure": {
            "persistent_body_motion_path": "proven",
            "outer_update_call_abi": "verified",
            "upper_direct_call_path": "verified",
            "input_control_ownership": "unknown",
            "alternate_caller_owner": "unknown",
            "rendered_frame_cadence": "unknown",
            "body_integrator_native_handoff_ready": True,
            "full_input_to_next_frame_handoff_ready": False,
        },
        "graph": graph,
        "candidates": candidates,
        "blockers": blockers,
        "targeted_export_plan": target_plan,
        "targeted_export_addresses": [row["address"] for row in target_plan],
        "scope": {
            "evidence_states": sorted(EVIDENCE_STATES),
            "callgraph_adjacency_is_semantic_role": False,
            "offset_pattern_is_object_identity": False,
            "pointer_similarity_is_ownership": False,
            "rendered_frame_schedule_inferred": False,
            "physical_units_inferred": False,
            "semantic_renames_performed": False,
            "original_game_execution_required": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("body_schedule", type=Path)
    parser.add_argument("caller_frontier", type=Path)
    parser.add_argument("outer_callsite", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--targets-out", type=Path)
    args = parser.parse_args()

    report = build_persistent_vehicle_state_closure(
        args.body_schedule, args.caller_frontier, args.outer_callsite
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    if args.targets_out:
        args.targets_out.parent.mkdir(parents=True, exist_ok=True)
        args.targets_out.write_text(
            "".join(address + "\n" for address in report["targeted_export_addresses"]),
            encoding="utf-8",
        )

    print(f"format: {report['format']}")
    print(f"persistent BODY motion path: {report['closure']['persistent_body_motion_path']}")
    print(f"candidate functions: {len(report['candidates'])}")
    print(f"remaining blockers: {len(report['blockers'])}")
    if args.json_out:
        print(f"output: {args.json_out}")
    if args.targets_out:
        print(f"targets: {args.targets_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
