#!/usr/bin/env python3
"""Build the source-backed PhysicsParticipantManager event-0x20 contract."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from physics_participant_manager_event_runtime import build_physics_participant_manager_event


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_physics_participant_manager_event()
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(json.dumps(
        {
            "format": report["format"],
            "status": report["status"],
            "ready": report["ready"],
            "event_opcode": report["event"]["opcode"],
            "event_producer": report["event"]["producer"],
            "dispatch_target": report["event"]["dispatch_target"],
            "manager_ready_field": report["manager"]["ready_field"],
            "causal_link_proven": report["relationship_to_phase505"]["causal_link_proven"],
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
