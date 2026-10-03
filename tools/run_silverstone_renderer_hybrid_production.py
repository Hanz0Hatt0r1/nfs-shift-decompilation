#!/usr/bin/env python3
"""Run Silverstone renderer production from static report bundles plus raw capture.

Phase 631 regenerates capture-derived draw-local/runtime reports from the
historical JSONL and treats handoff copies as canonical cross-checks. Phase 633
optionally applies the same policy to the renderer base requirement audit:
shader-use and texture/sampler evidence are regenerated from the same capture,
then joined with the exact Phase 618 ambiguity report. No ranking or missing
capture event is promoted into proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from index_silverstone_renderer_report_bundle import index_report_bundles
from run_silverstone_renderer_base_audit_regeneration import (
    regenerate_renderer_base_audit,
)
from run_silverstone_renderer_production import run_production
from run_silverstone_renderer_raw_capture_bootstrap import run_raw_capture_bootstrap

FORMAT = "SHIFT.SilverstoneRendererHybridProductionRun/1"
STATIC_REQUIRED_KEYS = {"base_audit", "ambiguity_audit"}
RAW_REGENERATED_KEYS = {"draw_local", "capture_pipeline"}
NON_FATAL_BUNDLE_REPORT_KEYS = {
    "draw_local",
    "capture_pipeline",
    "object_candidate_join",
    "runtime_shader_targets",
}
BASE_AUDIT_FORMAT = "SHIFT.D3D9RendererRequirementAudit/1"


def _canonical_payload(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _canonical_sha(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_payload(value)).hexdigest()


def _load_json_map(path: str | Path) -> Mapping[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"JSON object expected: {path}")
    return value


def _canonical_sha_file(path: str | Path) -> str:
    return _canonical_sha(_load_json_map(path))


def _write_json_atomic(path: Path, value: Mapping[str, Any]) -> str:
    payload = (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as stream:
        temp = Path(stream.name)
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    temp.replace(path)
    return hashlib.sha256(payload).hexdigest()


def _report_rows(index_manifest: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        str(row.get("key")): row
        for row in (index_manifest.get("reports") or [])
        if isinstance(row, Mapping) and row.get("key")
    }


def _identity_set(row: Mapping[str, Any] | None) -> list[str]:
    if not isinstance(row, Mapping):
        return []
    return sorted(
        {
            str(occurrence.get("canonical_sha256"))
            for occurrence in (row.get("occurrences") or [])
            if isinstance(occurrence, Mapping)
            and isinstance(occurrence.get("canonical_sha256"), str)
            and len(str(occurrence.get("canonical_sha256"))) == 64
        }
    )


def _crosscheck_report(
    key: str,
    regenerated_path: str | Path | None,
    report_row: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], list[str]]:
    bundle_identities = _identity_set(report_row)
    blockers: list[str] = []
    regenerated_sha: str | None = None
    regenerated_error: str | None = None
    if regenerated_path:
        try:
            regenerated_sha = _canonical_sha_file(regenerated_path)
        except Exception as exc:
            regenerated_error = f"{type(exc).__name__}:{exc}"
            blockers.append(
                f"crosscheck:{key}:regenerated-report-unreadable:{regenerated_error}"
            )

    if regenerated_sha is None:
        status = "regenerated-report-unavailable"
    elif not bundle_identities:
        status = "bundle-copy-absent-regenerated-source-used"
    elif regenerated_sha in bundle_identities:
        status = (
            "exact-canonical-match"
            if len(bundle_identities) == 1
            else "exact-canonical-match-among-bundle-variants"
        )
    else:
        status = "bundle-regenerated-canonical-mismatch"
        blockers.append(
            f"crosscheck:{key}:bundle-regenerated-canonical-mismatch"
        )

    return {
        "key": key,
        "status": status,
        "regenerated_path": str(regenerated_path) if regenerated_path else None,
        "regenerated_canonical_sha256": regenerated_sha,
        "regenerated_error": regenerated_error,
        "bundle_status": (
            report_row.get("status") if isinstance(report_row, Mapping) else None
        ),
        "bundle_occurrence_count": (
            int(report_row.get("occurrence_count") or 0)
            if isinstance(report_row, Mapping)
            else 0
        ),
        "bundle_distinct_canonical_payload_count": len(bundle_identities),
        "bundle_canonical_sha256": bundle_identities,
        "selection_claim": False,
    }, blockers


def _bundle_blockers(
    index_manifest: Mapping[str, Any],
    *,
    tolerate_base_audit: bool = False,
) -> tuple[list[str], list[str]]:
    tolerated_keys = set(NON_FATAL_BUNDLE_REPORT_KEYS)
    if tolerate_base_audit:
        tolerated_keys.add("base_audit")
    fatal: list[str] = []
    tolerated: list[str] = []
    for raw in index_manifest.get("blocking_reasons") or []:
        reason = str(raw)
        if reason.startswith("report:"):
            parts = reason.split(":", 2)
            key = parts[1] if len(parts) > 1 else ""
            if key in tolerated_keys:
                tolerated.append(reason)
                continue
        fatal.append(reason)
    return list(dict.fromkeys(fatal)), list(dict.fromkeys(tolerated))


def _default_shader_targets() -> str:
    return str(ROOT / "evidence" / "silverstone_era3_runtime_shader_targets.json")


def _choose_shader_targets(
    index_manifest: Mapping[str, Any],
    *,
    explicit: str | Path | None,
) -> tuple[str, dict[str, Any], list[str]]:
    rows = _report_rows(index_manifest)
    row = rows.get("runtime_shader_targets")
    normalized = index_manifest.get("normalized_outputs")
    normalized = normalized if isinstance(normalized, Mapping) else {}

    if explicit is not None:
        chosen = str(Path(explicit).expanduser())
        source = "explicit"
    elif normalized.get("runtime_shader_targets"):
        chosen = str(normalized["runtime_shader_targets"])
        source = "bundle-exact"
    else:
        chosen = _default_shader_targets()
        source = "committed-default"

    blockers: list[str] = []
    chosen_sha: str | None = None
    chosen_error: str | None = None
    try:
        chosen_sha = _canonical_sha_file(chosen)
    except Exception as exc:
        chosen_error = f"{type(exc).__name__}:{exc}"
        blockers.append(
            f"runtime_shader_targets:chosen-report-unreadable:{chosen_error}"
        )

    bundle_identities = _identity_set(row)
    if chosen_sha is None:
        crosscheck = "chosen-report-unreadable"
    elif not bundle_identities:
        crosscheck = "bundle-copy-absent"
    elif chosen_sha in bundle_identities:
        crosscheck = (
            "exact-canonical-match"
            if len(bundle_identities) == 1
            else "exact-canonical-match-among-bundle-variants"
        )
    else:
        crosscheck = "bundle-chosen-canonical-mismatch"
        blockers.append(
            "runtime_shader_targets:bundle-chosen-canonical-mismatch"
        )

    return chosen, {
        "path": chosen,
        "source": source,
        "canonical_sha256": chosen_sha,
        "error": chosen_error,
        "bundle_status": row.get("status") if isinstance(row, Mapping) else None,
        "bundle_canonical_sha256": bundle_identities,
        "crosscheck": crosscheck,
        "selection_by_rank_or_frequency": False,
    }, blockers


def run_hybrid_production(
    *,
    bundles: list[str | Path],
    capture_jsonl: str | Path,
    pe_evidence: str | Path,
    output_dir: str | Path,
    corpus: list[str | Path],
    runtime_shader_targets: str | Path | None = None,
    max_json_bytes: int = 128 * 1024 * 1024,
    regenerate_base_audit: bool = False,
) -> dict[str, Any]:
    out = Path(output_dir)
    bundle_dir = out / "bundle"
    raw_dir = out / "raw"
    base_regen_dir = out / "base-audit"
    production_dir = out / "production"

    index_manifest = index_report_bundles(
        bundles,
        output_dir=bundle_dir,
        max_json_bytes=max_json_bytes,
    )
    fatal_bundle_blockers, tolerated_bundle_blockers = _bundle_blockers(
        index_manifest,
        tolerate_base_audit=regenerate_base_audit,
    )
    rows = _report_rows(index_manifest)
    normalized = index_manifest.get("normalized_outputs")
    normalized = normalized if isinstance(normalized, Mapping) else {}

    blockers: list[str] = [
        f"bundle:{reason}" for reason in fatal_bundle_blockers
    ]

    base_audit = normalized.get("base_audit")
    ambiguity_audit = normalized.get("ambiguity_audit")
    if not regenerate_base_audit and not base_audit:
        blockers.append("bundle:base_audit:exact-normalized-report-required")
    if not ambiguity_audit:
        blockers.append("bundle:ambiguity_audit:exact-normalized-report-required")

    chosen_targets, target_provenance, target_blockers = _choose_shader_targets(
        index_manifest,
        explicit=runtime_shader_targets,
    )
    blockers.extend(target_blockers)

    raw_manifest: Mapping[str, Any] | None = None
    raw_started = not blockers
    if raw_started:
        raw_manifest = run_raw_capture_bootstrap(
            capture_jsonl=capture_jsonl,
            pe_evidence=pe_evidence,
            runtime_shader_targets=chosen_targets,
            output_dir=raw_dir,
        )
        blockers.extend(
            f"raw:{reason}"
            for reason in (raw_manifest.get("blocking_reasons") or [])
        )

    crosschecks: list[dict[str, Any]] = []
    if isinstance(raw_manifest, Mapping):
        raw_outputs = raw_manifest.get("outputs")
        raw_outputs = raw_outputs if isinstance(raw_outputs, Mapping) else {}
        for key in ("draw_local", "capture_pipeline"):
            check, check_blockers = _crosscheck_report(
                key,
                raw_outputs.get(key),
                rows.get(key),
            )
            crosschecks.append(check)
            blockers.extend(check_blockers)
    else:
        crosschecks.extend(
            {
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
            }
            for key in ("draw_local", "capture_pipeline")
        )

    base_regen_manifest: Mapping[str, Any] | None = None
    base_crosscheck: Mapping[str, Any] | None = None
    if regenerate_base_audit:
        raw_outputs = (
            raw_manifest.get("outputs")
            if isinstance(raw_manifest, Mapping)
            and isinstance(raw_manifest.get("outputs"), Mapping)
            else {}
        )
        draw_local_path = raw_outputs.get("draw_local")
        if not draw_local_path:
            blockers.append("base_regeneration:draw-local-unavailable")
            base_audit = None
        elif not ambiguity_audit:
            blockers.append("base_regeneration:ambiguity-audit-unavailable")
            base_audit = None
        else:
            try:
                base_regen_manifest = regenerate_renderer_base_audit(
                    capture_jsonl=capture_jsonl,
                    runtime_shader_targets=chosen_targets,
                    draw_local=draw_local_path,
                    ambiguity_audit=ambiguity_audit,
                    output_dir=base_regen_dir,
                )
            except Exception as exc:
                blockers.append(
                    f"base_regeneration:failed:{type(exc).__name__}:{exc}"
                )
                base_regen_manifest = None
            if isinstance(base_regen_manifest, Mapping):
                blockers.extend(
                    f"base_regeneration:{reason}"
                    for reason in (base_regen_manifest.get("blocking_reasons") or [])
                )
                base_outputs = base_regen_manifest.get("outputs")
                base_outputs = (
                    base_outputs if isinstance(base_outputs, Mapping) else {}
                )
                base_audit = base_outputs.get("base_audit")
                check, check_blockers = _crosscheck_report(
                    "base_audit",
                    base_audit,
                    rows.get("base_audit"),
                )
                base_crosscheck = check
                blockers.extend(check_blockers)
                if base_audit:
                    try:
                        base_value = _load_json_map(base_audit)
                        if base_value.get("format") != BASE_AUDIT_FORMAT:
                            blockers.append(
                                "base_regeneration:base-audit-format-mismatch"
                            )
                    except Exception as exc:
                        blockers.append(
                            f"base_regeneration:base-audit-unreadable:{type(exc).__name__}:{exc}"
                        )
            else:
                base_audit = None

    unique_blockers = list(dict.fromkeys(str(value) for value in blockers))
    production_manifest: Mapping[str, Any] | None = None
    production_started = False

    raw_ready = (
        isinstance(raw_manifest, Mapping)
        and raw_manifest.get("ready") is True
    )
    base_ready = bool(base_audit) and (
        not regenerate_base_audit
        or (
            isinstance(base_regen_manifest, Mapping)
            and base_regen_manifest.get("ready") is True
        )
    )
    if not unique_blockers and raw_ready and base_ready:
        raw_outputs = raw_manifest.get("outputs") or {}
        object_candidate_join = normalized.get("object_candidate_join")
        production_started = True
        production_manifest = run_production(
            output_dir=production_dir,
            corpus=corpus,
            base_audit=base_audit,
            ambiguity_audit=ambiguity_audit,
            runtime_shader_targets=chosen_targets,
            draw_local=raw_outputs.get("draw_local"),
            capture_pipeline=raw_outputs.get("capture_pipeline"),
            object_candidate_join=object_candidate_join,
        )
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
    status = (
        "completed"
        if production_started
        and production_status == "completed"
        and not unique_blockers
        else "blocked"
    )

    object_row = rows.get("object_candidate_join")
    object_input = {
        "bundle_status": (
            object_row.get("status") if isinstance(object_row, Mapping) else None
        ),
        "bundle_canonical_sha256": _identity_set(object_row),
        "normalized_path": normalized.get("object_candidate_join"),
        "passed_to_production": bool(
            production_started and normalized.get("object_candidate_join")
        ),
        "ambiguity_selects_candidate": False,
    }

    base_input = {
        "mode": "regenerated" if regenerate_base_audit else "bundle-exact",
        "path": str(base_audit) if base_audit else None,
        "bundle_normalized_path": normalized.get("base_audit"),
        "bundle_status": (
            rows.get("base_audit", {}).get("status")
            if isinstance(rows.get("base_audit"), Mapping)
            else None
        ),
        "bundle_canonical_sha256": _identity_set(rows.get("base_audit")),
        "regeneration_manifest": (
            str(base_regen_dir / "silverstone_renderer_base_audit_regeneration.json")
            if regenerate_base_audit and base_regen_manifest is not None
            else None
        ),
        "regeneration_status": (
            base_regen_manifest.get("status")
            if isinstance(base_regen_manifest, Mapping)
            else None
        ),
        "crosscheck": dict(base_crosscheck) if isinstance(base_crosscheck, Mapping) else None,
    }

    manifest = {
        "format": FORMAT,
        "version": 1,
        "status": status,
        "ready": status == "completed",
        "summary": {
            "bundle_static_inputs_ready": (
                not fatal_bundle_blockers
                and bool(ambiguity_audit)
                and (regenerate_base_audit or bool(normalized.get("base_audit")))
            ),
            "base_audit_regenerated": regenerate_base_audit,
            "base_audit_ready": base_ready,
            "raw_bootstrap_started": raw_started,
            "raw_bootstrap_ready": raw_ready,
            "crosscheck_count": len(crosschecks),
            "crosscheck_mismatch_count": sum(
                row.get("status") == "bundle-regenerated-canonical-mismatch"
                for row in crosschecks
            )
            + (
                1
                if isinstance(base_crosscheck, Mapping)
                and base_crosscheck.get("status")
                == "bundle-regenerated-canonical-mismatch"
                else 0
            ),
            "production_started": production_started,
            "production_completed": production_status == "completed",
            "blocking_reason_count": len(unique_blockers),
        },
        "bundle_index": {
            "format": index_manifest.get("format"),
            "status": index_manifest.get("status"),
            "summary": index_manifest.get("summary"),
            "fatal_blocking_reasons": fatal_bundle_blockers,
            "tolerated_raw_or_optional_report_blockers": tolerated_bundle_blockers,
            "manifest": str(
                bundle_dir / "silverstone_renderer_report_bundle_index.json"
            ),
        },
        "runtime_shader_targets": target_provenance,
        "base_audit": base_input,
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
        "capture_derived_report_crosschecks": crosschecks,
        "object_candidate_join": object_input,
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
            "static_base_and_ambiguity_source": (
                "regenerated base from historical capture + Phase 628 exact ambiguity"
                if regenerate_base_audit
                else "Phase 628 exact bundle identity"
            ),
            "base_audit_source": (
                "historical raw capture + exact Phase 618 ambiguity"
                if regenerate_base_audit
                else "Phase 628 exact bundle identity"
            ),
            "ambiguity_source": "Phase 628 exact bundle identity",
            "bundle_base_audit_is_selection_authority": not regenerate_base_audit,
            "bundle_base_audit_is_canonical_crosscheck_only": regenerate_base_audit,
            "capture_derived_source": (
                "Phase 630 regeneration from historical raw JSONL"
            ),
            "bundle_capture_reports_are_selection_authority": False,
            "bundle_capture_reports_are_canonical_crosscheck_only": True,
            "bundle_variant_may_be_accepted_only_by_exact_raw_canonical_match": True,
            "mismatching_capture_derived_handoff_blocks_production": True,
            "base_regeneration_adds_hard_capture_requirement": False,
            "object_candidate_ambiguity_is_ranked": False,
            "ranking_or_frequency_is_proof": False,
            "missing_capture_event_implies_recapture": False,
            "original_game_execution_required": False,
            "new_capture_required": False,
            "buffer_payload_is_last_conditional_fallback": True,
        },
    }
    _write_json_atomic(
        out / "silverstone_renderer_hybrid_production_run.json",
        manifest,
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundles", nargs="+")
    parser.add_argument("--capture-jsonl", required=True)
    parser.add_argument("--pe-evidence", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--corpus", action="append", default=[])
    parser.add_argument("--runtime-shader-targets")
    parser.add_argument(
        "--regenerate-base-audit",
        action="store_true",
        help=(
            "Regenerate D3D9RendererRequirementAudit from the historical capture "
            "and use any bundled base audit only as a canonical cross-check."
        ),
    )
    parser.add_argument(
        "--max-json-bytes",
        type=int,
        default=128 * 1024 * 1024,
    )
    args = parser.parse_args(argv)

    manifest = run_hybrid_production(
        bundles=args.bundles,
        capture_jsonl=args.capture_jsonl,
        pe_evidence=args.pe_evidence,
        output_dir=args.output_dir,
        corpus=args.corpus,
        runtime_shader_targets=args.runtime_shader_targets,
        max_json_bytes=args.max_json_bytes,
        regenerate_base_audit=args.regenerate_base_audit,
    )
    print(
        json.dumps(
            {
                "format": manifest["format"],
                "status": manifest["status"],
                "summary": manifest["summary"],
                "blocking_reasons": manifest["blocking_reasons"],
                "renderer_frontier": manifest["production"]["renderer_frontier"],
                "manifest": str(
                    Path(args.output_dir)
                    / "silverstone_renderer_hybrid_production_run.json"
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if manifest["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
