"""Model the source-backed selector context used by IGPhaseVehicle.

This is deliberately kept separate from DAT_00c109e0, which is the
PhysicsParticipantManager global covered by Phases 506-507.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

FORMAT = "SHIFT.VehiclePhysicsSelectorContext/1"


def build_vehicle_physics_selector_context() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready",
        "ready": True,
        "context": {
            "global_instance": "DAT_00bbc600",
            "accessor": "FUN_00402435",
            "accessor_thunk": "thunk_FUN_00453990",
            "member_selector_field": "+0x9fc",
            "descriptor_count_field": "+0x1c",
            "descriptor_base": "+0xb8",
            "descriptor_stride": "0x90",
            "descriptor_name_offset": "+0x10",
            "descriptor_index_shadow_base": "+0x144",
            "descriptor_index_shadow_stride": "0x90",
        },
        "lifecycle": {
            "constructor": "FUN_00410490",
            "constructor_defaults": {
                "descriptor_count": "+0x1c",
                "selector_storage_initialized": "constructor object includes selector storage at +0x9fc",
            },
            "selector_init": "FUN_004102d0 -> FUN_004f0050(context+0x9fc, param_2)",
            "shutdown": "FUN_00411430(context)",
            "global_lazy_init": "FUN_00402435 ensures FUN_00410490(&DAT_00bbc600) once and registers FUN_00a9ae60",
        },
        "matching": {
            "function": "FUN_00410ef0",
            "precondition": "FUN_0082f3c0(context+0x9fc) is true before descriptor matching",
            "preflight": [
                "if FUN_00473f10(selector_storage) == 0: FUN_0040b870(); thunk_FUN_00448bd0(selector_storage, 0, 0x1f)",
            ],
            "ordinal_initialization": "descriptor shadow ordinals at context+0x144 + ordinal*0x90 are initialized to ordinal",
            "insert": {
                "function": "FUN_00800dd0",
                "source_entry": "descriptor address + descriptor ordinal",
                "behavior_in_match": "selected descriptor is inserted into selector storage",
            },
            "linking": {
                "name_source": "descriptor+0x10",
                "comparison": "__stricmp",
                "empty_name_rule": "empty/null names are linked together",
                "unmatched_name": "candidate remains unresolved and becomes the next local fallback ordinal",
            },
            "termination": {
                "all_linked": "matching loop terminates when no unresolved descriptor remains",
                "fallback_scan": "FUN_0052cce0 enumerates selector storage in order",
                "candidate_ready_test": "candidate+0x74 == 0",
                "success_result": "writes candidate pointer to caller and returns enumeration ordinal",
                "no_ready_candidate": "calls FUN_00688010(selector_storage, ...) and returns -1",
            },
        },
        "separation": {
            "selector_global": "DAT_00bbc600",
            "participant_manager_global": "DAT_00c109e0",
            "same_object_proven": False,
            "reason": "thunk_FUN_00453990/FUN_00402435 return &DAT_00bbc600, while Phase 506-507 manager event/registry APIs explicitly target &DAT_00c109e0",
        },
        "evidence": [
            "thunk_FUN_00453990 calls FUN_00402435, which returns &DAT_00bbc600.",
            "FUN_00410490 constructs DAT_00bbc600 and calls FUN_00410350 for baseline fields.",
            "FUN_004102d0 initializes selector storage at context+0x9fc.",
            "FUN_00410ef0 reads descriptor count/base from the context and inserts matched descriptors via FUN_00800dd0.",
            "The final selection scan enumerates that same selector storage via FUN_0052cce0.",
            "The separate PhysicsParticipantManager contracts use DAT_00c109e0, not DAT_00bbc600.",
        ],
        "limitations": [
            "The repository does not assign a C++ class name to DAT_00bbc600.",
            "FUN_0052cce0 is treated only as the observed selector-storage enumerator; its generic container implementation is not given a higher-level semantic name.",
            "This phase does not identify the runtime identity of the selected participant candidate.",
            "Provider selection and numeric physics equivalence remain runtime-capture dependent.",
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the source-backed vehicle physics selector-context contract"
    )
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)

    report = build_vehicle_physics_selector_context()
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["FORMAT", "build_vehicle_physics_selector_context"]
