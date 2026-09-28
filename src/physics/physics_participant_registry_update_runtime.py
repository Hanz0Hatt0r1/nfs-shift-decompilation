"""Model source-backed PhysicsParticipantManager participant-slot registration/update.

The contract records concrete array allocation and update routines used by
PhysicsParticipant.cpp. It does not infer an engine/PhysX class name and does
not join this registry to the separate FUN_00410ef0 selector context.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

FORMAT = "SHIFT.PhysicsParticipantRegistryUpdate/1"


def build_physics_participant_registry_update() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready",
        "ready": True,
        "manager": {
            "global_instance": "DAT_00c109e0",
            "slot_array_field": "+0x140",
            "slot_count_field": "+0x148",
            "allocated_entry_stride": "0x1fa0",
            "constructor": "FUN_007146c0",
            "destructor": "FUN_00714840",
        },
        "allocation": {
            "function": "FUN_007146c0",
            "entry_count_parameter": "param_1",
            "slot_array_allocation": "param_1 * 0x1fa0 bytes",
            "slot_array_field_write": "manager+0x140 = constructed entry array",
            "slot_count_field_write": "manager+0x148 = param_1",
            "aux_entry_array": {"field": "+0x3a0", "stride": 8},
        },
        "registration": {
            "function": "FUN_00713f40",
            "index_parameter": "param_1",
            "descriptor_parameter": "param_2",
            "source_slot": "manager+0x140 + param_1 * 0x1fa0",
            "descriptor_enabled_field": "param_2+0x10",
            "descriptor_index_field": "param_2+0x14",
            "descriptor_enabled_value": 1,
            "preserve_or_default_flag": "param_3",
            "default_sources_when_flag_zero": {
                "+0x18": "slot+0x15b8",
                "+0x1c": "slot+0x2298",
                "+0x20": "slot+0x2244",
                "+0x24": "slot+0x2250",
                "+0x28": "slot+0x225c",
                "+0x2c": "slot+0x2260",
                "+0x30": "slot+0x2270",
                "+0x34": "slot+0x320",
                "+0x3c": "slot+0x26e0",
            },
        },
        "update": {
            "function": "FUN_00713ec0",
            "index_parameter": "param_1",
            "descriptor_parameter": "param_2",
            "target_slot": "manager+0x140 + param_1 * 0x1fa0",
            "writes": {
                "+0x2298": "descriptor+0x1c",
                "+0x2244": "descriptor+0x20",
                "+0x2250": "descriptor+0x24",
                "+0x225c": "descriptor+0x28",
                "+0x2260": "descriptor+0x2c",
                "+0x2270": "descriptor+0x30",
                "+0x26e0": "descriptor+0x3c",
            },
            "pre_transform_input": "descriptor+0x18 -> slot+0x340 via FUN_00787a70",
            "post_transform": "FUN_007448c0(slot)",
            "return_value": "low-byte success marker 1",
        },
        "participant_callsite": {
            "source_file": ".\\Source\\System\\PhysicsParticipant.cpp",
            "function_context": "FUN_0074ddc3",
            "type_gate": "participant descriptor +0x1c == 3",
            "registration_call": "FUN_00713f40(&DAT_00c109e0, participant_index, descriptor, 1)",
            "update_call": "FUN_00713ec0(&DAT_00c109e0, participant_index, descriptor)",
            "participant_index_source": "PhysicsParticipant +0x3c",
        },
        "lifecycle": {
            "initialization": "FUN_007146c0 allocates/constructs manager participant slots",
            "registration": "FUN_00713f40 enables the descriptor and records the slot index",
            "update": "FUN_00713ec0 imports descriptor state into the indexed participant slot",
            "destruction": "FUN_00714840 destructs and frees the slot array",
        },
        "relationship_to_phase505": {
            "phase505_selector": "FUN_00410ef0",
            "selector_context": "thunk_FUN_00453990()",
            "manager_global": "DAT_00c109e0",
            "same_object_proven": False,
            "note": "This contract proves a participant registry/update API on DAT_00c109e0 and its direct use from PhysicsParticipant.cpp; it does not prove that thunk_FUN_00453990 returns the same object.",
        },
        "limitations": [
            "The meaning of individual participant fields remains limited to observed data movement and control-flow.",
            "No PhysX SDK class, engine object type or physical unit is inferred.",
            "The Phase 505 selector-context to manager-global identity join remains open.",
            "Runtime participant identity and numeric physics equivalence remain capture-dependent.",
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the source-backed physics participant registry/update contract"
    )
    parser.add_argument("-o", "--output")
    args = parser.parse_args(argv)

    report = build_physics_participant_registry_update()
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["FORMAT", "build_physics_participant_registry_update"]
