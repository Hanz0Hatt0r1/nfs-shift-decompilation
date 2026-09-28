"""Describe the source-backed PhysicsParticipantManager event-0x20 path.

This contract intentionally stops short of claiming that event 0x20 is the
same registry-population path later consumed by FUN_00410ef0. The decompilation
does prove that the event is produced with opcode 0x20, dispatched by the
physics event loop, consumed by FUN_00714560 on DAT_00c109e0, and that the
consumer marks manager state at +0x39c ready.
"""
from __future__ import annotations

import argparse
import json
from typing import Any, Sequence

FORMAT = "SHIFT.PhysicsParticipantManagerEvent/1"


def build_physics_participant_manager_event() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready",
        "ready": True,
        "manager": {
            "global_instance": "DAT_00c109e0",
            "consumer": "FUN_00714560",
            "consumer_source_file": ".\\Source\\System\\PhysicsParticipantManager.cpp",
            "ready_field": "+0x39c",
            "ready_value": 1,
            "configuration": {
                "copy_source_bytes": "event+0x0c..+0x88 inclusive (31 dwords)",
                "count_source": "event+0xb0",
                "nested_entry_source": "event+0x8c",
                "optional_byte_blob": "FUN_006327f0(event)",
                "optional_blob_destination": "manager+0x3a4",
                "optional_blob_length": "manager+0x3a8",
                "output_count": "manager+0x3b0",
                "copied_settings": "manager+0x3b4..+0x430",
            },
        },
        "event": {
            "opcode": "0x20",
            "channel": 3,
            "producer": "FUN_0070e1c0",
            "producer_payload": "param_2 bytes copied into event payload after opcode/channel setup",
            "dispatchers": [
                "FUN_00711210",
                "FUN_007112d8",
            ],
            "dispatch_target": "FUN_00714560(&DAT_00c109e0, event)",
        },
        "source_evidence": [
            "FUN_0070e1c0 writes channel/type byte +5 = 3 and opcode byte +4 = 0x20 before copying the payload.",
            "FUN_00711210 routes opcode 0x20 to FUN_00714560 on DAT_00c109e0.",
            "FUN_007112d8 contains the same opcode-0x20 dispatch to FUN_00714560.",
            "FUN_00714560 copies 31 dwords from the event payload, imports the event count and nested entries, and sets manager+0x39c to 1.",
            "The decompilation contains source-path assertions in PhysicsParticipantManager.cpp at lines 0x424 and 0x425.",
        ],
        "relationship_to_phase505": {
            "participant_selector": "FUN_00410ef0",
            "selector_reads_manager": False,
            "causal_link_proven": False,
            "note": "The source proves both paths exist, but does not establish that DAT_00c109e0 is the exact registry returned by thunk_FUN_00453990. Keep the manager-event path as a separate evidence layer until runtime or stronger cross-reference evidence closes the join.",
        },
        "limitations": [
            "Opcode 0x20 is an observed internal event type; no higher-level event class name is invented.",
            "Manager +0x39c is recorded as an observed ready field, not assigned an engine semantic beyond that observation.",
            "No PhysX SDK class or runtime participant identity is inferred.",
            "The event-to-FUN_00410ef0 registry causal relationship remains unproven.",
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the source-backed PhysicsParticipantManager event-0x20 contract"
    )
    parser.add_argument("-o", "--output")
    args = parser.parse_args(argv)

    report = build_physics_participant_manager_event()
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


__all__ = ["FORMAT", "build_physics_participant_manager_event"]
