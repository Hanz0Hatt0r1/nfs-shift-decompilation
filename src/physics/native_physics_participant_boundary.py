"""Build the source-backed participant-registry boundary for native_runtime.

This contract intentionally stops before assigning a concrete runtime
participant instance. It joins only already-proven source/control-flow facts:
the IGPhaseVehicle selector gate, the DAT_00c109e0 registry/update API, the
separate DAT_00bbc600 selector context, and the process/reselection writeback
slots.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

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

FORMAT = "SHIFT.NativePhysicsParticipantBoundary/1"
REGISTRY_SLOT_STRIDE = 0x1FA0
PARTICIPANT_DESCRIPTOR_TYPE = 3


def build_native_physics_participant_boundary() -> dict[str, Any]:
    gate = build_vehicle_physics_participant_gate()
    registry = build_physics_participant_registry_update()
    selector = build_vehicle_physics_selector_context()
    process = build_vehicle_physics_participant_process()

    blockers: list[str] = []
    for name, report in (
        ("participant-gate", gate),
        ("participant-registry", registry),
        ("selector-context", selector),
        ("participant-process", process),
    ):
        if report.get("ready") is not True:
            blockers.append(f"{name}:not-ready")

    manager = registry.get("manager") or {}
    callsite = registry.get("participant_callsite") or {}
    separation = selector.get("separation") or {}
    context = selector.get("context") or {}
    owner = process.get("owner") or {}
    selection = process.get("selection_step") or {}
    matching = selector.get("matching") or {}
    termination = (
        matching.get("termination")
        if isinstance(matching, dict)
        else {}
    ) or {}

    if manager.get("global_instance") != "DAT_00c109e0":
        blockers.append("registry:manager-global-mismatch")
    if manager.get("slot_array_field") != "+0x140":
        blockers.append("registry:slot-array-field-mismatch")
    if manager.get("slot_count_field") != "+0x148":
        blockers.append("registry:slot-count-field-mismatch")
    if str(manager.get("allocated_entry_stride") or "").lower() != "0x1fa0":
        blockers.append("registry:slot-stride-mismatch")
    if callsite.get("type_gate") != "participant descriptor +0x1c == 3":
        blockers.append("registry:participant-descriptor-type-mismatch")
    if (
        callsite.get("participant_index_source")
        != "PhysicsParticipant +0x3c"
    ):
        blockers.append("registry:index-source-mismatch")

    if context.get("global_instance") != "DAT_00bbc600":
        blockers.append("selector:global-mismatch")
    if separation.get("same_object_proven") is not False:
        blockers.append("selector:manager-separation-not-preserved")
    if separation.get("participant_manager_global") != "DAT_00c109e0":
        blockers.append("selector:manager-global-mismatch")
    if selection.get("selector_global") != "DAT_00bbc600":
        blockers.append("process:selector-global-mismatch")
    if owner.get("pointer_slot") != "IGPhaseVehicle+0x450":
        blockers.append("process:pointer-slot-mismatch")
    if owner.get("ordinal_slot") != "IGPhaseVehicle+0x454":
        blockers.append("process:ordinal-slot-mismatch")
    if owner.get("state_slot") != "IGPhaseVehicle+0x45c":
        blockers.append("process:state-slot-mismatch")
    if termination.get("candidate_ready_test") != "candidate+0x74 == 0":
        blockers.append("selector:candidate-ready-gate-mismatch")

    ready = not blockers
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": blockers,
        "registry_contract_ready": registry.get("ready") is True,
        "participant_gate_ready": gate.get("ready") is True,
        "participant_process_ready": process.get("ready") is True,
        "selector_context_ready": selector.get("ready") is True,
        "registry_manager_global": "DAT_00c109e0",
        "selector_global": "DAT_00bbc600",
        "selector_context_separate": True,
        "registry_slot_array_offset": 0x140,
        "registry_slot_count_offset": 0x148,
        "registry_slot_stride": REGISTRY_SLOT_STRIDE,
        "participant_descriptor_type": PARTICIPANT_DESCRIPTOR_TYPE,
        "registry_index_source": "PhysicsParticipant+0x3c",
        "registry_index_source_offset": 0x3C,
        "participant_pointer_slot": "IGPhaseVehicle+0x450",
        "participant_ordinal_slot": "IGPhaseVehicle+0x454",
        "participant_state_slot": "IGPhaseVehicle+0x45c",
        "selector_candidate_ready_offset": 0x74,
        "registry_selector_identity_join_proven": False,
        "participant_instance_ready": False,
        "participant_registry_index": -1,
        "selector_ordinal": -1,
        "participant_process_state": -1,
        # Legacy Phase 602 aliases remain unresolved. They must never be
        # populated from static evidence because their identity domain was
        # intentionally ambiguous.
        "participant_index": -1,
        "participant_mode": -1,
        "source_contracts": {
            "participant_gate": gate["format"],
            "participant_registry": registry["format"],
            "selector_context": selector["format"],
            "participant_process": process["format"],
        },
        "boundary": {
            "native_state_structural_admission": ready,
            "selected_runtime_instance_proven": False,
            "selected_provider_proven": False,
            "numeric_physics_equivalence_proven": False,
            "manager_selector_same_object_claimed": False,
            "registry_index_equals_selector_ordinal": False,
            "registry_selector_identity_join_proven": False,
            "legacy_participant_index_alias_active": False,
            "participant_ready_policy": (
                "must remain false until independent runtime-instance evidence "
                "joins the manager registry identity and selected IGPhaseVehicle "
                "participant while retaining the selector ordinal separately"
            ),
        },
        "limitations": [
            "The selector context and PhysicsParticipantManager registry remain distinct objects.",
            "No concrete runtime participant pointer, manager registry index, selector ordinal or process state is fabricated.",
            "No PhysX/provider class identity is assigned.",
            "No provider selection or numerical solver parity is claimed.",
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)

    report = build_native_physics_participant_boundary()
    payload = json.dumps(
        report,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "FORMAT",
    "REGISTRY_SLOT_STRIDE",
    "PARTICIPANT_DESCRIPTOR_TYPE",
    "build_native_physics_participant_boundary",
]
