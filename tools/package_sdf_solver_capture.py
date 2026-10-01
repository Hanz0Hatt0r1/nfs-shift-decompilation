#!/usr/bin/env python3
"""Package one SDF runtime capture into a deterministic portable evidence ZIP."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
PHYSICS_SRC = ROOT / "src" / "physics"
for path in (ROOT, PHYSICS_SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from sdf_runtime_probe_evidence_bundle import (  # noqa: E402
    build_sdf_runtime_probe_evidence_bundle,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture_directory", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)

    report = build_sdf_runtime_probe_evidence_bundle(
        args.capture_directory,
        output_path=args.output,
    )
    print(
        json.dumps(
            {
                "format": report["format"],
                "ready": report["ready"],
                "capture_ready": report["capture_ready"],
                "file_count": report["file_count"],
                "archive": report["archive"],
                "errors": report["errors"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
