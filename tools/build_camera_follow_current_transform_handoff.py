#!/usr/bin/env python3
"""Build the Process 1D current-vehicle-transform camera handoff."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
CAMERA = ROOT / "src" / "camera"
for path in (ROOT, CAMERA):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from camera_follow_current_transform_handoff import build_handoff  # noqa: E402
from camera_follow_source_frontier import build_camera_follow_source_frontier  # noqa: E402

DEFAULT_WORLD_WIRING = ROOT / "evidence" / "bmw_persistent_world_transform_runtime_wiring.json"


def _load(path: str | Path) -> Mapping[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"JSON object expected: {path}")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--world-wiring",
        default=str(DEFAULT_WORLD_WIRING),
        help="SHIFT.BMWPersistentWorldTransformRuntimeWiring/1 evidence JSON",
    )
    parser.add_argument("--json-out", help="optional report path")
    args = parser.parse_args(argv)

    camera = build_camera_follow_source_frontier()
    report = build_handoff(camera, _load(args.world_wiring))
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"

    if args.json_out:
        output = Path(args.json_out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")

    print(
        json.dumps(
            {
                "format": report["format"],
                "ready": report["ready"],
                "status": report["status"],
                "process2_action": report["process2_action"],
            },
            sort_keys=True,
        ),
        file=sys.stderr,
    )
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
