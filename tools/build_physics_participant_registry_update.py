#!/usr/bin/env python3
"""Build the source-backed physics participant registry/update contract."""
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

from physics_participant_registry_update_runtime import build_physics_participant_registry_update


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)

    report = build_physics_participant_registry_update()
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")

    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "manager_global": report["manager"]["global_instance"],
        "slot_stride": report["manager"]["allocated_entry_stride"],
        "registration": report["registration"]["function"],
        "update": report["update"]["function"],
        "phase505_same_object_proven": report["relationship_to_phase505"]["same_object_proven"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
