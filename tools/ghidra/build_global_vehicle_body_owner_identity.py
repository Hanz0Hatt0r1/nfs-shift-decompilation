#!/usr/bin/env python3
"""Compose global vehicle base, BODY-owner provenance and BMW chassis BODY.

The public output stays SHIFT.GlobalVehicleBodyOwnerIdentity/1. Two static input
forms are accepted for compatibility:

* the original direct-receiver contract, where FUN_007b2270 ECX may equal the
  FUN_00765470 entry ECX on every path;
* the retail field-provenance contract, which proves the actual machine edge
  entry ECX -> [entry ECX + 0x339c] -> FUN_007b2270 receiver.

The second form deliberately does not equate the vehicle-base pointer with the
BODY-array owner pointer.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.GlobalVehicleBodyOwnerIdentity/1"
GLOBAL_FORMAT = "SHIFT.GlobalVehicleComponentBaseIdentity/1"
RECEIVER_FORMAT = "SHIFT.Fun00765470BodyOwnerReceiverProvenance/1"
FIELD_FORMAT = "SHIFT.Fun00765470BodyOwnerFieldProvenance/1"
CHASSIS_FORMAT = "SHIFT.BMWChassisBodyIdentityFrontier/1"
GLOBAL_VEHICLE_ADDRESS = 0x00C13700
BODY_OWNER_FIELD_OFFSET = "0x339c"
CHASSIS_BODY_INDEX = 0


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _load(path: Path, expected: str) -> dict[str, Any]:
    value = _read(path)
    if value.get("format") != expected:
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


def _validate_global_identity(global_identity: dict[str, Any]) -> None:
    join = global_identity.get("identity_join") or {}
    handoff = global_identity.get("handoff") or {}
    scope = global_identity.get("scope") or {}
    _require(join.get("global_outer_receiver_is_vehicle_component_base") is True, "global outer receiver is not proven as vehicle component base")
    _require(join.get("same_numeric_address") is True, "global outer/vehicle numeric address equality is not proven")
    _require(
        _int(join.get("outer_update_receiver_address")) == GLOBAL_VEHICLE_ADDRESS
        and _int(join.get("runtime_component_vehicle_base_address")) == GLOBAL_VEHICLE_ADDRESS,
        "global vehicle address drift",
    )
    _require(handoff.get("global_vehicle_component_base_identity_ready") is True, "global vehicle component identity is not ready")
    _require(handoff.get("update_child_to_vehicle_base_equality_required") is False, "obsolete update-child equality requirement was reintroduced")
    _require(handoff.get("update_child_to_vehicle_base_equality_proven") is False, "global identity input preclaims update-child equality")
    _require(handoff.get("outer_receiver_to_BODY_owner_continuity_proven") is False, "global identity input preclaims BODY-owner continuity")
    _require(handoff.get("vehicle_BODY_selection_ready") is False, "global identity input preclaims vehicle BODY selection")
    _require(handoff.get("phase698_positive_selection_admissible") is False, "global identity input preclaims Phase 698 admission")
    _require(scope.get("BODY_array_owner_equals_global_vehicle_base_proven") is False, "global identity scope preclaims BODY owner equality")


def _validate_chassis(chassis: dict[str, Any]) -> None:
    selection = chassis.get("selection") or {}
    handoff = chassis.get("handoff") or {}
    _require(selection.get("main_chassis_BODY_selected") is True, "BMW main chassis BODY is not selected")
    _require(selection.get("selected_BODY_name") == "body", "BMW chassis BODY name drift")
    _require(_int(selection.get("selected_BODY_index")) == CHASSIS_BODY_INDEX, "BMW chassis BODY index drift")
    _require(
        handoff.get("main_chassis_BODY_selected") is True
        and _int(handoff.get("main_chassis_BODY_index")) == CHASSIS_BODY_INDEX,
        "BMW chassis handoff drift",
    )
    _require(handoff.get("vehicle_BODY_selection_ready") is False, "chassis identity input preclaims vehicle BODY selection")
    _require(handoff.get("phase698_positive_selection_admissible") is False, "chassis identity input preclaims Phase 698 admission")


def _receiver_status(value: dict[str, Any]) -> tuple[bool, bool, bool, str | None, list[dict[str, Any]]]:
    analysis = value.get("analysis") or {}
    handoff = value.get("handoff") or {}
    blockers = value.get("blockers")
    if not isinstance(blockers, list):
        raise ValueError("BODY-owner receiver blockers must be a list")
    origins = analysis.get("receiver_origins_before_body_loop_call")
    if not isinstance(origins, list) or any(not isinstance(item, str) for item in origins):
        raise ValueError("BODY-owner receiver origin list is invalid")

    direct = handoff.get("half_step_entry_ECX_to_BODY_array_owner_ECX_continuity_proven")
    compose = handoff.get("global_vehicle_to_BODY_owner_composition_ready")
    rewrite = handoff.get("phase703_gate_rewrite_ready")
    alone = handoff.get("phase698_positive_selection_admissible_by_this_artifact_alone")
    _require(isinstance(direct, bool), "receiver continuity flag missing")
    _require(isinstance(compose, bool), "receiver composition-ready flag missing")
    _require(isinstance(rewrite, bool), "Phase 703 rewrite flag missing")
    _require(alone is False, "local receiver artifact incorrectly claims Phase 698 admission alone")
    _require(direct == compose == rewrite, "BODY-owner receiver handoff flags disagree")

    if direct:
        _require(origins == ["entry:ECX"], "positive BODY-owner receiver proof does not resolve uniquely to entry:ECX")
        _require(analysis.get("receiver_equals_half_step_entry_ECX_on_all_reachable_paths") is True, "positive BODY-owner receiver proof is not all-path")
        _require(analysis.get("receiver_provenance_ambiguous") is False, "positive BODY-owner receiver proof is marked ambiguous")
        _require(blockers == [], "positive BODY-owner receiver report has blockers")
    return bool(direct), bool(direct), False, None, blockers


def _field_status(value: dict[str, Any]) -> tuple[bool, bool, bool, str | None, list[dict[str, Any]]]:
    machine = value.get("machine_edge") or {}
    handoff = value.get("handoff") or {}
    blockers = value.get("blockers")
    _require(blockers == [], "BODY-owner field proof still has blockers")
    _require(machine.get("entry_receiver_to_BODY_owner_pointer_field_edge_proven") is True, "BODY-owner field edge is not proven")
    _require(machine.get("entry_receiver_equals_call_receiver_pointer") is False, "BODY-owner field proof incorrectly claims pointer equality")
    _require(machine.get("BODY_owner_pointer_field_offset") == BODY_OWNER_FIELD_OFFSET, "BODY-owner field offset drift")
    _require(machine.get("BODY_owner_pointer_expression") == "dword ptr [entry:ECX + 0x339c]", "BODY-owner field expression drift")
    _require(handoff.get("half_step_entry_ECX_to_BODY_array_owner_field_continuity_proven") is True, "BODY-owner field continuity is not proven")
    _require(handoff.get("BODY_array_owner_pointer_field_offset") == BODY_OWNER_FIELD_OFFSET, "BODY-owner field handoff offset drift")
    _require(handoff.get("global_vehicle_to_BODY_owner_composition_ready") is True, "BODY-owner field proof is not composition-ready")
    _require(handoff.get("phase703_gate_rewrite_ready") is True, "BODY-owner field proof is not Phase 703-ready")
    _require(handoff.get("phase698_positive_selection_admissible_by_this_artifact_alone") is False, "BODY-owner field proof incorrectly admits Phase 698 alone")
    return True, False, True, BODY_OWNER_FIELD_OFFSET, []


def build_global_vehicle_body_owner_identity(
    global_vehicle_identity_path: Path,
    body_owner_provenance_path: Path,
    chassis_identity_path: Path,
) -> dict[str, Any]:
    global_identity = _load(global_vehicle_identity_path, GLOBAL_FORMAT)
    provenance = _read(body_owner_provenance_path)
    chassis = _load(chassis_identity_path, CHASSIS_FORMAT)
    _validate_global_identity(global_identity)
    _validate_chassis(chassis)

    provenance_format = provenance.get("format")
    if provenance_format == RECEIVER_FORMAT:
        identity_ready, owner_equals_base, field_continuity, field_offset, upstream_blockers = _receiver_status(provenance)
    elif provenance_format == FIELD_FORMAT:
        identity_ready, owner_equals_base, field_continuity, field_offset, upstream_blockers = _field_status(provenance)
    else:
        raise ValueError(f"{body_owner_provenance_path}: expected {RECEIVER_FORMAT} or {FIELD_FORMAT}")

    blockers: list[dict[str, Any]] = []
    if not identity_ready:
        blockers.append(
            {
                "id": "half-step-entry-receiver-to-BODY-array-owner",
                "evidence_state": "blocked",
                "required_contract": FIELD_FORMAT,
                "required_result": "half_step_entry_ECX_to_BODY_array_owner_field_continuity_proven=true",
                "upstream_blockers": upstream_blockers,
            }
        )

    return {
        "format": FORMAT,
        "inputs": {
            "global_vehicle_component_base_identity": str(global_vehicle_identity_path),
            "half_step_BODY_owner_provenance": str(body_owner_provenance_path),
            "half_step_BODY_owner_provenance_format": provenance_format,
            "BMW_chassis_BODY_identity": str(chassis_identity_path),
        },
        "identity_join": {
            "global_vehicle_address": f"0x{GLOBAL_VEHICLE_ADDRESS:08x}",
            "global_vehicle_component_base_identity_ready": True,
            "half_step_entry_ECX_to_BODY_array_owner_ECX_continuity_proven": identity_ready and owner_equals_base,
            "half_step_entry_ECX_to_BODY_array_owner_field_continuity_proven": identity_ready and field_continuity,
            "BODY_array_owner_is_global_vehicle_base": identity_ready and owner_equals_base,
            "BODY_array_owner_pointer_loaded_from_global_vehicle_base": identity_ready and field_continuity,
            "BODY_array_owner_pointer_field_offset": field_offset if identity_ready else None,
            "main_chassis_BODY_selected": True,
            "main_chassis_BODY_name": "body",
            "main_chassis_BODY_index": CHASSIS_BODY_INDEX,
            "global_vehicle_BODY_owner_identity_ready": identity_ready,
            "evidence_state": (
                "proven-composed-static-field" if identity_ready and field_continuity
                else "proven-composed-static" if identity_ready
                else "blocked"
            ),
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
                "BODY0 bind initialization/writer provenance -> SHIFT.BMWBody0BindFrameProof/1"
                if identity_ready
                else "FUN_00765470 vehicle-base +0x339c BODY-owner pointer field provenance"
            ),
        },
        "blockers": blockers,
        "scope": {
            "update_child_pointer_equals_global_vehicle_base_proven": False,
            "update_child_pointer_equality_required": False,
            "callgraph_adjacency_used_as_object_identity": False,
            "BODY_name_plausibility_used_as_chassis_proof": False,
            "BODY_array_owner_pointer_equals_global_vehicle_base_proven": identity_ready and owner_equals_base,
            "BODY_array_owner_pointer_field_edge_proven": identity_ready and field_continuity,
            "BODY_array_owner_pointer_field_offset": field_offset if identity_ready else None,
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
    parser.add_argument("body_owner_provenance", type=Path)
    parser.add_argument("chassis_identity", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    report = build_global_vehicle_body_owner_identity(
        args.global_vehicle_identity,
        args.body_owner_provenance,
        args.chassis_identity,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    print(f"vehicle BODY selection ready: {report['handoff']['vehicle_BODY_selection_ready']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
