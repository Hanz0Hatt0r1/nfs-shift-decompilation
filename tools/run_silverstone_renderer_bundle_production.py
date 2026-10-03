#!/usr/bin/env python3
"""Run the Silverstone renderer production pipeline directly from report ZIP bundles.

Phase 628 remains the only report-selection authority: reports are selected by
embedded format plus canonical JSON identity, never by filename, archive order,
frequency, or timestamp. This wrapper only connects the Phase 628 normalized
outputs to the existing Phase 627 production runner.
"""
from __future__ import annotations

import argparse
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
from run_silverstone_renderer_production import _default_shader_targets, run_production

FORMAT = "SHIFT.SilverstoneRendererBundleProductionRun/1"


def _write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
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


def run_bundle_production(
    *,
    bundles: list[str | Path],
    output_dir: str | Path,
    corpus: list[str | Path],
    max_json_bytes: int = 128 * 1024 * 1024,
) -> dict[str, Any]:
    out = Path(output_dir)
    inputs_dir = out / "inputs"
    production_dir = out / "production"
    index_manifest_path = inputs_dir / "silverstone_renderer_report_bundle_index.json"
    production_manifest_path = production_dir / "silverstone_renderer_production_run.json"

    index_manifest = index_report_bundles(
        bundles,
        output_dir=inputs_dir,
        max_json_bytes=max_json_bytes,
    )

    production_manifest: Mapping[str, Any] | None = None
    blockers = list(index_manifest.get("blocking_reasons") or [])
    production_started = False

    if index_manifest.get("ready") is True:
        arguments = index_manifest.get("production_runner_arguments")
        arguments = arguments if isinstance(arguments, Mapping) else {}
        runtime_shader_targets = arguments.get("runtime_shader_targets")
        if not runtime_shader_targets:
            runtime_shader_targets = _default_shader_targets()

        production_started = True
        production_manifest = run_production(
            output_dir=production_dir,
            corpus=corpus,
            base_audit=arguments.get("base_audit"),
            ambiguity_audit=arguments.get("ambiguity_audit"),
            runtime_shader_targets=runtime_shader_targets,
            draw_local=arguments.get("draw_local"),
            capture_pipeline=arguments.get("capture_pipeline"),
            object_candidate_join=arguments.get("object_candidate_join"),
        )
        blockers.extend(production_manifest.get("blocking_reasons") or [])

    unique_blockers = list(dict.fromkeys(str(value) for value in blockers))
    production_status = (
        production_manifest.get("status")
        if isinstance(production_manifest, Mapping)
        else None
    )
    status = (
        "completed"
        if index_manifest.get("ready") is True
        and production_status == "completed"
        and not unique_blockers
        else "blocked"
    )

    manifest = {
        "format": FORMAT,
        "version": 1,
        "status": status,
        "ready": status == "completed",
        "summary": {
            "bundle_index_ready": index_manifest.get("ready") is True,
            "production_started": production_started,
            "production_completed": production_status == "completed",
            "bundle_count": len(index_manifest.get("bundles") or []),
            "recognized_report_occurrence_count": (
                (index_manifest.get("summary") or {}).get(
                    "recognized_report_occurrence_count"
                )
                if isinstance(index_manifest.get("summary"), Mapping)
                else None
            ),
            "blocking_reason_count": len(unique_blockers),
        },
        "paths": {
            "bundle_index": str(index_manifest_path),
            "production_run": (
                str(production_manifest_path) if production_started else None
            ),
        },
        "bundle_index": {
            "format": index_manifest.get("format"),
            "status": index_manifest.get("status"),
            "summary": index_manifest.get("summary"),
            "blocking_reasons": list(
                index_manifest.get("blocking_reasons") or []
            ),
            "production_runner_arguments": dict(
                index_manifest.get("production_runner_arguments") or {}
            ),
        },
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
        },
        "blocking_reasons": unique_blockers,
        "boundary": {
            "report_selection_authority": "Phase 628 bundle index",
            "filename_used_for_selection": False,
            "archive_order_used_for_selection": False,
            "frequency_used_for_selection": False,
            "distinct_payloads_for_same_format_are_ambiguous": True,
            "bundle_index_blocker_starts_production": False,
            "adds_renderer_proof_semantics": False,
            "original_game_execution_required": False,
            "new_capture_required": False,
            "buffer_payload_is_last_conditional_fallback": True,
        },
    }
    _write_json_atomic(out / "silverstone_renderer_bundle_production_run.json", manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "bundles",
        nargs="+",
        help="ZIP handoff bundle(s), for example out.zip",
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--corpus",
        action="append",
        default=[],
        help="BFF or ZIP corpus input; repeatable",
    )
    parser.add_argument(
        "--max-json-bytes",
        type=int,
        default=128 * 1024 * 1024,
        help="Phase 628 per-entry JSON decompression limit",
    )
    args = parser.parse_args(argv)

    manifest = run_bundle_production(
        bundles=args.bundles,
        output_dir=args.output_dir,
        corpus=args.corpus,
        max_json_bytes=args.max_json_bytes,
    )
    print(
        json.dumps(
            {
                "format": manifest["format"],
                "status": manifest["status"],
                "summary": manifest["summary"],
                "blocking_reasons": manifest["blocking_reasons"],
                "renderer_frontier": manifest["production"][
                    "renderer_frontier"
                ],
                "manifest": str(
                    Path(args.output_dir)
                    / "silverstone_renderer_bundle_production_run.json"
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if manifest["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
