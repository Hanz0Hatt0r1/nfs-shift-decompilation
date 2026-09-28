#!/usr/bin/env python3
"""Build the source-backed vehicle physics selector-context contract."""
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

from vehicle_physics_selector_context_runtime import build_vehicle_physics_selector_context


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)

    report = build_vehicle_physics_selector_context()
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")

    print(json.dumps(
        {
            "format": report["format"],
            "status": report["status"],
            "ready": report["ready"],
            "selector_global": report["context"]["global_instance"],
            "selector_storage": report["context"]["member_selector_field"],
            "descriptor_stride": report["context"]["descriptor_stride"],
            "manager_global": report["separation"]["participant_manager_global"],
            "same_object_proven": report["separation"]["same_object_proven"],
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
