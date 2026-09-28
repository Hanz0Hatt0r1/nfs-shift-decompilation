"""Model the source-backed IGPhaseVehicle completion/finalization path.

The contract records observable cleanup ordering from the retail SHIFT.exe.c
snapshot without assigning semantic class names to generic containers or
resource handles.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

FORMAT = "SHIFT.IGPhaseVehicleCompletionFinalization/1"


def build_igphasevehicle_finalization() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready",
        "ready": True,
        "owner": {
            "process_function": "FUN_004d5f30",
            "finalizer": "FUN_004d5930",
            "destructor_cleanup": "FUN_004d54a0",
            "completion_callback": "object vtable +0xc",
        },
        "completion_finalizer": {
            "function": "FUN_004d5930",
            "pre_callback": True,
            "containers": [
                {
                    "field": "IGPhaseVehicle+0x3ec",
                    "entry_callback": "DAT_00c26058 vtable +0x204",
                    "post_action": "FUN_00697420 clears the container",
                },
                {
                    "field": "IGPhaseVehicle+0x3cc",
                    "entry_callback": "DAT_00c26058 vtable +0x220",
                    "post_action": "FUN_00697420 clears the container",
                },
                {
                    "field": "IGPhaseVehicle+0x40c",
                    "entry_payload": "entry+0xc",
                    "entry_cleanup": [
                        "thunk_FUN_00470711(payload)",
                        "FUN_0067a6b0(payload)",
                    ],
                    "post_action": "FUN_00697420 clears the container",
                },
            ],
            "guarded_resource": {
                "guard_field": "IGPhaseVehicle+0x3c8",
                "when_nonzero": [
                    "FUN_006372a0(IGPhaseVehicle+0x160)",
                    "IGPhaseVehicle+0x3c8 = 0",
                ],
            },
            "resource_cleanup": [
                "FUN_00637870(IGPhaseVehicle+0x8)",
                "FUN_00637530(IGPhaseVehicle+0x160)",
                "FUN_00637880(IGPhaseVehicle+0x8)",
                "FUN_00697420(IGPhaseVehicle+0x3a4)",
                "FUN_00634eb0(thunk_FUN_0045b39c()+0x1758)",
                "thunk_FUN_0050caa0(IGPhaseVehicle)",
            ],
            "ordering": "container callbacks and resource cleanup complete before the object's +0xc vtable callback in FUN_004d5f30",
        },
        "load_boundary": {
            "function": "FUN_004d5520",
            "resource_fields": [
                "IGPhaseVehicle+0x8",
                "IGPhaseVehicle+0x160",
                "IGPhaseVehicle+0x3a4",
                "IGPhaseVehicle+0x3c8",
            ],
            "observed_setup": [
                "vehicle or cockpit BFF is bound into the phase resource path",
                "IGPhaseVehicle+0x3c8 is initialized to 0",
                "resources referenced by the phase are attached to +0x160",
            ],
        },
        "process_link": {
            "function": "FUN_004d5f30",
            "normal_state": [
                "process/reselection loop terminates",
                "FUN_004d5930(param_1)",
                "log Process Done",
                "object vtable +0xc callback",
            ],
            "cockpit_state": [
                "state +0x45c == 2 takes the dedicated cockpit branch",
                "thunk_FUN_00d7f900(param_1)",
                "FUN_004d5930(param_1)",
                "log Process Cockpit Done",
                "object vtable +0xc callback",
            ],
        },
        "destructor_boundary": {
            "function": "FUN_004d54a0",
            "actions": [
                "release +0x460 object when non-null",
                "clear +0x3ec container",
                "clear +0x3cc container",
                "clear +0x40c container",
                "clear +0x3a4 resource container",
                "clear +0x42c container",
                "call thunk_FUN_0050caa0(param_1)",
                "release +0xc object when non-null",
            ],
            "relationship": "destructor cleanup is broader lifetime teardown than the process-completion finalizer",
        },
        "evidence": [
            "FUN_004d5930 iterates +0x3ec, +0x3cc and +0x40c and performs distinct callback/cleanup actions before clearing each container.",
            "FUN_004d5930 conditionally clears +0x160 when +0x3c8 is nonzero, then closes/cleans +0x8, +0x160 and +0x3a4.",
            "FUN_004d5f30 invokes FUN_004d5930 before its final object vtable callback in both normal and cockpit completion paths.",
            "FUN_004d54a0 resets the same owned containers during object destruction and also calls thunk_FUN_0050caa0.",
        ],
        "limitations": [
            "Container fields and helper calls are described structurally; their generic engine types are not inferred.",
            "vtable offsets +0x204 and +0x220 are recorded as observed dispatch slots, not named operations.",
            "No resource ownership model beyond the observed cleanup ordering is asserted.",
            "This phase does not add runtime provider/PhysX numeric claims.",
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the source-backed IGPhaseVehicle completion/finalization contract"
    )
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)

    report = build_igphasevehicle_finalization()
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["FORMAT", "build_igphasevehicle_finalization"]
