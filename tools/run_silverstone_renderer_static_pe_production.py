#!/usr/bin/env python3
"""Run hybrid Silverstone renderer production from a static PE image plus raw capture.

The PE image is read as bytes only through the existing source-backed
``d3d9_pe_evidence`` adapter.  It is never executed or loaded as a program.
The resulting ``SHIFT.PEImageEvidence/1`` report is then handed to Phase 631.
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
SRC = ROOT / "src"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from d3d9_pe_evidence import analyze_d3d9_pe_image_file
from run_silverstone_renderer_hybrid_production import run_hybrid_production

FORMAT = "SHIFT.SilverstoneRendererStaticPEProductionRun/1"
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


def _canonical_sha(value: Mapping[str, Any]) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


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


def _pe_input(path: Path) -> tuple[dict[str, Any], list[str]]:
    present = path.is_file()
    record = {
        "path": str(path),
        "present": present,
        "size": path.stat().st_size if present else None,
        "sha256": _sha256_file(path) if present else None,
    }
    return record, [] if present else ["file-not-found"]


def run_static_pe_production(
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
    pe_dir = out / "pe"
    hybrid_dir = out / "hybrid"
    pe_output = pe_dir / "shift_pe_image_evidence.json"
    pe_path = Path(pe_image).expanduser()

    pe_record, pe_input_blockers = _pe_input(pe_path)
    blockers = [f"pe_image:{reason}" for reason in pe_input_blockers]
    pe_report: Mapping[str, Any] | None = None
    pe_pretty_sha: str | None = None
    pe_canonical_sha: str | None = None
    pe_error: str | None = None

    if pe_record["present"]:
        try:
            candidate = analyze_d3d9_pe_image_file(pe_path)
            if not isinstance(candidate, Mapping):
                raise ValueError("PE evidence root is not a JSON object")
            if candidate.get("format") != PE_FORMAT:
                raise ValueError(
                    f"PE evidence format mismatch: {candidate.get('format')!r}"
                )
            pe_report = dict(candidate)
            pe_canonical_sha = _canonical_sha(pe_report)
            pe_pretty_sha = _write_json_atomic(pe_output, pe_report)
        except Exception as exc:
            pe_error = f"{type(exc).__name__}:{exc}"
            blockers.append(f"pe_evidence:{pe_error}")

    hybrid_manifest: Mapping[str, Any] | None = None
    hybrid_started = pe_report is not None and not blockers
    if hybrid_started:
        hybrid_manifest = run_hybrid_production(
            bundles=bundles,
            capture_jsonl=capture_jsonl,
            pe_evidence=pe_output,
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
    hybrid_status = (
        hybrid_manifest.get("status")
        if isinstance(hybrid_manifest, Mapping)
        else None
    )
    status = (
        "completed"
        if hybrid_started
        and hybrid_status == "completed"
        and not unique_blockers
        else "blocked"
    )

    conclusions = pe_report.get("conclusions") if isinstance(pe_report, Mapping) else None
    conclusions = conclusions if isinstance(conclusions, Mapping) else {}
    image = pe_report.get("image") if isinstance(pe_report, Mapping) else None
    image = image if isinstance(image, Mapping) else {}

    manifest = {
        "format": FORMAT,
        "version": 1,
        "status": status,
        "ready": status == "completed",
        "summary": {
            "pe_image_present": pe_record["present"],
            "pe_evidence_generated": pe_report is not None,
            "pe_usage_table_status": conclusions.get("usage_table_status"),
            "pe_usage_table_file_backed": conclusions.get("file_backed_usage_table"),
            "hybrid_started": hybrid_started,
            "hybrid_completed": hybrid_status == "completed",
            "blocking_reason_count": len(unique_blockers),
        },
        "pe_image": pe_record,
        "pe_evidence": {
            "format": pe_report.get("format") if isinstance(pe_report, Mapping) else None,
            "output": str(pe_output) if pe_report is not None else None,
            "output_sha256": pe_pretty_sha,
            "canonical_sha256": pe_canonical_sha,
            "error": pe_error,
            "image": {
                "bytes": image.get("bytes"),
                "image_base": image.get("image_base"),
                "machine": image.get("machine"),
                "optional_header_magic": image.get("optional_header_magic"),
                "section_count": image.get("section_count"),
            },
            "usage_table_status": conclusions.get("usage_table_status"),
            "file_backed_usage_table": conclusions.get("file_backed_usage_table"),
        },
        "hybrid_production": {
            "format": hybrid_manifest.get("format") if isinstance(hybrid_manifest, Mapping) else None,
            "status": hybrid_status,
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
            "pe_source": "static file-backed bytes",
            "pe_adapter": "d3d9_pe_evidence.analyze_d3d9_pe_image_file",
            "pe_image_is_executed": False,
            "pe_image_is_loaded_as_program": False,
            "pe_virtual_addresses_are_mapped_to_file_offsets_only": True,
            "loader_initialized_bytes_are_treated_as_file_backed": False,
            "usage_values_are_inferred": False,
            "partial_usage_table_may_continue_to_phase630_for_fail_closed_reporting": True,
            "original_game_execution_required": False,
            "new_capture_required": False,
            "ranking_or_frequency_is_proof": False,
        },
    }
    _write_json_atomic(
        out / "silverstone_renderer_static_pe_production_run.json",
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

    manifest = run_static_pe_production(
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
                "renderer_frontier": manifest["hybrid_production"]["renderer_frontier"],
                "manifest": str(
                    Path(args.output_dir)
                    / "silverstone_renderer_static_pe_production_run.json"
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if manifest["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
