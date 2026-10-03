#!/usr/bin/env python3
"""Build the strongest fail-closed native bootstrap from SHIFT BFF/ZIP inputs."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if SRC.is_dir():
    paths = [SRC]
    paths.extend(sorted(
        (path for path in SRC.rglob("*") if path.is_dir()),
        key=lambda path: (len(path.parts), str(path)),
    ))
    for path in reversed(paths):
        value = str(path)
        if value not in sys.path:
            sys.path.insert(0, value)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from offline_runtime_bootstrap import build_offline_runtime_bootstrap


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", help="BFF, ZIP, or directory inputs")
    parser.add_argument("-o", "--output", required=True, help="bootstrap output directory")
    parser.add_argument("--track", required=True, help="exact track archive stem")
    parser.add_argument("--vehicle", required=True, help="exact vehicle archive stem")
    parser.add_argument(
        "--decode-limit-per-archive",
        type=int,
        default=0,
        help="known-parser attempt limit per archive; 0 means complete known corpus",
    )
    parser.add_argument(
        "--root-consensus",
        help="optional existing SHIFT.SGBMultiMatrixRootConsensus/1 evidence",
    )
    parser.add_argument(
        "--runtime-shader-admission",
        help="optional exact runtime shader admission evidence",
    )
    parser.add_argument(
        "--require-runtime-ready",
        action="store_true",
        help="return non-zero unless all runtime gates are proven ready",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.decode_limit_per_archive < 0:
        parser.error("--decode-limit-per-archive must be non-negative")

    report = build_offline_runtime_bootstrap(
        args.inputs,
        args.output,
        track=args.track,
        vehicle=args.vehicle,
        decode_limit_per_archive=args.decode_limit_per_archive,
        root_consensus_path=args.root_consensus,
        runtime_shader_admission_path=args.runtime_shader_admission,
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "offline_build_ready": report["offline_build_ready"],
        "runtime_ready": report["runtime_ready"],
        "track": report["track"],
        "vehicle": report["vehicle"],
        "readiness": report["readiness"],
        "blocking_reasons": report["blocking_reasons"],
        "output": str(Path(args.output) / "runtime_bootstrap.json"),
    }, ensure_ascii=False, indent=2))

    if not report["offline_build_ready"]:
        return 2
    if args.require_runtime_ready and not report["runtime_ready"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
