#!/usr/bin/env python3
"""Separate the static pointer domains between vehicle lifetime and BODY pose.

This is a composition contract for the first playable Linux vertical-slice
identity blocker.  It deliberately does *not* turn the vehicle/update caller,
the fixed outer-physics receiver, or the BODY-array owner into the same object.
Instead it records which pointer/value transfers are already source/static
backed and emits the exact missing joins needed before a persistent BODY pose can
be used as a concrete vehicle world transform.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.VehicleBodyIdentityFrontier/1"
LIFETIME_FORMAT = "SHIFT.VehicleLifetimeMemoryBridge/1"
OUTER_FORMAT = "SHIFT.OuterUpdateCallsiteStatic/1"
PERSISTENT_FORMAT = "SHIFT.PersistentVehicleStateClosure/1"
BODY_FORMAT = "SHIFT.BodyFrameIntegrationStatic/1"

OUTER_UPDATE = "0x00770e80"
HALF_STEP = "0x00765470"
BODY_ARRAY_LOOP = "0x007b2270"
BODY_INTEGRATOR = "0x007bab70"
UPSTREAM_BATCH = "0x00713050"
FIRST_CALLER = "0x00794a30"
OUTER_RECEIVER = "DAT_00c13700"


def _load(path: Path, expected: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}")
    return value


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _hex(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError(f"expected hexadecimal string, got {value!r}")
    return f"0x{int(value, 0):x}"


def _lifetime_domains(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows = report.get("create_bridges")
    if not isinstance(rows, list) or not rows:
        raise ValueError("lifetime bridge has no create bridges")
    domains: list[dict[str, Any]] = []
    seen: set[tuple[Any, Any, Any]] = set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("descriptor"), int):
            raise ValueError("lifetime bridge contains invalid create bridge")
        key = (
            row.get("descriptor"),
            row.get("vehicle_pointer_function"),
            row.get("vehicle_pointer_source_node"),
        )
        if key in seen:
            raise ValueError("duplicate persistent vehicle pointer domain")
        seen.add(key)
        _require(
            row.get("same_runtime_object_as_vehicle_update_proven") is False,
            "lifetime bridge unexpectedly preclaims vehicle-update identity",
        )
        domains.append(
            {
                "descriptor": row["descriptor"],
                "class_name": row.get("class_name"),
                "vehicle_pointer_function": row.get("vehicle_pointer_function"),
                "vehicle_pointer_source_node": row.get("vehicle_pointer_source_node"),
                "stored_table_address": row.get("stored_table_address"),
                "domain_role": "persistent-lifetime-vehicle-pointer-frontier",
                "evidence_state": "verified",
                "same_runtime_object_as_update_child_state": "unknown",
                "same_runtime_object_as_BODY_state": "unknown",
            }
        )
    return sorted(domains, key=lambda row: row["descriptor"])


def build_vehicle_body_identity_frontier(
    lifetime_bridge_path: Path,
    outer_callsite_path: Path,
    persistent_closure_path: Path,
    body_integration_path: Path,
) -> dict[str, Any]:
    lifetime = _load(lifetime_bridge_path, LIFETIME_FORMAT)
    outer = _load(outer_callsite_path, OUTER_FORMAT)
    persistent = _load(persistent_closure_path, PERSISTENT_FORMAT)
    body = _load(body_integration_path, BODY_FORMAT)

    lifetime_domains = _lifetime_domains(lifetime)
    _require(
        (lifetime.get("scope") or {}).get("same_runtime_object_as_vehicle_update_proven")
        is False,
        "lifetime bridge scope unexpectedly preclaims vehicle-update identity",
    )

    outer_row = outer.get("outer_update")
    batch = outer.get("upstream_batch_path")
    direct = outer.get("direct_callsites")
    scope = outer.get("scope")
    _require(isinstance(outer_row, dict), "outer callsite outer_update missing")
    _require(isinstance(batch, dict), "outer callsite upstream_batch_path missing")
    _require(isinstance(direct, list), "outer callsite direct_callsites missing")
    _require(isinstance(scope, dict), "outer callsite scope missing")
    _require(outer_row.get("function") == OUTER_UPDATE, "outer-update anchor drift")
    _require(
        outer_row.get("receiver_at_callsites") == OUTER_RECEIVER,
        "outer-update receiver drift",
    )
    _require(batch.get("function") == UPSTREAM_BATCH, "update batch anchor drift")
    _require(
        _hex(batch.get("child_object_pointer_adjustment")) == "0x340",
        "update child pointer adjustment drift",
    )
    _require(
        batch.get("first_caller_source_call_count") == 3,
        "update child call count drift",
    )
    _require(scope.get("vehicle_class_identity_proven") is False, "outer contract unexpectedly preclaims vehicle class identity")

    first_rows = [
        row for row in direct
        if isinstance(row, dict) and row.get("caller") == FIRST_CALLER
    ]
    if len(first_rows) != 1:
        raise ValueError("expected exactly one first-caller outer callsite row")
    first = first_rows[0]
    _require(
        first.get("channels_written_from_function_arguments_before_call") is True,
        "first caller no longer proves channel stores before outer update",
    )
    _require(first.get("promoted") is False, "first caller unexpectedly promoted")

    anchors = persistent.get("anchors")
    closure = persistent.get("closure")
    persistent_scope = persistent.get("scope")
    _require(isinstance(anchors, dict), "persistent closure anchors missing")
    _require(isinstance(closure, dict), "persistent closure state missing")
    _require(isinstance(persistent_scope, dict), "persistent closure scope missing")
    expected_anchors = {
        "outer_update": OUTER_UPDATE,
        "half_step_orchestrator": HALF_STEP,
        "body_array_loop": BODY_ARRAY_LOOP,
        "body_integrator": BODY_INTEGRATOR,
        "outer_receiver": OUTER_RECEIVER,
    }
    for key, expected in expected_anchors.items():
        _require(anchors.get(key) == expected, f"persistent closure {key} drift")
    _require(
        closure.get("persistent_body_motion_path") == "proven",
        "persistent BODY motion path is not proven",
    )
    _require(
        persistent_scope.get("offset_pattern_is_object_identity") is False,
        "persistent closure unexpectedly treats offsets as object identity",
    )

    functions = body.get("functions")
    closed = body.get("closed_boundaries")
    _require(isinstance(functions, dict), "BODY integration functions missing")
    _require(isinstance(closed, dict), "BODY integration closed_boundaries missing")
    loop = functions.get("FUN_007b2270")
    integrator = functions.get("FUN_007bab70")
    half = functions.get("FUN_00765470")
    _require(isinstance(loop, dict), "BODY array-loop contract missing")
    _require(isinstance(integrator, dict), "BODY integrator contract missing")
    _require(isinstance(half, dict), "half-step contract missing")
    _require(loop.get("address") == BODY_ARRAY_LOOP, "BODY array-loop address drift")
    _require(integrator.get("address") == BODY_INTEGRATOR, "BODY integrator address drift")
    _require(half.get("address") == HALF_STEP, "half-step address drift")
    _require(loop.get("body_count_offset") == "0x10", "BODY count offset drift")
    _require(loop.get("body_array_offset") == "0x14", "BODY array offset drift")
    _require(loop.get("body_stride") == "0x170", "BODY stride drift")
    _require(closed.get("body_array_stride_and_count") is True, "BODY array topology not proven")

    pointer_domains = {
        "lifetime_vehicle_pointers": lifetime_domains,
        "update_child_receiver": {
            "producer": UPSTREAM_BATCH,
            "consumer": FIRST_CALLER,
            "source_rule": "*record + 0x340",
            "record_pointer_array_offset": batch.get("record_pointer_array_offset"),
            "record_count_offset": batch.get("record_count_offset"),
            "record_stride": batch.get("record_stride"),
            "evidence_state": "verified",
            "class_identity_state": "unknown",
        },
        "outer_physics_receiver": {
            "consumer": OUTER_UPDATE,
            "source_expression": "&DAT_00c13700",
            "symbol": OUTER_RECEIVER,
            "evidence_state": "verified",
            "semantic_class_identity_state": "unknown",
        },
        "body_array_owner": {
            "consumer": BODY_ARRAY_LOOP,
            "count_offset": "0x10",
            "array_pointer_offset": "0x14",
            "body_stride": "0x170",
            "persistent_writer": BODY_INTEGRATOR,
            "topology_evidence_state": "proven",
            "pointer_identity_with_outer_receiver_state": "unknown",
            "semantic_class_identity_state": "unknown",
        },
    }

    transfer_facts = [
        {
            "from": "update_child_receiver",
            "to": "outer_physics_receiver",
            "relation": "outer-call receiver expression",
            "evidence_state": "verified",
            "pointer_forwarded": False,
            "fact": (
                "the source-backed FUN_00794a30 outer call uses &DAT_00c13700 as "
                "the FUN_00770e80 receiver; caller object values are forwarded through "
                "the two 64-bit channel arguments instead"
            ),
            "runtime_pointer_inequality_proven": False,
        },
        {
            "from": "update_child_receiver",
            "to": "outer_physics_receiver",
            "relation": "two 64-bit channel values",
            "evidence_state": "verified",
            "pointer_identity_transfer": False,
            "channel_a": {
                "caller_offset": first.get("caller_channel_a_offset"),
                "outer_receiver_offset": outer_row.get("channel_a_receiver_offset"),
            },
            "channel_b": {
                "caller_offset": first.get("caller_channel_b_offset"),
                "outer_receiver_offset": outer_row.get("channel_b_receiver_offset"),
            },
        },
        {
            "from": "outer_physics_receiver",
            "to": "body_array_owner",
            "relation": "half-step/BODY-array receiver continuity",
            "evidence_state": "unknown",
            "known_schedule": f"{OUTER_UPDATE} -> {HALF_STEP} -> {BODY_ARRAY_LOOP}",
            "required_evidence": (
                "exact source or machine pointer provenance through FUN_00765470 into "
                "the receiver used by FUN_007b2270"
            ),
        },
        {
            "from": "lifetime_vehicle_pointers",
            "to": "update_child_receiver",
            "relation": "same-runtime-object continuity",
            "evidence_state": "unknown",
            "required_evidence": (
                "pointer-value continuity, persistent field/registration evidence, or an "
                "independently identified owner relation joining the lifetime pointer to "
                "the *record+0x340 update child"
            ),
        },
        {
            "from": "update_child_receiver",
            "to": "BODY element",
            "relation": "BODY index/pointer ownership",
            "evidence_state": "unknown",
            "required_evidence": (
                "an exact BODY index/pointer field, registration call, lifecycle setter, or "
                "other static pointer-value transfer into the +0x14/0x170 BODY array"
            ),
        },
    ]

    blockers = [
        {
            "id": "lifetime-vehicle-pointer-to-update-child-identity",
            "evidence_state": "unknown",
            "priority": 1,
            "targets": sorted(
                {
                    str(row.get("vehicle_pointer_function"))
                    for row in lifetime_domains
                    if row.get("vehicle_pointer_function")
                }
                | {UPSTREAM_BATCH, FIRST_CALLER}
            ),
        },
        {
            "id": "update-child-to-BODY-index-or-pointer",
            "evidence_state": "unknown",
            "priority": 0,
            "targets": [UPSTREAM_BATCH, FIRST_CALLER, HALF_STEP, BODY_ARRAY_LOOP],
            "required_evidence": "source/static-backed index or pointer continuity selecting one BODY element",
        },
        {
            "id": "outer-receiver-to-BODY-array-owner-continuity",
            "evidence_state": "unknown",
            "priority": 0,
            "targets": [HALF_STEP, BODY_ARRAY_LOOP],
            "required_evidence": "exact receiver provenance at the FUN_00765470 -> FUN_007b2270 callsite",
        },
        {
            "id": "vehicle-world-transform-mapping",
            "evidence_state": "blocked",
            "priority": 0,
            "blocked_by": "update-child-to-BODY-index-or-pointer",
            "required_evidence": "identified vehicle BODY plus a proven BODY-origin/basis -> vehicle-world transform convention",
        },
    ]

    next_targets = sorted(
        {target for row in blockers if row["priority"] == 0 for target in row.get("targets", [])},
        key=lambda value: int(value, 0),
    )

    return {
        "format": FORMAT,
        "inputs": {
            "vehicle_lifetime_memory_bridge": str(lifetime_bridge_path),
            "outer_update_callsite": str(outer_callsite_path),
            "persistent_vehicle_state_closure": str(persistent_closure_path),
            "body_frame_integration": str(body_integration_path),
        },
        "pointer_domains": pointer_domains,
        "transfer_facts": transfer_facts,
        "blockers": blockers,
        "next_instruction_targets": next_targets,
        "handoff": {
            "persistent_BODY_pose_available": True,
            "vehicle_BODY_selection_ready": False,
            "selected_BODY_index": None,
            "selected_BODY_pointer": None,
            "vehicle_world_transform_ready": False,
            "renderer_vehicle_transform_transport_ready": False,
            "critical_next_join": "update_child_receiver -> BODY index/pointer",
        },
        "scope": {
            "normal_outer_call_forwards_vehicle_receiver_pointer": False,
            "normal_outer_call_forwards_vehicle_channel_values": True,
            "runtime_pointer_inequality_between_update_child_and_outer_receiver_proven": False,
            "outer_receiver_to_BODY_owner_pointer_continuity_proven": False,
            "lifetime_pointer_to_update_child_identity_proven": False,
            "update_child_to_BODY_identity_proven": False,
            "vehicle_world_transform_mapping_proven": False,
            "callgraph_adjacency_is_object_identity": False,
            "matching_offsets_are_object_identity": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
            "note": (
                "The source-backed normal update path replaces the update-child receiver with "
                "the fixed &DAT_00c13700 outer receiver and transfers two 64-bit values, not a "
                "proven vehicle pointer. BODY selection therefore requires a separate static "
                "vehicle/update-object -> BODY index/pointer relationship."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vehicle_lifetime_memory_bridge", type=Path)
    parser.add_argument("outer_update_callsite", type=Path)
    parser.add_argument("persistent_vehicle_state_closure", type=Path)
    parser.add_argument("body_frame_integration", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--targets-out", type=Path)
    args = parser.parse_args()

    report = build_vehicle_body_identity_frontier(
        args.vehicle_lifetime_memory_bridge,
        args.outer_update_callsite,
        args.persistent_vehicle_state_closure,
        args.body_frame_integration,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    if args.targets_out:
        args.targets_out.parent.mkdir(parents=True, exist_ok=True)
        args.targets_out.write_text(
            "".join(address + "\n" for address in report["next_instruction_targets"]),
            encoding="utf-8",
        )
    print(f"format: {report['format']}")
    print(f"vehicle BODY selection ready: {report['handoff']['vehicle_BODY_selection_ready']}")
    print(f"critical next join: {report['handoff']['critical_next_join']}")
    print(f"next instruction targets: {len(report['next_instruction_targets'])}")
    if args.json_out:
        print(f"json: {args.json_out}")
    if args.targets_out:
        print(f"targets: {args.targets_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
