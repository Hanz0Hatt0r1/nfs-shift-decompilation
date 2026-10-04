#!/usr/bin/env python3
"""Promote GlobalVehicleBodyOwnerIdentity through the proven +0x339c field edge.

The original composition required the FUN_007b2270 receiver pointer itself to be
identical to the FUN_00765470 entry pointer.  Retail machine evidence disproves
that equality and proves a stronger object-layout relationship instead:

    global vehicle base -> [base + 0x339c] -> FUN_007b2270 receiver

This promotion preserves the existing SHIFT.GlobalVehicleBodyOwnerIdentity/1
handoff consumed by Process 2 while explicitly keeping pointer equality false.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
from typing import Any

FORMAT = "SHIFT.GlobalVehicleBodyOwnerIdentity/1"
FIELD_FORMAT = "SHIFT.Fun00765470BodyOwnerFieldProvenance/1"
GLOBAL_VEHICLE_ADDRESS = "0x00c13700"
BODY_OWNER_FIELD_OFFSET = "0x339c"
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


def promote_global_vehicle_body_owner_identity(
    blocked_identity_path: Path,
    field_provenance_path: Path,
) -> dict[str, Any]:
    blocked = _load(blocked_identity_path, FORMAT)
    field = _load(field_provenance_path, FIELD_FORMAT)

    join = blocked.get("identity_join") or {}
    handoff = blocked.get("handoff") or {}
    scope = blocked.get("scope") or {}
    blockers = blocked.get("blockers")
    _require(isinstance(blockers, list), "blocked identity blockers must be a list")

    _require(join.get("global_vehicle_address") == GLOBAL_VEHICLE_ADDRESS, "global vehicle address drift")
    _require(join.get("global_vehicle_component_base_identity_ready") is True, "global vehicle component base is not ready")
    _require(join.get("main_chassis_BODY_selected") is True, "main chassis BODY is not selected")
    _require(join.get("main_chassis_BODY_name") == "body", "main chassis BODY name drift")
    _require(_int(join.get("main_chassis_BODY_index")) == CHASSIS_BODY_INDEX, "main chassis BODY index drift")
    _require(join.get("global_vehicle_BODY_owner_identity_ready") is False, "input identity already preclaims BODY-owner readiness")
    _require(join.get("BODY_array_owner_is_global_vehicle_base") is False, "blocked input unexpectedly claims BODY-owner pointer equality")
    _require(handoff.get("outer_receiver_to_BODY_owner_continuity_proven") is False, "blocked input preclaims owner continuity")
    _require(handoff.get("vehicle_BODY_selection_ready") is False, "blocked input preclaims BODY selection")
    _require(handoff.get("selected_BODY_index") is None, "blocked input preclaims BODY index")
    _require(handoff.get("phase698_positive_selection_admissible") is False, "blocked input preclaims Phase 698")
    _require(handoff.get("phase700_runtime_handoff_admissible") is False, "blocked input preclaims Phase 700")
    _require(handoff.get("phase703_update_child_equality_gate_required") is False, "obsolete update-child equality gate was reintroduced")
    _require(scope.get("update_child_pointer_equality_required") is False, "scope reintroduced update-child equality")

    machine = field.get("machine_edge") or {}
    field_handoff = field.get("handoff") or {}
    field_blockers = field.get("blockers")
    _require(field_blockers == [], "BODY-owner field proof still has blockers")
    _require(machine.get("entry_receiver_to_BODY_owner_pointer_field_edge_proven") is True, "BODY-owner field edge is not proven")
    _require(machine.get("entry_receiver_equals_call_receiver_pointer") is False, "field proof incorrectly claims pointer equality")
    _require(machine.get("BODY_owner_pointer_field_offset") == BODY_OWNER_FIELD_OFFSET, "BODY-owner field offset drift")
    _require(machine.get("BODY_owner_pointer_expression") == "dword ptr [entry:ECX + 0x339c]", "BODY-owner field expression drift")
    _require(field_handoff.get("half_step_entry_ECX_to_BODY_array_owner_field_continuity_proven") is True, "field continuity is not proven")
    _require(field_handoff.get("BODY_array_owner_pointer_field_offset") == BODY_OWNER_FIELD_OFFSET, "field handoff offset drift")
    _require(field_handoff.get("global_vehicle_to_BODY_owner_composition_ready") is True, "field proof is not composition-ready")
    _require(field_handoff.get("phase703_gate_rewrite_ready") is True, "field proof is not Phase 703-ready")
    _require(field_handoff.get("phase698_positive_selection_admissible_by_this_artifact_alone") is False, "field proof incorrectly admits Phase 698 alone")

    result = deepcopy(blocked)
    result["inputs"] = dict(result.get("inputs") or {})
    result["inputs"]["BODY_owner_field_provenance"] = str(field_provenance_path)

    out_join = result["identity_join"]
    out_join["half_step_entry_ECX_to_BODY_array_owner_ECX_continuity_proven"] = False
    out_join["half_step_entry_ECX_to_BODY_array_owner_field_continuity_proven"] = True
    out_join["BODY_array_owner_is_global_vehicle_base"] = False
    out_join["BODY_array_owner_pointer_loaded_from_global_vehicle_base"] = True
    out_join["BODY_array_owner_pointer_field_offset"] = BODY_OWNER_FIELD_OFFSET
    out_join["global_vehicle_BODY_owner_identity_ready"] = True
    out_join["evidence_state"] = "proven-composed-static-field"

    out_handoff = result["handoff"]
    out_handoff["outer_receiver_to_BODY_owner_continuity_proven"] = True
    out_handoff["vehicle_BODY_selection_ready"] = True
    out_handoff["selected_BODY_index"] = CHASSIS_BODY_INDEX
    out_handoff["phase698_positive_selection_admissible"] = True
    out_handoff["phase700_runtime_handoff_admissible"] = True
    out_handoff["phase703_update_child_equality_gate_required"] = False
    out_handoff["phase703_gate_rewrite_ready"] = True
    out_handoff["vehicle_world_transform_ready"] = False
    out_handoff["critical_next_join"] = "BODY0 bind initialization/writer provenance -> SHIFT.BMWBody0BindFrameProof/1"

    result["blockers"] = []
    out_scope = result["scope"]
    out_scope["BODY_array_owner_pointer_equals_global_vehicle_base_proven"] = False
    out_scope["BODY_array_owner_pointer_field_edge_proven"] = True
    out_scope["BODY_array_owner_pointer_field_offset"] = BODY_OWNER_FIELD_OFFSET
    out_scope["dynamic_BODY_pose_to_VHF_composition_proven"] = False
    out_scope["original_game_executed"] = False
    out_scope["new_runtime_capture_required"] = False
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("blocked_identity", type=Path)
    parser.add_argument("field_provenance", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    report = promote_global_vehicle_body_owner_identity(
        args.blocked_identity, args.field_provenance
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
