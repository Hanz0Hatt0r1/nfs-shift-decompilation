#!/usr/bin/env python3
"""Run Silverstone renderer production from raw/static sources with no base/618 handoff.

Phase 635 composes the existing exact stages in dependency order:

raw capture bootstrap -> Phase 634 ambiguity regeneration -> Phase 633 base audit
regeneration -> Phase 619-626 production.

When an exact OfflineRuntimeBootstrap report is supplied, Phase 638 also
regenerates the optional Phase 595 OBJECT candidate join from its hashed scene
artifacts plus the newly regenerated capture pipeline. Bundle copies remain
canonical cross-checks only and cannot override a blocked regenerated source.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from index_silverstone_renderer_report_bundle import index_report_bundles
from regenerate_renderer_object_candidate_join import regenerate_object_candidate_join
from run_silverstone_renderer_ambiguity_regeneration import run_ambiguity_regeneration
from run_silverstone_renderer_base_audit_regeneration import regenerate_renderer_base_audit
from run_silverstone_renderer_hybrid_production import (
    _choose_shader_targets,
    _crosscheck_report,
    _identity_set,
    _load_json_map,
    _report_rows,
    _write_json_atomic,
)
from run_silverstone_renderer_production import run_production
from run_silverstone_renderer_raw_capture_bootstrap import run_raw_capture_bootstrap

FORMAT = "SHIFT.SilverstoneRendererSelfBootstrapProductionRun/1"
TARGET_FORMAT = "SHIFT.IMBRuntimeShaderTargetSet/1"
AMBIGUITY_FORMAT = "SHIFT.IMBDrawLocalAmbiguityAudit/1"
BASE_AUDIT_FORMAT = "SHIFT.D3D9RendererRequirementAudit/1"

TOLERATED_BUNDLE_REPORT_KEYS = {
    "base_audit",
    "ambiguity_audit",
    "draw_local",
    "capture_pipeline",
    "object_candidate_join",
    "runtime_shader_targets",
}


def _bundle_blockers(
    index_manifest: Mapping[str, Any],
) -> tuple[list[str], list[str]]:
    fatal: list[str] = []
    tolerated: list[str] = []
    for raw in index_manifest.get("blocking_reasons") or []:
        reason = str(raw)
        if reason.startswith("report:"):
            parts = reason.split(":", 2)
            key = parts[1] if len(parts) > 1 else ""
            if key in TOLERATED_BUNDLE_REPORT_KEYS:
                tolerated.append(reason)
                continue
        fatal.append(reason)
    return list(dict.fromkeys(fatal)), list(dict.fromkeys(tolerated))


def _full_target_set_gate(path: str | Path) -> tuple[Mapping[str, Any] | None, list[str]]:
    blockers: list[str] = []
    try:
        value = _load_json_map(path)
    except Exception as exc:
        blockers.append(f"unreadable:{type(exc).__name__}:{exc}")
        return None, blockers
    if value.get("format") != TARGET_FORMAT:
        blockers.append(
            f"format-mismatch:{value.get('format')!r}:full-{TARGET_FORMAT}-required"
        )
        return None, blockers
    bindings = value.get("binding_targets")
    if not isinstance(bindings, list):
        blockers.append("binding_targets-missing")
        return None, blockers
    return value, blockers


def _generated_output(
    manifest: Mapping[str, Any] | None,
    key: str,
) -> str | None:
    if not isinstance(manifest, Mapping):
        return None
    outputs = manifest.get("outputs")
    if not isinstance(outputs, Mapping):
        return None
    value = outputs.get(key)
    return str(value) if value else None


def run_self_bootstrap_production(
    *,
    bundles: list[str | Path],
    capture_jsonl: str | Path,
    output_dir: str | Path,
    corpus: list[str | Path],
    pe_evidence: str | Path | None = None,
    pe_image: str | Path | None = None,
    runtime_shader_targets: str | Path | None = None,
    runtime_bootstrap: str | Path | None = None,
    max_json_bytes: int = 128 * 1024 * 1024,
) -> dict[str, Any]:
    out = Path(output_dir)
    bundle_dir = out / "bundle"
    raw_dir = out / "raw"
    object_dir = out / "object-candidate"
    ambiguity_dir = out / "ambiguity"
    base_dir = out / "base-audit"
    production_dir = out / "production"

    index_manifest = index_report_bundles(
        bundles,
        output_dir=bundle_dir,
        max_json_bytes=max_json_bytes,
    )
    rows = _report_rows(index_manifest)
    normalized = index_manifest.get("normalized_outputs")
    normalized = normalized if isinstance(normalized, Mapping) else {}
    fatal_bundle, tolerated_bundle = _bundle_blockers(index_manifest)
    blockers = [f"bundle:{reason}" for reason in fatal_bundle]

    chosen_targets, target_provenance, target_blockers = _choose_shader_targets(
        index_manifest,
        explicit=runtime_shader_targets,
    )
    blockers.extend(target_blockers)
    _target_value, full_target_blockers = _full_target_set_gate(chosen_targets)
    blockers.extend(
        f"runtime_shader_targets:{reason}" for reason in full_target_blockers
    )
    target_provenance = {
        **target_provenance,
        "required_format": TARGET_FORMAT,
        "full_target_set_ready": not full_target_blockers,
    }

    raw_manifest: Mapping[str, Any] | None = None
    raw_started = not blockers
    if raw_started:
        try:
            raw_manifest = run_raw_capture_bootstrap(
                capture_jsonl=capture_jsonl,
                pe_evidence=pe_evidence,
                pe_image=pe_image,
                runtime_shader_targets=chosen_targets,
                output_dir=raw_dir,
            )
        except Exception as exc:
            blockers.append(f"raw:failed:{type(exc).__name__}:{exc}")
            raw_manifest = None
        if isinstance(raw_manifest, Mapping):
            blockers.extend(
                f"raw:{reason}"
                for reason in (raw_manifest.get("blocking_reasons") or [])
            )

    crosschecks: list[dict[str, Any]] = []
    raw_outputs = (
        raw_manifest.get("outputs")
        if isinstance(raw_manifest, Mapping)
        and isinstance(raw_manifest.get("outputs"), Mapping)
        else {}
    )
    for key in ("draw_local", "capture_pipeline"):
        if isinstance(raw_manifest, Mapping):
            check, reasons = _crosscheck_report(
                key,
                raw_outputs.get(key),
                rows.get(key),
            )
            crosschecks.append(check)
            blockers.extend(reasons)
        else:
            crosschecks.append({
                "key": key,
                "status": "raw-bootstrap-not-run",
                "regenerated_path": None,
                "regenerated_canonical_sha256": None,
                "bundle_status": (
                    rows.get(key, {}).get("status")
                    if isinstance(rows.get(key), Mapping)
                    else None
                ),
                "bundle_canonical_sha256": _identity_set(rows.get(key)),
                "selection_claim": False,
            })

    raw_ready = (
        isinstance(raw_manifest, Mapping)
        and raw_manifest.get("ready") is True
    )
    draw_local_path = (
        str(raw_outputs.get("draw_local"))
        if raw_outputs.get("draw_local")
        else None
    )
    capture_pipeline_path = (
        str(raw_outputs.get("capture_pipeline"))
        if raw_outputs.get("capture_pipeline")
        else None
    )

    object_source_supplied = runtime_bootstrap is not None
    object_regeneration: Mapping[str, Any] | None = None
    object_regenerated_path: str | None = None
    object_crosscheck: Mapping[str, Any] | None = None
    object_optional_blockers: list[str] = []
    if object_source_supplied and raw_ready and capture_pipeline_path:
        try:
            object_regeneration = regenerate_object_candidate_join(
                runtime_bootstrap=runtime_bootstrap,
                capture_pipeline=capture_pipeline_path,
                output_dir=object_dir,
            )
        except Exception as exc:
            blockers.append(
                f"object_candidate_regeneration:failed:{type(exc).__name__}:{exc}"
            )
            object_regeneration = None
        if isinstance(object_regeneration, Mapping):
            source_ready = object_regeneration.get("source_ready") is True
            join_ready = object_regeneration.get("ready") is True
            reasons = [
                f"object_candidate_regeneration:{reason}"
                for reason in (object_regeneration.get("blocking_reasons") or [])
            ]
            if not source_ready:
                blockers.extend(reasons or [
                    "object_candidate_regeneration:source-not-ready"
                ])
            elif not join_ready:
                object_optional_blockers.extend(reasons or [
                    "object_candidate_regeneration:join-not-ready"
                ])
            else:
                object_regenerated_path = _generated_output(
                    object_regeneration,
                    "object_candidate_join",
                )
                if not object_regenerated_path:
                    blockers.append(
                        "object_candidate_regeneration:ready-without-output"
                    )
                else:
                    check, reasons = _crosscheck_report(
                        "object_candidate_join",
                        object_regenerated_path,
                        rows.get("object_candidate_join"),
                    )
                    object_crosscheck = check
                    blockers.extend(reasons)
    elif object_source_supplied and raw_ready:
        blockers.append(
            "object_candidate_regeneration:capture-pipeline-unavailable"
        )

    ambiguity_manifest: Mapping[str, Any] | None = None
    ambiguity_path: str | None = None
    ambiguity_crosscheck: Mapping[str, Any] | None = None
    if raw_ready and draw_local_path and not blockers:
        try:
            ambiguity_manifest = run_ambiguity_regeneration(
                capture_jsonl=capture_jsonl,
                runtime_shader_targets=chosen_targets,
                draw_local=draw_local_path,
                corpus=corpus,
                output_dir=ambiguity_dir,
            )
        except Exception as exc:
            blockers.append(
                f"ambiguity_regeneration:failed:{type(exc).__name__}:{exc}"
            )
            ambiguity_manifest = None
        if isinstance(ambiguity_manifest, Mapping):
            blockers.extend(
                f"ambiguity_regeneration:{reason}"
                for reason in (ambiguity_manifest.get("blocking_reasons") or [])
            )
            ambiguity_path = _generated_output(
                ambiguity_manifest,
                "phase618_ambiguity",
            )
            check, reasons = _crosscheck_report(
                "ambiguity_audit",
                ambiguity_path,
                rows.get("ambiguity_audit"),
            )
            ambiguity_crosscheck = check
            blockers.extend(reasons)
            if ambiguity_path:
                try:
                    ambiguity_value = _load_json_map(ambiguity_path)
                    if ambiguity_value.get("format") != AMBIGUITY_FORMAT:
                        blockers.append(
                            "ambiguity_regeneration:phase618-format-mismatch"
                        )
                except Exception as exc:
                    blockers.append(
                        f"ambiguity_regeneration:phase618-unreadable:{type(exc).__name__}:{exc}"
                    )
    elif not draw_local_path:
        blockers.append("ambiguity_regeneration:draw-local-unavailable")

    ambiguity_ready = (
        isinstance(ambiguity_manifest, Mapping)
        and ambiguity_manifest.get("ready") is True
        and bool(ambiguity_path)
    )

    base_manifest: Mapping[str, Any] | None = None
    base_path: str | None = None
    base_crosscheck: Mapping[str, Any] | None = None
    if ambiguity_ready and draw_local_path and not blockers:
        try:
            base_manifest = regenerate_renderer_base_audit(
                capture_jsonl=capture_jsonl,
                runtime_shader_targets=chosen_targets,
                draw_local=draw_local_path,
                ambiguity_audit=ambiguity_path,
                output_dir=base_dir,
            )
        except Exception as exc:
            blockers.append(
                f"base_regeneration:failed:{type(exc).__name__}:{exc}"
            )
            base_manifest = None
        if isinstance(base_manifest, Mapping):
            blockers.extend(
                f"base_regeneration:{reason}"
                for reason in (base_manifest.get("blocking_reasons") or [])
            )
            base_path = _generated_output(base_manifest, "base_audit")
            check, reasons = _crosscheck_report(
                "base_audit",
                base_path,
                rows.get("base_audit"),
            )
            base_crosscheck = check
            blockers.extend(reasons)
            if base_path:
                try:
                    base_value = _load_json_map(base_path)
                    if base_value.get("format") != BASE_AUDIT_FORMAT:
                        blockers.append(
                            "base_regeneration:base-audit-format-mismatch"
                        )
                except Exception as exc:
                    blockers.append(
                        f"base_regeneration:base-audit-unreadable:{type(exc).__name__}:{exc}"
                    )
    elif not ambiguity_ready:
        blockers.append("base_regeneration:ambiguity-audit-unavailable")

    base_ready = (
        isinstance(base_manifest, Mapping)
        and base_manifest.get("ready") is True
        and bool(base_path)
    )

    bundle_object_path = normalized.get("object_candidate_join")
    if object_source_supplied:
        selected_object_path = object_regenerated_path
        object_mode = "regenerated-from-runtime-bootstrap"
    else:
        selected_object_path = bundle_object_path
        object_mode = "bundle-optional"

    unique_blockers = list(dict.fromkeys(str(value) for value in blockers))
    production_manifest: Mapping[str, Any] | None = None
    production_started = False
    if not unique_blockers and raw_ready and ambiguity_ready and base_ready:
        production_started = True
        try:
            production_manifest = run_production(
                output_dir=production_dir,
                corpus=corpus,
                base_audit=base_path,
                ambiguity_audit=ambiguity_path,
                runtime_shader_targets=chosen_targets,
                draw_local=raw_outputs.get("draw_local"),
                capture_pipeline=raw_outputs.get("capture_pipeline"),
                object_candidate_join=selected_object_path,
            )
        except Exception as exc:
            unique_blockers.append(
                f"production:failed:{type(exc).__name__}:{exc}"
            )
            production_manifest = None
        if isinstance(production_manifest, Mapping):
            unique_blockers.extend(
                f"production:{reason}"
                for reason in (production_manifest.get("blocking_reasons") or [])
            )
        unique_blockers = list(dict.fromkeys(unique_blockers))

    production_status = (
        production_manifest.get("status")
        if isinstance(production_manifest, Mapping)
        else None
    )
    ready = (
        production_started
        and production_status == "completed"
        and not unique_blockers
    )

    object_row = rows.get("object_candidate_join")
    object_input = {
        "mode": object_mode,
        "runtime_bootstrap": (
            str(runtime_bootstrap) if runtime_bootstrap is not None else None
        ),
        "regeneration_format": (
            object_regeneration.get("format")
            if isinstance(object_regeneration, Mapping)
            else None
        ),
        "regeneration_status": (
            object_regeneration.get("status")
            if isinstance(object_regeneration, Mapping)
            else None
        ),
        "regeneration_source_ready": (
            object_regeneration.get("source_ready") is True
            if isinstance(object_regeneration, Mapping)
            else False
        ),
        "regeneration_ready": (
            object_regeneration.get("ready") is True
            if isinstance(object_regeneration, Mapping)
            else False
        ),
        "regeneration_blocking_reasons": (
            list(object_regeneration.get("blocking_reasons") or [])
            if isinstance(object_regeneration, Mapping)
            else []
        ),
        "optional_unresolved_blocking_reasons": object_optional_blockers,
        "regenerated_path": object_regenerated_path,
        "regeneration_manifest": (
            str(object_dir / "renderer_object_candidate_regeneration.json")
            if isinstance(object_regeneration, Mapping)
            else None
        ),
        "bundle_status": (
            object_row.get("status") if isinstance(object_row, Mapping) else None
        ),
        "bundle_canonical_sha256": _identity_set(object_row),
        "bundle_normalized_path": bundle_object_path,
        "crosscheck": (
            dict(object_crosscheck)
            if isinstance(object_crosscheck, Mapping)
            else None
        ),
        "selected_path": selected_object_path,
        "passed_to_production": bool(
            production_started and selected_object_path
        ),
        "bundle_fallback_used": (
            not object_source_supplied and bool(bundle_object_path)
        ),
        "ambiguity_selects_candidate": False,
    }

    all_crosschecks = list(crosschecks)
    if isinstance(object_crosscheck, Mapping):
        all_crosschecks.append(dict(object_crosscheck))
    if isinstance(ambiguity_crosscheck, Mapping):
        all_crosschecks.append(dict(ambiguity_crosscheck))
    if isinstance(base_crosscheck, Mapping):
        all_crosschecks.append(dict(base_crosscheck))

    manifest = {
        "format": FORMAT,
        "version": 1,
        "status": "completed" if ready else "blocked",
        "ready": ready,
        "summary": {
            "full_runtime_shader_target_set_ready": not full_target_blockers,
            "raw_bootstrap_ready": raw_ready,
            "object_candidate_join_source_supplied": object_source_supplied,
            "object_candidate_join_regeneration_ready": bool(
                object_regenerated_path
            ),
            "ambiguity_regeneration_ready": ambiguity_ready,
            "base_audit_regeneration_ready": base_ready,
            "crosscheck_count": len(all_crosschecks),
            "crosscheck_mismatch_count": sum(
                row.get("status") == "bundle-regenerated-canonical-mismatch"
                for row in all_crosschecks
            ),
            "production_started": production_started,
            "production_completed": production_status == "completed",
            "blocking_reason_count": len(unique_blockers),
        },
        "bundle_index": {
            "format": index_manifest.get("format"),
            "status": index_manifest.get("status"),
            "summary": index_manifest.get("summary"),
            "fatal_blocking_reasons": fatal_bundle,
            "tolerated_regenerated_or_optional_report_blockers": tolerated_bundle,
            "manifest": str(
                bundle_dir / "silverstone_renderer_report_bundle_index.json"
            ),
        },
        "runtime_shader_targets": target_provenance,
        "raw_bootstrap": {
            "format": (
                raw_manifest.get("format")
                if isinstance(raw_manifest, Mapping)
                else None
            ),
            "status": (
                raw_manifest.get("status")
                if isinstance(raw_manifest, Mapping)
                else None
            ),
            "summary": (
                raw_manifest.get("summary")
                if isinstance(raw_manifest, Mapping)
                else None
            ),
            "manifest": (
                str(raw_dir / "silverstone_renderer_raw_capture_bootstrap.json")
                if raw_started
                else None
            ),
        },
        "object_candidate_join": object_input,
        "ambiguity_audit": {
            "mode": "regenerated",
            "path": ambiguity_path,
            "bundle_normalized_path": normalized.get("ambiguity_audit"),
            "regeneration_status": (
                ambiguity_manifest.get("status")
                if isinstance(ambiguity_manifest, Mapping)
                else None
            ),
            "regeneration_manifest": (
                str(
                    ambiguity_dir
                    / "silverstone_renderer_ambiguity_regeneration.json"
                )
                if isinstance(ambiguity_manifest, Mapping)
                else None
            ),
            "crosscheck": (
                dict(ambiguity_crosscheck)
                if isinstance(ambiguity_crosscheck, Mapping)
                else None
            ),
        },
        "base_audit": {
            "mode": "regenerated",
            "path": base_path,
            "bundle_normalized_path": normalized.get("base_audit"),
            "regeneration_status": (
                base_manifest.get("status")
                if isinstance(base_manifest, Mapping)
                else None
            ),
            "regeneration_manifest": (
                str(
                    base_dir
                    / "silverstone_renderer_base_audit_regeneration.json"
                )
                if isinstance(base_manifest, Mapping)
                else None
            ),
            "crosscheck": (
                dict(base_crosscheck)
                if isinstance(base_crosscheck, Mapping)
                else None
            ),
        },
        "regenerated_report_crosschecks": all_crosschecks,
        "production": {
            "format": (
                production_manifest.get("format")
                if isinstance(production_manifest, Mapping)
                else None
            ),
            "status": production_status,
            "summary": (
                production_manifest.get("summary")
                if isinstance(production_manifest, Mapping)
                else None
            ),
            "renderer_frontier": (
                production_manifest.get("renderer_frontier")
                if isinstance(production_manifest, Mapping)
                else None
            ),
            "manifest": (
                str(production_dir / "silverstone_renderer_production_run.json")
                if production_started
                else None
            ),
        },
        "blocking_reasons": unique_blockers,
        "boundary": {
            "dependency_order": (
                "Phase630 -> Phase638 optional object join -> Phase634 -> "
                "Phase633 -> Phase619-626"
            ),
            "bundle_draw_capture_ambiguity_base_are_selection_authority": False,
            "bundle_regenerated_reports_are_canonical_crosscheck_only": True,
            "bundle_variant_may_be_accepted_only_by_exact_regenerated_identity": True,
            "full_runtime_shader_target_set_is_still_required": True,
            "compact_phase568_target_evidence_is_sufficient": False,
            "object_candidate_join_is_optional_until_repeated_instance_gate": True,
            "object_candidate_join_regenerated_from_runtime_bootstrap_when_supplied": True,
            "bundle_object_candidate_join_is_selection_authority_when_regenerated": False,
            "unready_regenerated_object_join_may_fallback_to_bundle": False,
            "candidate_ranking_is_proof": False,
            "missing_capture_event_implies_recapture": False,
            "original_game_execution_required": False,
            "new_capture_required": False,
        },
    }
    _write_json_atomic(
        out / "silverstone_renderer_self_bootstrap_production_run.json",
        manifest,
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundles", nargs="+")
    parser.add_argument("--capture-jsonl", required=True)
    pe = parser.add_mutually_exclusive_group(required=True)
    pe.add_argument("--pe-evidence")
    pe.add_argument("--pe-image")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--corpus", action="append", default=[])
    parser.add_argument("--runtime-shader-targets")
    parser.add_argument("--runtime-bootstrap")
    parser.add_argument(
        "--max-json-bytes",
        type=int,
        default=128 * 1024 * 1024,
    )
    args = parser.parse_args(argv)

    manifest = run_self_bootstrap_production(
        bundles=args.bundles,
        capture_jsonl=args.capture_jsonl,
        pe_evidence=args.pe_evidence,
        pe_image=args.pe_image,
        output_dir=args.output_dir,
        corpus=args.corpus,
        runtime_shader_targets=args.runtime_shader_targets,
        runtime_bootstrap=args.runtime_bootstrap,
        max_json_bytes=args.max_json_bytes,
    )
    print(json.dumps({
        "format": manifest["format"],
        "status": manifest["status"],
        "summary": manifest["summary"],
        "blocking_reasons": manifest["blocking_reasons"],
        "renderer_frontier": manifest["production"]["renderer_frontier"],
        "manifest": str(
            Path(args.output_dir)
            / "silverstone_renderer_self_bootstrap_production_run.json"
        ),
    }, ensure_ascii=False, indent=2))
    return 0 if manifest["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
