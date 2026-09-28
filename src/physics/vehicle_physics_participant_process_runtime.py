"""Model the source-backed IGPhaseVehicle participant process/reselection loop.

The contract records only the control/data flow visible in the retail
SHIFT.exe.c snapshot. It deliberately does not assign an engine/PhysX class
name to the selected pointer.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

FORMAT = "SHIFT.VehiclePhysicsParticipantProcessReselect/1"


def build_vehicle_physics_participant_process() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready",
        "ready": True,
        "owner": {
            "function": "FUN_004d5f30",
            "source_name": "IGPhaseVehicle process/update path",
            "pointer_slot": "IGPhaseVehicle+0x450",
            "ordinal_slot": "IGPhaseVehicle+0x454",
            "state_slot": "IGPhaseVehicle+0x45c",
        },
        "preload_step": {
            "function": "FUN_00468ed0",
            "pointer_argument": "IGPhaseVehicle+0x450",
            "first_argument": "selected_pointer[0x23] (selected_pointer + 0x8c)",
            "second_argument": "selected_pointer",
            "ordering": "runs before the next FUN_00410ef0 selection attempt",
        },
        "selection_step": {
            "selector_global": "DAT_00bbc600",
            "selector_function": "FUN_00410ef0",
            "output_pointer": "&local_8",
            "result_ordinal": "local iVar2",
            "failure_value": -1,
            "success_writeback": {
                "ordinal": "IGPhaseVehicle+0x454 = iVar2",
                "pointer": "IGPhaseVehicle+0x450 = local_8",
            },
        },
        "load_step": {
            "path_template": "Pakfiles/Vehicles/%s.bff",
            "path_builder": "FUN_00636030(&local_18, ...)",
            "load_function": "FUN_00635e60(*(void **)(IGPhaseVehicle+0x3a4), local_14)",
            "success_condition": "(char)uVar3 != 0",
            "writeback_order": [
                "IGPhaseVehicle+0x454 = selected ordinal",
                "IGPhaseVehicle+0x450 = selected pointer",
            ],
            "break_conditions": [
                "selector returns -1",
                "vehicle BFF load function returns false",
            ],
        },
        "loop": {
            "function": "FUN_004d5f30",
            "kind": "process-current-pointer-then-select-and-load-next",
            "repeats": True,
            "termination": [
                "no candidate from FUN_00410ef0",
                "next vehicle BFF load fails",
            ],
            "post_loop": {
                "state_transition": "if state is 0 and *(thunk_FUN_00444fcc()+0x374) != 0, set state to 1",
                "finalizer": "FUN_004d5930",
                "completion_log": "IGPhaseVehicle: Process Done",
                "callback": "vtable call at *param_1 + 0xc",
            },
            "special_state_2": {
                "condition": "IGPhaseVehicle+0x45c == 2",
                "path": [
                    "thunk_FUN_00444fcc() -> +0x374",
                    "FUN_00481d40(+0x374)",
                    "FUN_004d5160(param_1)",
                    "set state to 3",
                    "thunk_FUN_00d7f900(param_1)",
                    "FUN_004d5930(param_1)",
                    "log Process Cockpit Done",
                    "vtable call at *param_1 + 0xc",
                ],
                "loop_bypassed": True,
            },
        },
        "relationship_to_phase508": {
            "selector_global": "DAT_00bbc600",
            "same_selector_global": True,
            "note": "FUN_004d5f30 directly calls FUN_00410ef0(&DAT_00bbc600, ...), independently confirming that the Phase 508 selector global is the object used for process/reselection.",
        },
        "relationship_to_phase505": {
            "pointer_slot": "IGPhaseVehicle+0x450",
            "ordinal_slot": "IGPhaseVehicle+0x454",
            "same_slots": True,
            "note": "Phase 505 identified these slots as the participant-selection writeback fields; Phase 509 now proves they are consumed by the subsequent process loop and overwritten by later successful selections.",
        },
        "evidence": [
            "FUN_004d5f30 reads the stored pointer at IGPhaseVehicle+0x450 and passes it into FUN_00468ed0 before another selection attempt.",
            "FUN_004d5f30 directly calls FUN_00410ef0(&DAT_00bbc600, &local_8).",
            "A successful selector result is followed by Pakfiles/Vehicles/%s.bff construction and load.",
            "Only after the load succeeds does the caller store the new ordinal/pointer into +0x454/+0x450.",
            "The loop therefore preserves the previously selected pointer until the next candidate is successfully loaded.",
        ],
        "limitations": [
            "FUN_00468ed0 is treated as an observed pre-load processing step; no higher-level semantic name is assigned to its first argument.",
            "The selected pointer's +0x8c field is recorded structurally, not given a physical or engine-specific meaning.",
            "No PhysX SDK class or provider identity is inferred.",
            "The loop proves repeated selector consumption, not the runtime identity of any individual candidate instance.",
            "Numeric physics/provider equivalence remains capture-dependent.",
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the source-backed IGPhaseVehicle participant process/reselection contract"
    )
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)

    report = build_vehicle_physics_participant_process()
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["FORMAT", "build_vehicle_physics_participant_process"]
