#!/usr/bin/env python3
"""Run hybrid Silverstone renderer production directly from static PE image bytes.

The PE image is parsed as data only. It is never executed. The resulting
SHIFT.PEImageEvidence/1 report is persisted with source SHA-256 provenance and
then passed to the unchanged Phase 631 hybrid production runner.
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
SRC = ROOT / "src"
TOOLS = ROOT / "tools"
if SRC.is_dir():
    paths = [SRC]
    paths.extend(
        sorted(
            (path for path in SRC.rglob("*") if path.is_dir()),
            key=lambda path: (len(path.parts), str(path)),
        )
    )
    for path in reversed(paths):
        value = str(path)
        if value not in sys.path:
            sys.path.insert(0, value)
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from d3d9_pe_evidence import analyze_d3d9_pe_image_file
from run_silverstone_renderer_hybrid_production import run_hybrid_production

FORMAT = "SHIFT.SilverstoneRendererPEImageHybridProductionRun/1"
PE_FORMAT = "SHIFT.PEImageEvidence/1"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


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


def run_pe_image_hybrid_production(
    *,
    bundles: list[str | Path],
    capture_jsonl: str | Path,
    pe_image: str | Path,
    output_dir: str | Path,
    corpus: list[str | Path],
    runtime_shader_targets: str | Path | None = None,
    max_json_bytes: int = 128 * 1024 * 1024,
) -> dict[str, Any]:
    out = Path(output_dir)
    static_dir = out / "static"
    hybrid_dir = out / "hybrid"
    image_path = Path(pe_image).expanduser()
    pe_report_path = static_dir / "d3d9_pe_evidence.json"

    image_record = {
        "path": str(image_path),
        "present": image_path.is_file(),
        "size": image_path.stat().st_size if image_path.is_file() else None,
        "sha256": _sha256_file(image_path) if image_path.is_file() else None,
    }
    blockers: list[str] = []
    pe_report: Mapping[str, Any] | None = None
    pe_report_sha: str | None = None

    if not image_path.is_file():
        blockers.append(f"pe_image:file-not-found:{image_path}")
    else:
        try:
            pe_report = analyze_d3d9_pe_image_file(image_path)
        except Exception as exc:
            blockers.append(
                f"pe_image:analysis-failed:{type(exc).__name__}:{exc}"
            )
        if pe_report is not None and pe_report.get("format") != PE_FORMAT:
            blockers.append(
                f"pe_image:analysis-format-mismatch:{pe_report.get('format')!r}"
            )
            pe_report = None
        if pe_report is not None:
            pe_report_sha = _write_json_atomic(pe_report_path, pe_report)

    hybrid_manifest: Mapping[str, Any] | None = None
    hybrid_started = not blockers and pe_report is not None
    if hybrid_started:
        hybrid_manifest = run_hybrid_production(
            bundles=bundles,
            capture_jsonl=capture_jsonl,
            pe_evidence=pe_report_path,
            output_dir=hybrid_dir,
            corpus=corpus,
            runtime_shader_targets=runtime_shader_targets,
            max_json_bytes=max_json_bytes,
        )
        blockers.extend(
            f"hybrid:{reason}"
            for reason in (hybrid_manifest.get("blocking_reasons") or [])
        )

    unique_blockers = list(dict.fromkeys(str(value) for value in blockers))
    hybrid_ready = (
        isinstance(hybrid_manifest, Mapping)
        and hybrid_manifest.get("ready") is True
    )
    status = "completed" if hybrid_ready and not unique_blockers else "blocked"

    manifest = {
        "format": FORMAT,
        "version": 1,
        "status": status,
        "ready": status == "completed",
        "summary": {
            "pe_image_present": image_record["present"],
            "pe_evidence_generated": pe_report is not None,
            "hybrid_started": hybrid_started,
            "hybrid_ready": hybrid_ready,
            "blocking_reason_count": len(unique_blockers),
        },
        "inputs": {
            "pe_image": image_record,
            "capture_jsonl": str(Path(capture_jsonl).expanduser()),
            "bundles": [str(Path(value).expanduser()) for value in bundles],
            "corpus": [str(Path(value).expanduser()) for value in corpus],
        },
        "generated_pe_evidence": {
            "path": str(pe_report_path) if pe_report is not None else None,
            "format": pe_report.get("format") if pe_report is not None else None,
            "sha256": pe_report_sha,
            "source_pe_image_sha256": image_record.get("sha256"),
        },
        "hybrid": {
            "format": hybrid_manifest.get("format") if isinstance(hybrid_manifest, Mapping) else None,
            "status": hybrid_manifest.get("status") if isinstance(hybrid_manifest, Mapping) else None,
            "summary": hybrid_manifest.get("summary") if isinstance(hybrid_manifest, Mapping) else None,
            "renderer_frontier": (
                (hybrid_manifest.get("production") or {}).get("renderer_frontier")
                if isinstance(hybrid_manifest, Mapping)
                and isinstance(hybrid_manifest.get("production"), Mapping)
                else None
            ),
            "manifest": (
                str(hybrid_dir / "silverstone_renderer_hybrid_production_run.json")
                if hybrid_started
                else None
            ),
        },
        "blocking_reasons": unique_blockers,
        "boundary": {
            "pe_image_is_read_as_static_data_only": True,
            "pe_image_is_executed": False,
            "pe_evidence_builder": "d3d9_pe_evidence.analyze_d3d9_pe_image_file",
            "usage_map_numeric_source": "SHIFT.PEImageEvidence/1:decoded_tables.usage",
            "usage_mapping_allows_inference": False,
            "hybrid_proof_semantics_changed": False,
            "original_game_execution_required": False,
            "new_capture_required": False,
        },
    }
    _write_json_atomic(
        out / "silverstone_renderer_pe_image_hybrid_production_run.json",
        manifest,
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundles", nargs="+")
    parser.add_argument("--capture-jsonl", required=True)
    parser.add_argument("--pe-image", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--corpus", action="append", default=[])
    parser.add_argument("--runtime-shader-targets")
    parser.add_argument(
        "--max-json-bytes",
        type=int,
        default=128 * 1024 * 1024,
    )
    args = parser.parse_args(argv)

    manifest = run_pe_image_hybrid_production(
        bundles=args.bundles,
        capture_jsonl=args.capture_jsonl,
        pe_image=args.pe_image,
        output_dir=args.output_dir,
        corpus=args.corpus,
        runtime_shader_targets=args.runtime_shader_targets,
        max_json_bytes=args.max_json_bytes,
    )
    print(
        json.dumps(
            {
                "format": manifest["format"],
                "status": manifest["status"],
                "summary": manifest["summary"],
                "blocking_reasons": manifest["blocking_reasons"],
                "renderer_frontier": manifest["hybrid"]["renderer_frontier"],
                "manifest": str(
                    Path(args.output_dir)
                    / "silverstone_renderer_pe_image_hybrid_production_run.json"
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if manifest["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
