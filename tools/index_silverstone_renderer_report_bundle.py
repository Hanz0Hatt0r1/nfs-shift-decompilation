#!/usr/bin/env python3
"""Index renderer JSON reports in ZIP bundles by embedded format, fail-closed.

This tool is intended for handoff archives such as ``out.zip``.  It never uses
entry filename, archive order, timestamp, or frequency to choose one report.
When more than one occurrence has the same canonical JSON payload all source
occurrences are retained; distinct payloads for the same format remain
ambiguous and no normalized report is emitted for that format.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.SilverstoneRendererReportBundleIndex/1"

REPORT_SPECS: tuple[dict[str, Any], ...] = (
    {
        "key": "base_audit",
        "format": "SHIFT.D3D9RendererRequirementAudit/1",
        "output": "d3d9_renderer_requirement_audit.json",
        "required_for_production": True,
    },
    {
        "key": "ambiguity_audit",
        "format": "SHIFT.IMBDrawLocalAmbiguityAudit/1",
        "output": "silverstone_d3d9_draw_local_ambiguity_audit.json",
        "required_for_production": True,
    },
    {
        "key": "draw_local",
        "format": "SHIFT.D3D9TargetDrawLocalEvidence/1",
        "output": "d3d9_target_draw_local_evidence.json",
        "required_for_production": True,
    },
    {
        "key": "capture_pipeline",
        "format": "SHIFT.IMBRuntimeCapturePipeline/1",
        "output": "silverstone_imb_runtime_capture_pipeline.json",
        "required_for_production": True,
    },
    {
        "key": "pe_evidence",
        "format": "SHIFT.PEImageEvidence/1",
        "output": "d3d9_pe_evidence.json",
        "required_for_production": False,
        # PE evidence is an optional playable-bootstrap input.  Distinct bundle
        # payloads remain AMBIGUOUS and are never normalized, but must not make
        # an explicitly supplied PE selector fail merely because a cross-check
        # bundle also carries unrelated PE variants.
        "ambiguity_blocks_index": False,
    },
    {
        "key": "object_candidate_join",
        "format": "SHIFT.SGBRuntimeObjectCandidateJoin/1",
        "output": "silverstone_sgb_runtime_object_candidate_join.json",
        "required_for_production": False,
    },
    {
        "key": "runtime_shader_targets",
        "format": "SHIFT.IMBRuntimeShaderTargetSet/1",
        "output": "silverstone_era3_runtime_shader_targets.json",
        "required_for_production": False,
    },
)

SPEC_BY_FORMAT = {row["format"]: row for row in REPORT_SPECS}


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_payload(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


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
    return _sha256_bytes(payload)


def _bundle_record(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "present": path.is_file(),
        "size": path.stat().st_size if path.is_file() else None,
        "sha256": _sha256_file(path) if path.is_file() else None,
    }


def index_report_bundles(
    bundles: list[str | Path],
    *,
    output_dir: str | Path,
    max_json_bytes: int = 128 * 1024 * 1024,
) -> dict[str, Any]:
    if max_json_bytes <= 0:
        raise ValueError("max_json_bytes must be positive")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    bundle_paths = [Path(value).expanduser() for value in bundles]
    bundle_rows = [_bundle_record(path) for path in bundle_paths]
    blockers: list[str] = []
    for ordinal, row in enumerate(bundle_rows):
        if not row["present"]:
            blockers.append(f"bundle-{ordinal}:file-not-found:{row['path']}")
    if not bundle_paths:
        blockers.append("bundle:no-inputs")

    occurrences: dict[str, list[dict[str, Any]]] = defaultdict(list)
    skipped_entries: list[dict[str, Any]] = []

    for bundle_ordinal, path in enumerate(bundle_paths):
        if not path.is_file():
            continue
        try:
            archive = zipfile.ZipFile(path)
        except Exception as exc:
            blockers.append(
                f"bundle-{bundle_ordinal}:zip-open-failed:{type(exc).__name__}:{exc}"
            )
            continue
        with archive:
            for info in archive.infolist():
                if info.is_dir() or not info.filename.lower().endswith(".json"):
                    continue
                if info.file_size > max_json_bytes:
                    skipped_entries.append({
                        "bundle_ordinal": bundle_ordinal,
                        "bundle_path": str(path),
                        "entry": info.filename,
                        "size": info.file_size,
                        "reason": "json-entry-too-large",
                    })
                    continue
                try:
                    payload = archive.read(info)
                except Exception as exc:
                    skipped_entries.append({
                        "bundle_ordinal": bundle_ordinal,
                        "bundle_path": str(path),
                        "entry": info.filename,
                        "size": info.file_size,
                        "reason": f"read-failed:{type(exc).__name__}:{exc}",
                    })
                    continue
                try:
                    value = json.loads(payload.decode("utf-8"))
                except Exception:
                    continue
                if not isinstance(value, Mapping):
                    continue
                report_format = value.get("format")
                if report_format not in SPEC_BY_FORMAT:
                    continue
                canonical = _canonical_payload(value)
                occurrences[str(report_format)].append({
                    "bundle_ordinal": bundle_ordinal,
                    "bundle_path": str(path),
                    "bundle_sha256": bundle_rows[bundle_ordinal]["sha256"],
                    "entry": info.filename,
                    "entry_size": info.file_size,
                    "raw_sha256": _sha256_bytes(payload),
                    "canonical_sha256": _sha256_bytes(canonical),
                    "value": dict(value),
                })

    report_rows: list[dict[str, Any]] = []
    normalized_outputs: dict[str, str] = {}
    normalized_values: dict[str, Mapping[str, Any]] = {}

    for spec in REPORT_SPECS:
        report_format = spec["format"]
        hits = occurrences.get(report_format, [])
        by_identity: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for hit in hits:
            by_identity[hit["canonical_sha256"]].append(hit)
        identities = sorted(by_identity)
        selected = identities[0] if len(identities) == 1 else None
        output_path = out / spec["output"]
        status: str
        output_sha: str | None = None
        if not hits:
            status = "missing"
            if spec["required_for_production"]:
                blockers.append(f"report:{spec['key']}:missing-from-bundles")
        elif len(identities) > 1:
            status = "ambiguous-distinct-payloads"
            if spec.get("ambiguity_blocks_index", True):
                blockers.append(
                    f"report:{spec['key']}:ambiguous-distinct-canonical-payloads:{len(identities)}"
                )
        else:
            status = (
                "exact-single-occurrence"
                if len(hits) == 1
                else "content-equivalent-multiple-occurrences"
            )
            representative = by_identity[selected][0]
            normalized_value = representative["value"]
            output_sha = _write_json_atomic(output_path, normalized_value)
            normalized_outputs[spec["key"]] = str(output_path)
            normalized_values[spec["key"]] = normalized_value

        occurrence_rows = []
        for hit in hits:
            occurrence_rows.append({
                key: hit[key]
                for key in (
                    "bundle_ordinal",
                    "bundle_path",
                    "bundle_sha256",
                    "entry",
                    "entry_size",
                    "raw_sha256",
                    "canonical_sha256",
                )
            })
        report_rows.append({
            "key": spec["key"],
            "format": report_format,
            "required_for_production": spec["required_for_production"],
            "ambiguity_blocks_index": spec.get("ambiguity_blocks_index", True),
            "status": status,
            "occurrence_count": len(hits),
            "distinct_canonical_payload_count": len(identities),
            "canonical_sha256": selected,
            "output": str(output_path) if selected is not None else None,
            "output_sha256": output_sha,
            "occurrences": occurrence_rows,
        })

    unique_blockers = list(dict.fromkeys(blockers))
    manifest = {
        "format": FORMAT,
        "version": 1,
        "status": "blocked" if unique_blockers else "ready",
        "ready": not unique_blockers,
        "summary": {
            "bundle_count": len(bundle_rows),
            "recognized_report_occurrence_count": sum(
                len(rows) for rows in occurrences.values()
            ),
            "resolved_report_count": sum(
                row["status"] in {
                    "exact-single-occurrence",
                    "content-equivalent-multiple-occurrences",
                }
                for row in report_rows
            ),
            "missing_required_report_count": sum(
                row["required_for_production"] and row["status"] == "missing"
                for row in report_rows
            ),
            "ambiguous_report_count": sum(
                row["status"] == "ambiguous-distinct-payloads"
                for row in report_rows
            ),
            "skipped_json_entry_count": len(skipped_entries),
        },
        "bundles": bundle_rows,
        "reports": report_rows,
        "normalized_outputs": normalized_outputs,
        "blocking_reasons": unique_blockers,
        "skipped_entries": skipped_entries,
        "production_runner_arguments": {
            "base_audit": normalized_outputs.get("base_audit"),
            "ambiguity_audit": normalized_outputs.get("ambiguity_audit"),
            "runtime_shader_targets": normalized_outputs.get("runtime_shader_targets"),
            "draw_local": normalized_outputs.get("draw_local"),
            "capture_pipeline": normalized_outputs.get("capture_pipeline"),
            "pe_evidence": normalized_outputs.get("pe_evidence"),
            "object_candidate_join": normalized_outputs.get("object_candidate_join"),
        },
        "boundary": {
            "selection_key": "embedded report format + canonical JSON payload identity",
            "filename_used_for_selection": False,
            "archive_order_used_for_selection": False,
            "frequency_used_for_selection": False,
            "content_equivalent_duplicates_are_single_report_identity": True,
            "distinct_payloads_for_same_format_are_ambiguous": True,
            "adds_renderer_proof_semantics": False,
            "original_game_execution_required": False,
            "new_capture_required": False,
        },
    }
    _write_json_atomic(out / "silverstone_renderer_report_bundle_index.json", manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundles", nargs="+", help="ZIP handoff bundle(s), for example out.zip")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--max-json-bytes",
        type=int,
        default=128 * 1024 * 1024,
        help="Skip individual JSON ZIP entries larger than this many bytes",
    )
    args = parser.parse_args(argv)
    manifest = index_report_bundles(
        args.bundles,
        output_dir=args.output_dir,
        max_json_bytes=args.max_json_bytes,
    )
    print(json.dumps({
        "format": manifest["format"],
        "status": manifest["status"],
        "summary": manifest["summary"],
        "blocking_reasons": manifest["blocking_reasons"],
        "production_runner_arguments": manifest["production_runner_arguments"],
        "manifest": str(Path(args.output_dir) / "silverstone_renderer_report_bundle_index.json"),
    }, ensure_ascii=False, indent=2))
    return 0 if manifest["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())