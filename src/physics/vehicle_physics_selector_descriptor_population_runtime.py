"""Source-backed selector descriptor population and bitfield layout.

This contract models only transformations directly visible in the retail
SHIFT.exe.c snapshot. It does not assign gameplay or physics semantics.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

FORMAT = "SHIFT.VehiclePhysicsSelectorDescriptorPopulation/1"


def build_vehicle_physics_selector_descriptor_population() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready",
        "ready": True,
        "storage": {
            "global_instance": "DAT_00bbc600",
            "capacity_field": "context+0x28",
            "capacity_value": 16,
            "count_field": "context+0x1c",
            "descriptor_base": "context+0xb8",
            "descriptor_stride": "0x90",
        },
        "population": {
            "function": "thunk_FUN_00d36a00",
            "destination": "context + index*0x90 + 0xb8",
            "valid_index_condition": "index < context+0x28",
            "wrapper": {
                "function": "thunk_FUN_00409290",
                "condition": "context+0x1c < context+0x28",
                "source": "source_record+0x10",
                "post_action": "context+0x1c += 1",
            },
            "packed_token": {
                "source": "uint32 at source_record+0x10",
                "descriptor_fields": {
                    "+0x00": "token bits 0..3",
                    "+0x04": "token bits 4..7",
                    "+0x08": "token bits 8..10",
                    "+0x0c": "token bits 11..14",
                    "+0x78": "token bits 15..18",
                    "+0x7d": "source byte at +0x14 bit 0",
                },
            },
            "strings": [
                {"source": "+0x05", "destination": "+0x10"},
                {"source": "+0x25", "destination": "+0x14"},
                {"source": "+0x45", "destination": "+0x18"},
                {"source": "+0x76", "destination": "+0x24"},
                {"source": "+0x96", "destination": "+0x28"},
            ],
            "copied_block": {
                "source": "+0xa8",
                "destination": "+0x38",
                "dword_count": 14,
                "byte_count": 56,
            },
            "derived_fields": {
                "+0x20": "thunk_FUN_00d36580(source_record, &temporary)",
                "+0x70": "FUN_00542620() when descriptor+0x08 == 0",
                "+0x74": 0,
                "+0x88": 0,
            },
            "post_population_side_effect": {
                "condition": "descriptor+0x00 == context+0x18",
                "action": "context+0x20 += 1",
            },
        },
        "selection_relation": {
            "selection_function": "thunk_FUN_0043af50",
            "eligible_test": "descriptor+0x74 == 0",
            "ordinal_writeback": "descriptor+0x8c = selected ordinal",
        },
        "evidence": [
            "FUN_00410490 constructs 16 repeated descriptor records using FUN_0040eec0.",
            "FUN_00410350 sets selector capacity context+0x28 to 0x10.",
            "FUN_00409290 gates population on count < capacity and increments count after thunk_FUN_00d36a00.",
            "thunk_FUN_00d36a00 packs source token bits into descriptor offsets +0x00/+0x04/+0x08/+0x0c/+0x78 and byte +0x7d.",
            "thunk_FUN_00d36a00 copies five source string regions to descriptor offsets +0x10/+0x14/+0x18/+0x24/+0x28.",
            "thunk_FUN_00d36a00 copies 14 dwords from source +0xa8 to descriptor +0x38.",
            "thunk_FUN_00d36a00 explicitly writes descriptor+0x74 = 0 and descriptor+0x88 = 0.",
            "thunk_FUN_00d36a00 conditionally initializes descriptor+0x70 through FUN_00542620 when descriptor+0x08 is zero.",
        ],
        "limitations": [
            "Packed fields are recorded as bit/offset transformations only; their gameplay or physics meanings are not inferred.",
            "The source-side record schema beyond the referenced offsets is not assigned a C++ type.",
            "String encodings/ownership are not promoted to a higher-level resource model.",
            "Runtime provider identity and numeric equivalence remain capture-dependent.",
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the source-backed selector descriptor population contract"
    )
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)

    report = build_vehicle_physics_selector_descriptor_population()
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["FORMAT", "build_vehicle_physics_selector_descriptor_population"]
