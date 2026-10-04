#!/usr/bin/env python3
"""Build the fail-closed playable camera-follow source frontier."""
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

from camera_follow_source_frontier import build_camera_follow_source_frontier


def _load(path: str | Path) -> Mapping[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"JSON object expected: {path}")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--vehicle-world-matrix-handoff",
        help=(
            "optional SHIFT.NativeBMWVehicleWorldMatrixRuntimeHandoff/1 "
            "contract/report"
        ),
    )
    parser.add_argument("--json-out", help="optional report path")
    args = parser.parse_args(argv)

    world_handoff = (
        _load(args.vehicle_world_matrix_handoff)
        if args.vehicle_world_matrix_handoff
        else None
    )
    report = build_camera_follow_source_frontier(world_handoff)
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
                "status": report["status"],
                "ready": report["ready"],
                "process2_action": report["process2_action"],
                "proof_request_count": len(report["process1_requested_proof"]),
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
