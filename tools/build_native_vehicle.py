#!/usr/bin/env python3
"""Build a fail-closed native vehicle resource artifact from offline pipeline JSON."""
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

from offline_native_vehicle import build_native_vehicle_files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalog", help="SHIFT.OfflineResourceCatalog/1 JSON")
    parser.add_argument("bootstrap", help="SHIFT.SceneVehicleBootstrap/1 JSON")
    parser.add_argument(
        "physics_bundle",
        help="SHIFT.VehiclePhysicsBundleExtractor/1 JSON",
    )
    parser.add_argument("-o", "--output", required=True, help="output directory")
    parser.add_argument(
        "--require-runtime-physics-contract",
        action="store_true",
        help=(
            "return non-zero unless the current native runtime physics manifest "
            "contract is also ready"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_native_vehicle_files(
        args.catalog,
        args.bootstrap,
        args.physics_bundle,
        args.output,
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "resource_ready": report["resource_ready"],
        "runtime_physics_contract_ready": report["runtime_physics_contract_ready"],
        "native_vehicle_runtime_ready": report["native_vehicle_runtime_ready"],
        "blocking_reasons": report["blocking_reasons"],
        "artifacts": report.get("artifacts") or {},
    }, ensure_ascii=False, indent=2))
    if not report["resource_ready"]:
        return 2
    if args.require_runtime_physics_contract and not report["runtime_physics_contract_ready"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
