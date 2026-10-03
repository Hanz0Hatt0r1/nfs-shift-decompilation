#!/usr/bin/env python3
"""High-level offline SHIFT resource pipeline: BFFs -> catalog/dependencies/bootstrap."""
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

from offline_resource_pipeline import (
    build_bootstrap_manifest,
    build_catalog,
    materialize_bff_inputs,
    run_offline_pipeline,
    write_catalog_bundle,
)
from offline_native_resource_handoff import build_native_resource_handoff_files


def _load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: str | Path, value: dict) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def cmd_catalog(args: argparse.Namespace) -> int:
    with materialize_bff_inputs(args.inputs) as archives:
        catalog, graph, coverage = build_catalog(
            archives,
            decode_known=args.decode_known,
            decode_limit_per_archive=args.decode_limit_per_archive,
        )
    out = Path(args.output)
    write_catalog_bundle(out, catalog, graph, coverage)
    print(json.dumps({
        "format": catalog["format"],
        "archives": catalog["summary"]["archives"],
        "resources": catalog["summary"]["resources"],
        "unknown_extensions": coverage["unknown_extensions"],
        "parsed": coverage["parsed"],
        "blocked": coverage["blocked"],
        "unsupported": coverage["unsupported"],
        "dependency_blockers": graph["summary"]["blocking_admissible_edges"],
        "output": str(out),
    }, ensure_ascii=False, indent=2))
    return 0 if coverage["blocked"] == 0 else 2


def cmd_bootstrap(args: argparse.Namespace) -> int:
    catalog = _load(args.catalog)
    graph = _load(args.graph)
    bootstrap, admission = build_bootstrap_manifest(
        catalog,
        graph,
        track=args.track,
        vehicle=args.vehicle,
    )
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(
        json.dumps(bootstrap, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    Path(args.admission).parent.mkdir(parents=True, exist_ok=True)
    Path(args.admission).write_text(
        json.dumps(admission, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": bootstrap["format"],
        "status": bootstrap["status"],
        "ready": bootstrap["ready"],
        "blocking_reasons": bootstrap["blocking_reasons"],
        "native_admission_status": admission["status"],
    }, ensure_ascii=False, indent=2))
    return 0 if bootstrap["ready"] else 2


def cmd_native_handoff(args: argparse.Namespace) -> int:
    report = build_native_resource_handoff_files(
        args.catalog,
        args.bootstrap,
        args.physics_bundle,
        args.output,
        scene_set_dir=args.scene_set,
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "resource_inputs_ready": report["resource_inputs_ready"],
        "blocking_reasons": report["blocking_reasons"],
        "artifacts": report.get("artifacts") or {},
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


def _augment_all_report_with_native_handoff(
    report: dict,
    handoff: dict,
    output_dir: str | Path,
) -> dict:
    """Persist one-command resource/handoff status without claiming runtime readiness."""
    out = Path(output_dir)
    combined = dict(report)
    combined["native_resource_handoff_status"] = handoff.get("status")
    combined["native_resource_handoff_ready"] = handoff.get("ready") is True
    combined["native_resource_handoff_blocking_reasons"] = list(
        handoff.get("blocking_reasons") or []
    )
    artifacts = dict(report.get("artifacts") or {})
    artifacts["native_resource_handoff"] = str(
        out / "native-handoff" / "native_resource_handoff.json"
    )
    for name, row in (handoff.get("artifacts") or {}).items():
        if isinstance(row, dict) and row.get("path"):
            artifacts[f"native_handoff_{name}"] = str(row["path"])
    combined["artifacts"] = artifacts
    boundary = dict(report.get("boundary") or {})
    boundary["native_resource_handoff_automated"] = True
    boundary["native_resource_handoff_is_runtime_execution"] = False
    combined["boundary"] = boundary
    _write_json(out / "pipeline_run.json", combined)
    return combined


def cmd_all(args: argparse.Namespace) -> int:
    out = Path(args.output)
    report = run_offline_pipeline(
        args.inputs,
        out,
        track=args.track,
        vehicle=args.vehicle,
        decode_limit_per_archive=args.decode_limit_per_archive,
    )
    handoff = build_native_resource_handoff_files(
        out / "resource_catalog.json",
        out / "scene_vehicle_bootstrap.json",
        out / "vehicle_physics_bundle_report.json",
        out / "native-handoff",
        scene_set_dir=args.scene_set,
    )
    report = _augment_all_report_with_native_handoff(report, handoff, out)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["resource_bootstrap_ready"]:
        return 2
    if args.require_native_resource_handoff and not report["native_resource_handoff_ready"]:
        return 2
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    catalog = sub.add_parser("catalog", help="index BFF inputs and optionally run known parsers")
    catalog.add_argument("inputs", nargs="+", help=".bff, .zip, or directories containing BFFs")
    catalog.add_argument("-o", "--output", required=True, help="output directory")
    catalog.add_argument("--decode-known", action="store_true", help="decode only extensions with concrete parsers")
    catalog.add_argument(
        "--decode-limit-per-archive",
        type=int,
        default=0,
        help="limit parser attempts per BFF; 0 means full known-format corpus",
    )
    catalog.set_defaults(fn=cmd_catalog)

    bootstrap = sub.add_parser("bootstrap", help="build exact scene+vehicle bootstrap from catalog/graph")
    bootstrap.add_argument("catalog")
    bootstrap.add_argument("graph")
    bootstrap.add_argument("--track", required=True, help="archive stem, e.g. Silverstone_Era3_GrandPrix")
    bootstrap.add_argument("--vehicle", required=True, help="archive stem, e.g. Ford_Mustang_2010")
    bootstrap.add_argument("-o", "--output", required=True)
    bootstrap.add_argument("--admission", required=True)
    bootstrap.set_defaults(fn=cmd_bootstrap)

    native_handoff = sub.add_parser(
        "native-handoff",
        help="join resource bootstrap to existing native scene/physics gates",
    )
    native_handoff.add_argument("catalog", help="SHIFT.OfflineResourceCatalog/1 JSON")
    native_handoff.add_argument("bootstrap", help="SHIFT.SceneVehicleBootstrap/1 JSON")
    native_handoff.add_argument(
        "physics_bundle",
        help="SHIFT.VehiclePhysicsBundleExtractor/1 JSON from the all pipeline",
    )
    native_handoff.add_argument("-o", "--output", required=True, help="output directory")
    native_handoff.add_argument(
        "--scene-set",
        help=(
            "existing runtime-proven SHIFT.NativeSceneVulkanSet/1 directory; "
            "when omitted the render side remains explicitly blocked"
        ),
    )
    native_handoff.set_defaults(fn=cmd_native_handoff)

    all_cmd = sub.add_parser(
        "all",
        help="run catalog + validation + graph + bootstrap + native resource handoff",
    )
    all_cmd.add_argument("inputs", nargs="+", help=".bff, .zip, or directories containing BFFs")
    all_cmd.add_argument("-o", "--output", required=True, help="output directory")
    all_cmd.add_argument("--track", required=True)
    all_cmd.add_argument("--vehicle", required=True)
    all_cmd.add_argument(
        "--scene-set",
        help=(
            "optional existing runtime-proven native scene-set directory; "
            "never synthesized from static resources"
        ),
    )
    all_cmd.add_argument(
        "--require-native-resource-handoff",
        action="store_true",
        help="return non-zero unless the native scene/physics resource-input join is ready",
    )
    all_cmd.add_argument(
        "--decode-limit-per-archive",
        type=int,
        default=0,
        help="limit parser attempts per BFF; 0 runs the complete known-format corpus",
    )
    all_cmd.set_defaults(fn=cmd_all)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "decode_limit_per_archive", 0) < 0:
        parser.error("--decode-limit-per-archive must be non-negative")
    return int(args.fn(args))


if __name__ == "__main__":
    raise SystemExit(main())
