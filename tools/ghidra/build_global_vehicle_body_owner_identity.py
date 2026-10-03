#!/usr/bin/env python3
"""Compose the proven global vehicle base, BODY-owner receiver and BMW chassis.

This is the semantic composition step after the local FUN_00765470 receiver
proof. It deliberately does not re-prove machine instructions and does not use
the obsolete *record+0x340 == vehicle-base requirement.

A positive result requires all three independent inputs:

* SHIFT.GlobalVehicleComponentBaseIdentity/1
* SHIFT.Fun00765470BodyOwnerReceiverProvenance/1
* SHIFT.BMWChassisBodyIdentityFrontier/1

Only then may the existing Phase 698/700 BODY-pose path select retail BMW BODY 0.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.GlobalVehicleBodyOwnerIdentity/1"
GLOBAL_FORMAT = "SHIFT.GlobalVehicleComponentBaseIdentity/1"
RECEIVER_FORMAT = "SHIFT.Fun00765470BodyOwnerReceiverProvenance/1"
CHASSIS_FORMAT = "SHIFT.BMWChassisBodyIdentityFrontier/1"
GLOBAL_VEHICLE_ADDRESS = 0x00C13700
CHASSIS_BODY_INDEX = 0


def _load(path: Path, expected: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("format") != expected:
        raise ValueError(f"{path}: expected {expected}")
    return value


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _int(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError(f"invalid integer: {value!r}")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 0)
    raise ValueError(f"invalid integer: {value!r}")


def build_global_vehicle_body_owner_identity(
    global_vehicle_identity_path: Path,
    body_owner_receiver_path: Path,
    chassis_identity_path: Path,
) -> dict[str, Any]:
    global_identity = _load(global_vehicle_identity_path, GLOBAL_FORMAT)
    receiver = _load(body_owner_receiver_path, RECEIVER_FORMAT)
    chassis = _load(chassis_identity_path, CHASSIS_FORMAT)

    global_join = global_identity.get("identity_join") or {}
    global_handoff = global_identity.get("handoff") or {}
    global_scope = global_identity.get("scope") or {}

    _require(
        global_join.get("global_outer_receiver_is_vehicle_component_base") is True,
        "global outer receiver is not proven as vehicle component base",
    )
    _require(
        global_join.get("same_numeric_address") is True,
        "global outer/vehicle numeric address equality is not proven",
    )
    outer_address = _int(global_join.get("outer_update_receiver_address"))
    component_address = _int(global_join.get("runtime_component_vehicle_base_address"))
    _require(
        outer_address == GLOBAL_VEHICLE_ADDRESS
        and component_address == GLOBAL_VEHICLE_ADDRESS,
        "global vehicle address drift",
    )
    _require(
        global_handoff.get("global_vehicle_component_base_identity_ready") is True,
        "global vehicle component identity is not ready",
    )
    _require(
        global_handoff.get("update_child_to_vehicle_base_equality_required") is False,
        "obsolete update-child equality requirement was reintroduced",
    )
    _require(
        global_handoff.get("update_child_to_vehicle_base_equality_proven") is False,
        "global identity input preclaims update-child equality",
    )
    _require(
        global_handoff.get("outer_receiver_to_BODY_owner_continuity_proven") is False,
        "global identity input preclaims BODY-owner continuity",
    )
    _require(
        global_handoff.get("vehicle_BODY_selection_ready") is False,
        "global identity input preclaims vehicle BODY selection",
    )
    _require(
        global_handoff.get("phase698_positive_selection_admissible") is False,
        "global identity input preclaims Phase 698 admission",
    )
    _require(
        global_scope.get("BODY_array_owner_equals_global_vehicle_base_proven") is False,
        "global identity scope preclaims BODY owner equality",
    )

    selection = chassis.get("selection") or {}
    chassis_handoff = chassis.get("handoff") or {}
    _require(
        selection.get("main_chassis_BODY_selected") is True,
        "BMW main chassis BODY is not selected",
    )
    _require(
        selection.get("selected_BODY_name") == "body",
        "BMW chassis BODY name drift",
    )
    _require(
        _int(selection.get("selected_BODY_index")) == CHASSIS_BODY_INDEX,
        "BMW chassis BODY index drift",
    )
    _require(
        chassis_handoff.get("main_chassis_BODY_selected") is True
        and _int(chassis_handoff.get("main_chassis_BODY_index")) == CHASSIS_BODY_INDEX,
        "BMW chassis handoff drift",
    )
    _require(
        chassis_handoff.get("vehicle_BODY_selection_ready") is False,
        "chassis identity input preclaims vehicle BODY selection",
    )
    _require(
        chassis_handoff.get("phase698_positive_selection_admissible") is False,
        "chassis identity input preclaims Phase 698 admission",
    )

    analysis = receiver.get("analysis") or {}
    receiver_handoff = receiver.get("handoff") or {}
    receiver_blockers = receiver.get("blockers")
    if not isinstance(receiver_blockers, list):
        raise ValueError("BODY-owner receiver blockers must be a list")

    receiver_origins = analysis.get("receiver_origins_before_body_loop_call")
    if not isinstance(receiver_origins, list) or any(
        not isinstance(value, str) for value in receiver_origins
    ):
        raise ValueError("BODY-owner receiver origin list is invalid")

    local_receiver_proven = receiver_handoff.get(
        "half_step_entry_ECX_to_BODY_array_owner_ECX_continuity_proven"
    )
    composition_ready = receiver_handoff.get(
        "global_vehicle_to_BODY_owner_composition_ready"
    )
    phase703_rewrite_ready = receiver_handoff.get("phase703_gate_rewrite_ready")
    artifact_alone_admits = receiver_handoff.get(
        "phase698_positive_selection_admissible_by_this_artifact_alone"
    )

    _require(isinstance(local_receiver_proven, bool), "receiver continuity flag missing")
    _require(isinstance(composition_ready, bool), "receiver composition-ready flag missing")
    _require(isinstance(phase703_rewrite_ready, bool), "Phase 703 rewrite flag missing")
    _require(
        artifact_alone_admits is False,
        "local receiver artifact incorrectly claims Phase 698 admission alone",
    )
    _require(
        local_receiver_proven == composition_ready == phase703_rewrite_ready,
        "BODY-owner receiver handoff flags disagree",
    )

    if local_receiver_proven:
        _require(
            receiver_origins == ["entry:ECX"],
            "positive BODY-owner receiver proof does not resolve uniquely to entry:ECX",
        )
        _require(
            analysis.get(
                "receiver_equals_half_step_entry_ECX_on_all_reachable_paths"
            )
            is True,
            "positive BODY-owner receiver proof is not all-path",
        )
        _require(
            analysis.get("receiver_provenance_ambiguous") is False,
            "positive BODY-owner receiver proof is marked ambiguous",
        )
        _require(receiver_blockers == [], "positive BODY-owner receiver report has blockers")

    identity_ready = bool(local_receiver_proven)
    blockers: list[dict[str, Any]] = []
    if not identity_ready:
        blockers.append(
            {
                "id": "half-step-entry-receiver-to-BODY-array-owner",
                "evidence_state": "blocked",
                "required_contract": RECEIVER_FORMAT,
                "required_result": (
                    "half_step_entry_ECX_to_BODY_array_owner_ECX_continuity_proven=true"
                ),
                "upstream_blockers": receiver_blockers,
            }
        )

    return {
        "format": FORMAT,
        "inputs": {
            "global_vehicle_component_base_identity": str(global_vehicle_identity_path),
            "half_step_BODY_owner_receiver": str(body_owner_receiver_path),
            "BMW_chassis_BODY_identity": str(chassis_identity_path),
        },
        "identity_join": {
            "global_vehicle_address": f"0x{GLOBAL_VEHICLE_ADDRESS:08x}",
            "global_vehicle_component_base_identity_ready": True,
            "half_step_entry_ECX_to_BODY_array_owner_ECX_continuity_proven": identity_ready,
            "BODY_array_owner_is_global_vehicle_base": identity_ready,
            "main_chassis_BODY_selected": True,
            "main_chassis_BODY_name": "body",
            "main_chassis_BODY_index": CHASSIS_BODY_INDEX,
            "global_vehicle_BODY_owner_identity_ready": identity_ready,
            "evidence_state": "proven-composed-static" if identity_ready else "blocked",
        },
        "handoff": {
            "outer_receiver_to_BODY_owner_continuity_proven": identity_ready,
            "vehicle_BODY_selection_ready": identity_ready,
            "selected_BODY_index": CHASSIS_BODY_INDEX if identity_ready else None,
            "phase698_positive_selection_admissible": identity_ready,
            "phase700_runtime_handoff_admissible": identity_ready,
            "phase703_update_child_equality_gate_required": False,
            "phase703_gate_rewrite_ready": identity_ready,
            "vehicle_world_transform_ready": False,
            "critical_next_join": (
                "BODY0 pose frame -> Phase 645 VHF vehicle-root/body-MEB bind-frame composition"
                if identity_ready
                else "FUN_00765470 entry ECX -> FUN_007b2270 BODY-array owner ECX"
            ),
        },
        "blockers": blockers,
        "scope": {
            "update_child_pointer_equals_global_vehicle_base_proven": False,
            "update_child_pointer_equality_required": False,
            "callgraph_adjacency_used_as_object_identity": False,
            "BODY_name_plausibility_used_as_chassis_proof": False,
            "renderer_bind_frame_consumed": False,
            "dynamic_BODY_pose_to_VHF_composition_proven": False,
            "fixed_step_auto_schedule_proven": False,
            "original_game_executed": False,
            "new_runtime_capture_required": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("global_vehicle_identity", type=Path)
    parser.add_argument("body_owner_receiver", type=Path)
    parser.add_argument("chassis_identity", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = build_global_vehicle_body_owner_identity(
        args.global_vehicle_identity,
        args.body_owner_receiver,
        args.chassis_identity,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    print(
        "vehicle BODY selection ready: "
        f"{report['handoff']['vehicle_BODY_selection_ready']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
