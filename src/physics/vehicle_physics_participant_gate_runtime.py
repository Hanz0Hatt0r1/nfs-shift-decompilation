"""Model the source-backed IGPhaseVehicle physics-participant creation gate.

The contract records only observations visible in SHIFT.exe.c: the phase
object asks a selection context for a participant, stores the returned pointer
and ordinal, waits when the selector returns -1, and only then begins loading
the base vehicle BFF. It does not identify the underlying engine/PhysX class.
"""
from __future__ import annotations

import argparse
import json
from typing import Any, Sequence

FORMAT = "SHIFT.VehiclePhysicsParticipantGate/1"


def build_vehicle_physics_participant_gate() -> dict[str, Any]:
    """Return the fixed source-backed participant creation/load gate."""
    selection = {
        "callee": "FUN_00410ef0",
        "selection_context_factory": "thunk_FUN_00453990",
        "argument_output_pointer": "IGPhaseVehicle+0x450",
        "returned_pointer_slot": "IGPhaseVehicle+0x450",
        "returned_ordinal_slot": "IGPhaseVehicle+0x454",
        "failure_value": -1,
        "failure_transition": {
            "return_code": 4,
            "log": "IGPhaseVehicle: Waiting for Physics Participant Create",
        },
    }

    source_algorithm = {
        "participant_descriptor_count": "selection_context+0x1c",
        "participant_descriptor_base": "selection_context+0xb8",
        "participant_descriptor_stride": "0x90",
        "participant_name_offset": "descriptor+0x10",
        "descriptor_ordinal_writeback": "descriptor_index -> descriptor+0x0",
        "candidate_eligibility_test": "candidate+0x74 == 0",
        "returned_ordinal": "eligible candidate ordinal in registry iteration order",
        "returned_pointer": "eligible candidate pointer written through argument_output_pointer",
        "name_matching": "case-insensitive match (__stricmp) after local descriptor linking",
        "no_candidate": "selector drains registry iteration and returns -1",
    }

    post_success = {
        "phase_state_field": "IGPhaseVehicle+0x45c",
        "cockpit_state_value": 1,
        "base_load_path": "Pakfiles/Vehicles/%s.bff",
        "cockpit_load_path": "Pakfiles/Vehicles/%s_cockpit.bff",
        "base_load_begins_after_success": True,
        "cockpit_branch_preserved": True,
    }

    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready",
        "ready": True,
        "source_functions": {
            "participant_selection": "FUN_00410ef0",
            "phase_vehicle_caller": "caller near FUN_00453990 -> FUN_00410ef0",
            "phase_vehicle_state_machine": "IGPhaseVehicle update path",
        },
        "selection": selection,
        "source_algorithm": source_algorithm,
        "post_success": post_success,
        "evidence": [
            "FUN_00410ef0 initializes/links participant descriptors and iterates the registry.",
            "A registry candidate is accepted only when byte at candidate+0x74 is zero.",
            "On success FUN_00410ef0 writes the candidate pointer through its second argument and returns the candidate ordinal.",
            "IGPhaseVehicle stores the return value at +0x454.",
            "A return value of -1 logs the waiting message and returns 4 before base vehicle BFF loading.",
            "On success the same caller formats Pakfiles/Vehicles/%s.bff and starts the base vehicle load path.",
        ],
        "limitations": [
            "The field at candidate+0x74 is recorded only as an observed eligibility condition; no semantic class name is assigned.",
            "No PhysX SDK class, provider implementation or runtime participant identity is inferred.",
            "The contract models source/control-flow evidence only; runtime capture is still required for the actual participant instance.",
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the source-backed vehicle physics participant creation/load gate"
    )
    parser.add_argument("-o", "--output")
    args = parser.parse_args(argv)
    report = build_vehicle_physics_participant_gate()
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        from pathlib import Path
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["FORMAT", "build_vehicle_physics_participant_gate"]
