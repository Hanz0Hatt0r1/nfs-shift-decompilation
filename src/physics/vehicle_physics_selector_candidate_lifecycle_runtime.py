"""Model the source-backed selector descriptor/candidate lifecycle.

The contract records only static control/data flow visible in the retail
SHIFT.exe.c snapshot. It keeps the descriptor state byte/flag distinct from
the separate completion/consumption flag and does not assign a higher-level
class name to the descriptor.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

FORMAT = "SHIFT.VehiclePhysicsSelectorCandidateLifecycle/1"


def build_vehicle_physics_selector_candidate_lifecycle() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready",
        "ready": True,
        "descriptor": {
            "owner_context": "DAT_00bbc600",
            "base": "context+0xb8",
            "stride": "0x90",
            "count_field": "context+0x1c",
            "state_offset": "+0x74",
            "ordinal_offset": "+0x8c",
            "post_load_flag_offset": "+0x1d",
            "constructor": "FUN_0040eec0",
            "constructor_defaults": {
                "+0x74": 1,
                "+0x7d": 1,
                "+0x88": 0,
                "+0x8c": 0,
            },
        },
        "population": {
            "function": "thunk_FUN_00d36a00",
            "writes": [
                "descriptor+0x1d = 0",
                "descriptor+0x1e from source bits",
                "descriptor+0x7d from source bits",
                "descriptor+0x88 = 0",
            ],
            "role": "observed descriptor population/reset before later load processing",
        },
        "selection_scan": {
            "function": "FUN_0043af50",
            "entry_point": "context+0xb8",
            "step": "0x90 bytes per descriptor",
            "eligible_test": "descriptor+0x74 == 0",
            "success": [
                "descriptor+0x8c = ordinal",
                "caller output pointer = descriptor",
                "return ordinal",
            ],
            "exhausted": {
                "return_value": -1,
                "mutation": "none",
            },
        },
        "selector_match_path": {
            "function": "FUN_00410ef0",
            "storage": "context+0x9fc",
            "scan": "FUN_0052cce0(selector_storage, &candidate)",
            "eligible_test": "candidate+0x74 == 0",
            "success": [
                "caller output pointer = candidate",
                "return selector-storage enumeration ordinal",
            ],
            "exhausted": {
                "function": "FUN_00688010",
                "return_value": -1,
            },
        },
        "batch_reservation_path": {
            "function": "FUN_004d69d0",
            "purpose": "observed temporary exclusion while collecting descriptors from the selector table",
            "steps": [
                "call FUN_0043af50(&DAT_00bbc600, &local_c)",
                "when a descriptor is returned, set descriptor+0x74 = 1 and retain its pointer",
                "repeat until no descriptor remains or 16 descriptors have been collected",
                "reset descriptor+0x74 = 0 for all collected descriptors",
                "process the collected descriptor pointers",
            ],
            "bound": 16,
        },
        "post_load_state_path": {
            "function": "FUN_0040f900",
            "writes": [
                "descriptor+0x1d = 1 after the observed load/process call path",
            ],
            "relation": "same descriptor field that thunk_FUN_00d36a00 initializes to zero",
        },
        "vehicle_load_consumer_path": {
            "function": "FUN_00465860",
            "steps": [
                "call FUN_0043af50(&DAT_00bbc600, &local_8)",
                "consume/load data from the returned descriptor",
                "set descriptor+0x1d = 1 after the observed load/process step",
                "call FUN_0043af50 again for another eligible descriptor",
            ],
            "state_separation": "The observed +0x1d write is kept separate from the +0x74 eligibility/exclusion test.",
        },
        "cross_phase_relation": {
            "phase508_selector_global": "DAT_00bbc600",
            "phase509_selector_global": "DAT_00bbc600",
            "phase509_note": "FUN_004d5f30 consumes the selector global through FUN_00410ef0; the present phase adds direct evidence for the descriptor-level +0x74 scan state.",
        },
        "evidence": [
            "FUN_0040eec0 initializes each descriptor record with +0x74 = 1 and +0x8c = 0.",
            "FUN_00410ef0 enumerates selector storage and accepts the first candidate with candidate+0x74 == 0.",
            "FUN_0043af50 scans the source descriptor table at context+0xb8 with 0x90-byte stride and also tests descriptor+0x74 == 0.",
            "FUN_0043af50 writes the selected descriptor ordinal into descriptor+0x8c before returning it.",
            "FUN_004d69d0 temporarily sets returned descriptor+0x74 back to 1 while collecting a bounded batch, then clears the same flag before processing the batch.",
            "thunk_FUN_00d36a00 initializes descriptor+0x1d = 0 while populating a descriptor; FUN_0040f900 later sets the same field to 1 after its observed load/process call path.",
            "FUN_00465860 independently sets descriptor+0x1d = 1 after its observed vehicle-load/process step, showing a distinct flag from the +0x74 eligibility/exclusion state.",
        ],
        "limitations": [
            "The +0x74 field is described only as the observed selector eligibility/exclusion state; no stronger semantic label is assigned.",
            "The +0x1d field is described only as a separate observed descriptor state that is initialized to zero and later set to one after load/process paths; its broader semantics are unknown.",
            "No C++ class identity is inferred for the descriptor or selector storage.",
            "Runtime instance identity and provider/physics numeric equivalence remain capture-dependent.",
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the source-backed selector candidate lifecycle contract"
    )
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)

    report = build_vehicle_physics_selector_candidate_lifecycle()
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["FORMAT", "build_vehicle_physics_selector_candidate_lifecycle"]
