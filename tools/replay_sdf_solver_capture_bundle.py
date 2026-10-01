#!/usr/bin/env python3
"""Replay one verified portable SDF evidence bundle through Phase 637."""
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

from sdf_runtime_probe_evidence_bundle_replay import (  # noqa: E402
    replay_sdf_runtime_probe_evidence_bundle,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args(argv)

    report = replay_sdf_runtime_probe_evidence_bundle(args.archive)
    print(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
