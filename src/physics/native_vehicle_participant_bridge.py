"""Bridge source-backed vehicle participant topology into native_runtime.

This phase deliberately transports only relationships that are already proven
across Phases 505, 507, 508 and 509.  The PhysicsParticipantManager registry
index and the IGPhaseVehicle selector ordinal remain separate identities.  No
runtime participant pointer, provider identity or force law is synthesized.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from physics_participant_registry_update_runtime import (
    build_physics_participant_registry_update,
)
from vehicle_physics_participant_gate_runtime import (
    build_vehicle_physics_participant_gate,
)
from vehicle_physics_participant_process_runtime import (
    build_vehicle_physics_participant_process,
)
from vehicle_physics_selector_context_runtime import (
    build_vehicle_physics_selector_context,
)

FORMAT = "SHIFT.NativeVehicleParticipantBridge/1"


def _blocked(reasons: Sequence[str]) -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "blocked",
        "ready": False,
        "blocking_reasons": list(dict.fromkeys(str(v) for v in reasons)),
        "native_participant_topology_ready": False,
        "native_participant_ready": False,
        "native_registry_index": -1,
        "native_selector_ordinal": -1,
        "native_process_state": -1,
    }


def build_native_vehicle_participant_bridge(
    *,
    participant_gate: Mapping[str, Any] | None = None,
    registry_update: Mapping[str, Any] | None = None,
    selector_context: Mapping[str, Any] | None = None,
    participant_process: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    gate = dict(
        participant_gate
        if participant_gate is not None
        else build_vehicle_physics_participant_gate()
    )
    registry = dict(
        registry_update
        if registry_update is not None
        else build_physics_participant_registry_update()
    )
    selector = dict(
        selector_context
        if selector_context is not None
        else build_vehicle_physics_selector_context()
    )
    process = dict(
        participant_process
        if participant_process is not None
        else build_vehicle_physics_participant_process()
    )

    expected = {
        "participant_gate": "SHIFT.VehiclePhysicsParticipantGate/1",
        "registry_update": "SHIFT.PhysicsParticipantRegistryUpdate/1",
        "selector_context": "SHIFT.VehiclePhysicsSelectorContext/1",
        "participant_process": "SHIFT.VehiclePhysicsParticipantProcessReselect/1",
    }
    reports = {
        "participant_gate": gate,
        "registry_update": registry,
        "selector_context": selector,
        "participant_process": process,
    }
    blockers: list[str] = []
    for name, report in reports.items():
        if report.get("format") != expected[name]:
            blockers.append(f"native-participant:{name}:invalid-format")
        if report.get("ready") is not True:
            blockers.append(f"native-participant:{name}:not-ready")

    gate_selection = gate.get("selection")
    registry_manager = registry.get("manager")
    registry_callsite = registry.get("participant_callsite")
    selector_ctx = selector.get("context")
    selector_sep = selector.get("separation")
    process_owner = process.get("owner")
    process_selection = process.get("selection_step")
    relation = process.get("relationship_to_phase505")
    if not all(
        isinstance(value, Mapping)
        for value in (
            gate_selection,
            registry_manager,
            registry_callsite,
            selector_ctx,
            selector_sep,
            process_owner,
            process_selection,
            relation,
        )
    ):
        blockers.append("native-participant:source-contract-shape-missing")
        return _blocked(blockers)

    manager_global = str(registry_manager.get("global_instance") or "")
    selector_global = str(selector_ctx.get("global_instance") or "")
    if manager_global != "DAT_00c109e0":
        blockers.append("native-participant:manager-global-mismatch")
    if selector_global != "DAT_00bbc600":
        blockers.append("native-participant:selector-global-mismatch")
    if manager_global == selector_global:
        blockers.append("native-participant:manager-selector-conflated")
    if selector_sep.get("same_object_proven") is not False:
        blockers.append("native-participant:identity-join-overclaimed")
    if process_selection.get("selector_global") != selector_global:
        blockers.append("native-participant:process-selector-global-mismatch")

    if gate_selection.get("returned_pointer_slot") != "IGPhaseVehicle+0x450":
        blockers.append("native-participant:pointer-slot-mismatch")
    if gate_selection.get("returned_ordinal_slot") != "IGPhaseVehicle+0x454":
        blockers.append("native-participant:ordinal-slot-mismatch")
    if process_owner.get("pointer_slot") != "IGPhaseVehicle+0x450":
        blockers.append("native-participant:process-pointer-slot-mismatch")
    if process_owner.get("ordinal_slot") != "IGPhaseVehicle+0x454":
        blockers.append("native-participant:process-ordinal-slot-mismatch")
    if process_owner.get("state_slot") != "IGPhaseVehicle+0x45c":
        blockers.append("native-participant:process-state-slot-mismatch")
    if relation.get("same_slots") is not True:
        blockers.append("native-participant:phase505-slot-join-missing")
    if (
        registry_callsite.get("participant_index_source")
        != "PhysicsParticipant +0x3c"
    ):
        blockers.append("native-participant:registry-index-source-mismatch")

    selector_matching = selector.get("matching")
    termination = (
        selector_matching.get("termination")
        if isinstance(selector_matching, Mapping)
        else None
    )
    if (
        not isinstance(termination, Mapping)
        or termination.get("candidate_ready_test") != "candidate+0x74 == 0"
    ):
        blockers.append("native-participant:candidate-ready-gate-mismatch")

    if blockers:
        return _blocked(blockers)

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready",
        "ready": True,
        "blocking_reasons": [],
        "native_participant_topology_ready": True,
        "native_participant_ready": False,
        "native_registry_index": -1,
        "native_selector_ordinal": -1,
        "native_process_state": -1,
        "topology": {
            "participant_manager_global": manager_global,
            "selector_global": selector_global,
            "manager_selector_same_object_proven": False,
            "manager_slot_array_offset": 0x140,
            "manager_slot_count_offset": 0x148,
            "manager_slot_stride_bytes": 0x1FA0,
            "manager_registry_index_source_offset": 0x3C,
            "igphase_selected_pointer_offset": 0x450,
            "igphase_selector_ordinal_offset": 0x454,
            "igphase_process_state_offset": 0x45C,
            "selector_candidate_ready_offset": 0x74,
            "selector_failure_ordinal": -1,
        },
        "source": {
            "participant_gate_format": gate["format"],
            "registry_update_format": registry["format"],
            "selector_context_format": selector["format"],
            "participant_process_format": process["format"],
            "selector_function": "FUN_00410ef0",
            "registry_register_function": "FUN_00713f40",
            "registry_update_function": "FUN_00713ec0",
            "participant_process_function": "FUN_004d5f30",
        },
        "boundary": {
            "registry_index_equals_selector_ordinal": False,
            "registry_selector_identity_join_proven": False,
            "participant_pointer_transport": "not-performed",
            "runtime_participant_instance_observed": False,
            "provider_identity_assigned": False,
            "force_application_assigned": False,
            "native_fixed_tick_may_observe_unresolved_topology": True,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output")
    args = parser.parse_args(argv)

    report = build_native_vehicle_participant_bridge()
    payload = (
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    )
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["FORMAT", "build_native_vehicle_participant_bridge"]
