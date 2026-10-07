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

from offline_bootstrap_corpus_validation import (
    build_bootstrap_corpus_validation_files,
)
from offline_native_participant_handoff import (
    attach_participant_runtime_evidence_files,
)
from offline_resource_pipeline import (
    build_bootstrap_manifest,
    build_catalog,
    materialize_bff_inputs,
    run_offline_pipeline,
    write_catalog_bundle,
)
from offline_resource_loaders import load_track, load_vehicle
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


def _cmd_resource_load(args: argparse.Namespace, *, kind: str) -> int:
    catalog = _load(args.catalog)
    graph = _load(args.graph)
    if kind == "track":
        report = load_track(catalog, graph, track=args.track)
    elif kind == "vehicle":
        report = load_vehicle(catalog, graph, vehicle=args.vehicle)
    else:
        raise ValueError(f"unsupported resource load kind: {kind}")
    _write_json(args.output, report)
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "blocking_reasons": report["blocking_reasons"],
        "output": str(Path(args.output)),
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


def cmd_load_track(args: argparse.Namespace) -> int:
    return _cmd_resource_load(args, kind="track")


def cmd_load_vehicle(args: argparse.Namespace) -> int:
    return _cmd_resource_load(args, kind="vehicle")


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


def _attach_participant_if_requested(
    report: dict,
    *,
    output_dir: str | Path,
    participant_runtime_evidence: str | Path | None,
) -> dict:
    if participant_runtime_evidence is None:
        return report
    return attach_participant_runtime_evidence_files(
        Path(output_dir) / "native_resource_handoff.json",
        participant_runtime_evidence,
        output_dir,
    )


def cmd_native_handoff(args: argparse.Namespace) -> int:
    report = build_native_resource_handoff_files(
        args.catalog,
        args.bootstrap,
        args.physics_bundle,
        args.output,
        scene_set_dir=args.scene_set,
    )
    participant_source = getattr(args, "participant_runtime_evidence", None)
    report = _attach_participant_if_requested(
        report,
        output_dir=args.output,
        participant_runtime_evidence=participant_source,
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "resource_inputs_ready": report["resource_inputs_ready"],
        "participant_runtime_identity_evaluated": report.get(
            "participant_runtime_identity_evaluated", False
        ),
        "participant_runtime_identity_ready": report.get(
            "participant_runtime_identity_ready", False
        ),
        "participant_runtime_identity_blocking_reasons": report.get(
            "participant_runtime_identity_blocking_reasons", []
        ),
        "blocking_reasons": report["blocking_reasons"],
        "artifacts": report.get("artifacts") or {},
    }, ensure_ascii=False, indent=2))
    if not report["ready"]:
        return 2
    if (
        getattr(args, "require_participant_runtime_identity", False)
        and report.get("participant_runtime_identity_ready") is not True
    ):
        return 2
    return 0


def _augment_all_report_with_corpus_validation(
    report: dict,
    validation: dict,
    output_dir: str | Path,
) -> dict:
    """Attach corpus target readiness as diagnostics, never as selected-target admission."""
    out = Path(output_dir)
    combined = dict(report)
    combined["bootstrap_corpus_validation_status"] = validation.get("status")
    combined["bootstrap_corpus_validation_ready"] = validation.get("ready") is True
    combined["bootstrap_corpus_validation_summary"] = dict(
        validation.get("summary") or {}
    )
    combined["bootstrap_corpus_validation_blocking_reasons"] = list(
        validation.get("blocking_reasons") or []
    )
    artifacts = dict(report.get("artifacts") or {})
    artifacts["bootstrap_corpus_validation"] = str(
        out / "bootstrap_corpus_validation.json"
    )
    combined["artifacts"] = artifacts
    boundary = dict(report.get("boundary") or {})
    boundary["bootstrap_corpus_validation_automated"] = True
    boundary["bootstrap_corpus_validation_is_selected_target_admission"] = False
    boundary["unrelated_blocked_targets_block_selected_bootstrap"] = False
    combined["boundary"] = boundary
    _write_json(out / "pipeline_run.json", combined)
    return combined


def _augment_all_report_with_native_handoff(
    report: dict,
    handoff: dict,
    output_dir: str | Path,
    *,
    scene_set_dir: str | Path | None = None,
    participant_runtime_evidence: str | Path | None = None,
) -> dict:
    """Persist one-command resource/handoff status without claiming runtime readiness."""
    out = Path(output_dir)
    combined = dict(report)
    combined["native_resource_handoff_status"] = handoff.get("status")
    combined["native_resource_handoff_ready"] = handoff.get("ready") is True
    combined["native_resource_handoff_blocking_reasons"] = list(
        handoff.get("blocking_reasons") or []
    )
    combined["participant_runtime_identity_evaluated"] = handoff.get(
        "participant_runtime_identity_evaluated"
    ) is True
    combined["participant_runtime_identity_ready"] = handoff.get(
        "participant_runtime_identity_ready"
    ) is True
    combined["participant_runtime_identity_blocking_reasons"] = list(
        handoff.get("participant_runtime_identity_blocking_reasons") or []
    )
    inputs = dict(report.get("inputs") or {})
    inputs["runtime_proven_scene_set"] = (
        str(Path(scene_set_dir).resolve()) if scene_set_dir is not None else None
    )
    inputs["participant_runtime_evidence_source"] = (
        str(Path(participant_runtime_evidence).resolve())
        if participant_runtime_evidence is not None
        else None
    )
    combined["inputs"] = inputs
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
    boundary["runtime_proven_scene_set_recorded"] = scene_set_dir is not None
    boundary["participant_runtime_evidence_transport_automated"] = (
        participant_runtime_evidence is not None
    )
    boundary["participant_runtime_evidence_transport_is_runtime_execution"] = False
    combined["boundary"] = boundary
    _write_json(out / "pipeline_run.json", combined)
    return combined


def _record_selected_target(
    report: dict,
    *,
    track: str,
    vehicle: str,
) -> dict:
    """Persist requested target labels without treating names as identity proof."""
    combined = dict(report)
    combined["track"] = str(track)
    combined["vehicle"] = str(vehicle)
    boundary = dict(report.get("boundary") or {})
    boundary["selected_target_labels_recorded"] = True
    boundary["selected_target_labels_are_retail_identity_proof"] = False
    combined["boundary"] = boundary
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
    report = _record_selected_target(
        report,
        track=args.track,
        vehicle=args.vehicle,
    )
    validation = build_bootstrap_corpus_validation_files(
        out / "resource_catalog.json",
        out / "dependency_graph.json",
        out / "bootstrap_corpus_validation.json",
    )
    report = _augment_all_report_with_corpus_validation(
        report,
        validation,
        out,
    )
    handoff = build_native_resource_handoff_files(
        out / "resource_catalog.json",
        out / "scene_vehicle_bootstrap.json",
        out / "vehicle_physics_bundle_report.json",
        out / "native-handoff",
        scene_set_dir=args.scene_set,
    )
    participant_source = getattr(args, "participant_runtime_evidence", None)
    handoff = _attach_participant_if_requested(
        handoff,
        output_dir=out / "native-handoff",
        participant_runtime_evidence=participant_source,
    )
    report = _augment_all_report_with_native_handoff(
        report,
        handoff,
        out,
        scene_set_dir=args.scene_set,
        participant_runtime_evidence=participant_source,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["resource_bootstrap_ready"]:
        return 2
    if args.require_native_resource_handoff and not report["native_resource_handoff_ready"]:
        return 2
    if (
        getattr(args, "require_participant_runtime_identity", False)
        and not report["participant_runtime_identity_ready"]
    ):
        return 2
    return 0


def _add_participant_runtime_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--participant-runtime-evidence",
        help=(
            "optional ready SHIFT.NativePhysicsParticipantRuntimeEvidence/1; "
            "copied byte-for-byte into the native handoff and bound by SHA-256"
        ),
    )
    parser.add_argument(
        "--require-participant-runtime-identity",
        action="store_true",
        help="return non-zero unless transported participant runtime identity is ready",
    )


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

    load_track_cmd = sub.add_parser(
        "load-track",
        help="select one exact track resource graph from an existing catalog",
    )
    load_track_cmd.add_argument("catalog", help="SHIFT.OfflineResourceCatalog/1 JSON")
    load_track_cmd.add_argument("graph", help="SHIFT.OfflineResourceDependencyGraph/1 JSON")
    load_track_cmd.add_argument("--track", required=True, help="archive stem, e.g. Silverstone_Era3_GrandPrix")
    load_track_cmd.add_argument("-o", "--output", required=True, help="SHIFT.OfflineTrackLoad/1 output")
    load_track_cmd.set_defaults(fn=cmd_load_track)

    load_vehicle_cmd = sub.add_parser(
        "load-vehicle",
        help="select one exact vehicle resource graph from an existing catalog",
    )
    load_vehicle_cmd.add_argument("catalog", help="SHIFT.OfflineResourceCatalog/1 JSON")
    load_vehicle_cmd.add_argument("graph", help="SHIFT.OfflineResourceDependencyGraph/1 JSON")
    load_vehicle_cmd.add_argument("--vehicle", required=True, help="archive stem, e.g. Ford_Mustang_2010")
    load_vehicle_cmd.add_argument("-o", "--output", required=True, help="SHIFT.OfflineVehicleLoad/1 output")
    load_vehicle_cmd.set_defaults(fn=cmd_load_vehicle)

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
    _add_participant_runtime_args(native_handoff)
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
    _add_participant_runtime_args(all_cmd)
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
